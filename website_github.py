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
from bs4 import BeautifulSoup

from utils import current_date, current_time, logger, write_text_file

url = "https://github.com/trending?since=daily"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
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


class WebSiteGitHub:
    @staticmethod
    def get_raw() -> str:
        ret = ""
        try:
            with request_session() as s:
                resp = s.get(url, timeout=30)
                ret = resp.text
        except Exception as _:
            logger.exception("get data failed")
            raise
        return ret

    @staticmethod
    def clean_raw(html_content: str) -> typing.List[typing.Dict[str, typing.Any]]:
        ret: typing.List[typing.Dict[str, typing.Any]] = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有 article.Box-row 元素
            articles = soup.find_all('article', class_='Box-row')
            
            for article in articles:
                try:
                    # 获取仓库名称和链接
                    repo_link = article.find('h2').find('a')
                    if not repo_link:
                        continue
                    
                    # 解析仓库完整名称 "owner/repo"
                    full_name = repo_link.get_text().strip()
                    full_name = re.sub(r'\s+', ' ', full_name)  # 处理多余空格
                    parts = [part.strip() for part in full_name.split('/')]
                    
                    if len(parts) != 2:
                        continue
                    
                    owner, repo_name = parts
                    repo_url = "https://github.com" + repo_link.get('href', '')
                    
                    # 获取描述
                    desc_elem = article.find('p', class_=['col-9', 'color-fg-muted'])
                    description = desc_elem.get_text().strip() if desc_elem else ""
                    
                    # 获取编程语言
                    lang_elem = article.find('span', {'itemprop': 'programmingLanguage'})
                    language = lang_elem.get_text().strip() if lang_elem else ""
                    
                    # 获取 stars 数量
                    stars_link = article.find('a', href=lambda x: x and x.endswith('/stargazers'))
                    stars = stars_link.get_text().strip() if stars_link else "0"
                    
                    # 获取 forks 数量
                    forks_link = article.find('a', href=lambda x: x and x.endswith('/forks'))
                    forks = forks_link.get_text().strip() if forks_link else "0"
                    
                    # 构建结果
                    repo_info = {
                        "owner": owner,
                        "repo": repo_name,
                        "title": f"{owner}/{repo_name}",
                        "url": repo_url,
                        "description": description,
                        "language": language,
                        "stars": stars,
                        "forks": forks,
                    }
                    
                    ret.append(repo_info)
                    
                except Exception as e:
                    logger.warning(f"解析单个仓库信息失败: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.exception(f"解析 HTML 失败: {str(e)}")
            raise
        
        return ret

    @staticmethod
    def read_already_download(
        full_path: str,
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        content: typing.List[typing.Dict[str, typing.Any]] = []
        if pathlib.Path(full_path).exists():
            with open(full_path, encoding='utf-8') as fd:
                content = json.loads(fd.read())
        return content

    @staticmethod
    def create_list(content: typing.List[typing.Dict[str, typing.Any]]) -> str:
        """创建列表格式的字符串"""
        topics = []
        template = """<!-- BEGIN GITHUB -->
<!-- 最后更新时间 {update_time} -->
{topics}
<!-- END GITHUB -->"""

        for item in content:
            # 构建显示标题，包含语言和 stars 信息
            display_title = item['title']
            if item.get('language'):
                display_title += f" ({item['language']})"
            if item.get('stars'):
                display_title += f" ⭐{item['stars']}"
            
            topics.append(f"1. [{display_title}]({item['url']})")
        
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
        merged_dict: typing.Dict[str, typing.Dict[str, typing.Any]] = {}
        
        for item in chain(cur, another):
            merged_dict[item["url"]] = item

        return list(merged_dict.values())

    def update_readme(self, content: typing.List[typing.Dict[str, typing.Any]]) -> str:
        with open("./README.md", "r", encoding='utf-8') as fd:
            readme = fd.read()
            return re.sub(
                r"<!-- BEGIN GITHUB -->[\W\w]*<!-- END GITHUB -->",
                self.create_list(content),
                readme,
            )

    def create_archive(
        self, content: typing.List[typing.Dict[str, typing.Any]], date: str
    ) -> str:
        return f"# {date}\n\n共 {len(content)} 个项目\n\n{self.create_list(content)}"

    def run(self, update_readme=True):
        dir_name = "github"

        raw_html = self.get_raw()
        cleaned_data = self.clean_raw(raw_html)

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
                "section_name": "GITHUB",
                "content": readme_content,
                "data_count": len(merged_data)
            }


if __name__ == "__main__":
    github_obj = WebSiteGitHub()
    github_obj.run() 