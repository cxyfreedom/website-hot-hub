# -*- coding: utf-8 -*-
import contextlib
import json
import pathlib
import re
import typing
from itertools import chain

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils import current_date, current_time, logger, write_text_file

url = "https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1&round_trip_time=50"
cookie_url = "https://www.douyin.com/passport/general/login_guiding_strategy/?aid=6383"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}

retries = Retry(
    total=3, backoff_factor=1, status_forcelist=[k for k in range(400, 600)]
)


@contextlib.contextmanager
def request_session():
    s = requests.session()
    try:
        s.headers.update(headers)
        s.mount("http://", HTTPAdapter(max_retries=retries))
        s.mount("https://", HTTPAdapter(max_retries=retries))
        yield s
    finally:
        s.close()


class WebSiteDouYin:

    @staticmethod
    def get_raw(cookie: str) -> dict:
        ret = {}
        try:
            with request_session() as s:
                s.headers.update({"Cookie": f"passport_csrf_token={cookie}"})
                resp = s.get(url, timeout=30)
                ret = resp.json()
        except:
            logger.exception("get data failed")
            raise
        return ret

    @staticmethod
    def get_cookie() -> str:
        cookie_data = ""
        try:
            with request_session() as s:
                resp = s.get(cookie_url)
                regex = re.compile(r"passport_csrf_token=(.*?); Path=/;")
                result = re.match(regex, resp.headers["Set-Cookie"])
                if result:
                    cookie_data = result.group(1)
                return cookie_data
        except:
            logger.exception("get douyin cookie failed")
        return cookie_data

    @staticmethod
    def clean_raw(raw_data: dict) -> typing.List[typing.Dict[str, typing.Any]]:
        ret: typing.List[typing.Dict[str, typing.Any]] = []
        for item in raw_data.get("data", {}).get("word_list", []):
            ret.append(
                {
                    "title": item["word"],
                    "url": f"https://www.douyin.com/hot/{item['sentence_id']}",
                }
            )
        return ret

    @staticmethod
    def read_already_download(
        full_path: str,
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        content: typing.List[typing.Dict[str, typing.Any]] = []
        if pathlib.Path(full_path).exists():
            with open(full_path) as fd:
                content = json.loads(fd.read())
        return content

    @staticmethod
    def create_list(content: typing.List[typing.Dict[str, typing.Any]]) -> str:
        topics = []
        template = """<!-- BEGIN DOUYIN -->
<!-- 最后更新时间 {update_time} -->
{topics}
<!-- END DOUYIN -->"""

        for item in content:
            topics.append(f"1. [{item['title']}]({item['url']})")
        template = template.replace("{update_time}", current_time())
        template = template.replace("{topics}", "\n".join(topics))
        return template

    @staticmethod
    def create_raw(full_path: str, raw: str) -> None:
        write_text_file(full_path, raw)

    @staticmethod
    def merge_data(
        cur: typing.List[typing.Dict[str, typing.Any]],
        another: typing.List[typing.Dict[str, typing.Any]],
    ):
        merged_dict: typing.Dict[str, typing.Any] = {}
        for item in chain(cur, another):
            merged_dict[item["url"]] = item["title"]

        return [{"url": k, "title": v} for k, v in merged_dict.items()]

    def update_readme(self, content: typing.List[typing.Dict[str, typing.Any]]) -> str:
        with open("./README.md", "r") as fd:
            readme = fd.read()
            return re.sub(
                r"<!-- BEGIN DOUYIN -->[\W\w]*<!-- END DOUYIN -->",
                self.create_list(content),
                readme,
            )

    def create_archive(
        self, content: typing.List[typing.Dict[str, typing.Any]], date: str
    ) -> str:
        return f"# {date}\n\n共 {len(content)} 条\n\n{self.create_list(content)}"

    def run(self, update_readme=True):
        dir_name = "douyin"
        cookie_data = self.get_cookie()

        raw_data = self.get_raw(cookie_data)
        cleaned_data = self.clean_raw(raw_data)

        cur_date = current_date()
        # 写入原始数据
        raw_path = f"./raw/{dir_name}/{cur_date}.json"
        already_download_data = self.read_already_download(raw_path)
        merged_data = self.merge_data(cleaned_data, already_download_data)

        self.create_raw(raw_path, json.dumps(merged_data, ensure_ascii=False))

        # 更新 archive
        archive_text = self.create_archive(merged_data, cur_date)
        archive_path = f"./archives/{dir_name}/{cur_date}.md"
        write_text_file(archive_path, archive_text)
        
        readme_content = self.create_list(merged_data)
        
        if update_readme:
            readme_text = self.update_readme(merged_data)
            readme_path = "./README.md"
            write_text_file(readme_path, readme_text)
            return True
        else:
            return {
                "section_name": "DOUYIN",
                "content": readme_content,
                "data_count": len(merged_data)
            }


if __name__ == "__main__":
    douyin_obj = WebSiteDouYin()
    douyin_obj.run()
