# -*- coding: utf-8 -*-
import contextlib
import json
import pathlib
import random
import re
import time
import typing
from itertools import chain

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils import current_date, current_time, logger, write_text_file

url = "https://api.bilibili.com/x/web-interface/ranking/v2"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}

# 连接层不重试，由 get_raw 统一重试（含 code=-352 风控）
# 最坏耗时：4 次 × (连接 3s + 读取 5s) + 退避 (1+2+4)s + 抖动 3×0.5s = 40.5s < 60s 批次超时
MAX_ATTEMPTS = 4
REQUEST_TIMEOUT = (3, 5)
BACKOFF_BASE = 1
JITTER = 0.5

retries = Retry(
    total=0, backoff_factor=0.5, status_forcelist=[k for k in range(400, 600)]
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


class WebSiteBilibili:
    @staticmethod
    def get_raw() -> dict:
        last_error: typing.Optional[Exception] = None
        with request_session() as s:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    resp = s.get(url, timeout=REQUEST_TIMEOUT)
                    resp.raise_for_status()
                    ret = resp.json()
                    if ret.get("code") == 0:
                        return ret
                    last_error = RuntimeError(
                        f"bilibili 返回 code={ret.get('code')} message={ret.get('message')}"
                    )
                except Exception as e:  # 网络错误、超时、4xx/5xx、非 JSON
                    last_error = e
                if attempt < MAX_ATTEMPTS:
                    delay = BACKOFF_BASE * 2 ** (attempt - 1) + random.uniform(0, JITTER)
                    logger.warning(
                        f"bilibili 第 {attempt}/{MAX_ATTEMPTS} 次请求失败: {last_error}，{delay:.1f}s 后重试"
                    )
                    time.sleep(delay)
        logger.error(f"bilibili 重试 {MAX_ATTEMPTS} 次后仍失败: {last_error}")
        raise RuntimeError(f"bilibili 获取数据失败: {last_error}") from last_error

    @staticmethod
    def clean_raw(raw_data: dict) -> typing.List[typing.Dict[str, typing.Any]]:
        ret: typing.List[typing.Dict[str, typing.Any]] = []
        for item in raw_data.get("data", {}).get("list", []):
            ret.append(
                {
                    "title": item["title"],
                    "url": item.get("short_link_v2") or f"https://b23.tv/{item['bvid']}",
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
        template = """<!-- BEGIN BILIBILI -->
<!-- 最后更新时间 {update_time} -->
{topics}
<!-- END BILIBILI -->"""

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
                r"<!-- BEGIN BILIBILI -->[\W\w]*<!-- END BILIBILI -->",
                lambda _m: self.create_list(content),
                readme,
            )

    def create_archive(
        self, content: typing.List[typing.Dict[str, typing.Any]], date: str
    ) -> str:
        return f"# {date}\n\n共 {len(content)} 条\n\n{self.create_list(content)}"

    def run(self, update_readme=True):
        dir_name = "bilibili"

        raw_data = self.get_raw()
        cleaned_data = self.clean_raw(raw_data)
        if not cleaned_data:
            raise ValueError(f"{dir_name} 解析结果为空，可能接口变更或被风控")

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
                "section_name": "BILIBILI",
                "content": readme_content,
                "data_count": len(merged_data)
            }


if __name__ == "__main__":
    bilibili_obj = WebSiteBilibili()
    bilibili_obj.run()
