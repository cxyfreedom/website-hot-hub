# -*- coding: utf-8 -*-

import concurrent.futures
import os

from website_sspai import WebSiteSSPai
from website_36kr import WebSite36Kr
from website_bilibili import WebSiteBilibili
from website_douyin import WebSiteDouYin
from website_juejin import WebSiteJueJin
from website_weread import WebSiteWeRead
from website_kuaishou import WebSiteKuaiShou
from utils import debug_print


def run_website_task(website_obj, website_name):
    try:
        debug_print("开始执行任务", website_name)
        website_obj.run()
        debug_print("任务执行完成", website_name)
    except Exception as e:
        debug_print(f"任务执行失败: {str(e)}", website_name)
        raise


def main():
    debug_print("开始执行所有网站任务")
    
    websites = [
        (WebSiteSSPai(), "SSPAI"),
        (WebSite36Kr(), "36KR"),
        (WebSiteBilibili(), "BILIBILI"),
        (WebSiteDouYin(), "DOUYIN"),
        (WebSiteJueJin(), "JUEJIN"),
        (WebSiteWeRead(), "WEREAD"),
        (WebSiteKuaiShou(), "KUAISHOU"),
    ]
    
    # 使用线程池执行任务
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(websites)) as executor:
        # 提交所有任务
        future_to_website = {
            executor.submit(run_website_task, website_obj, website_name): website_name
            for website_obj, website_name in websites
        }
        
        # 等待所有任务完成
        for future in concurrent.futures.as_completed(future_to_website):
            website_name = future_to_website[future]
            try:
                future.result()
                debug_print(f"✓ {website_name} 任务成功完成")
            except Exception as e:
                debug_print(f"✗ {website_name} 任务失败: {str(e)}")
    
    debug_print("所有网站任务执行完成")


if __name__ == "__main__":
    main()
