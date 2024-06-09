# -*- coding: utf-8 -*-

import concurrent.futures

from website_sspai import WebSiteSSPai
from website_36kr import WebSite36Kr
from website_bilibili import WebSiteBilibili
from website_douyin import WebSiteDouYin
from website_juejin import WebSiteJueJin
from website_weread import WebSiteWeRead
from website_kuaishou import WebSiteKuaiShou


def run_task(func, *args):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(func, *args)


def main():
    website_sspai_obj = WebSiteSSPai()
    website_36kr_obj = WebSite36Kr()
    website_bilibili_obj = WebSiteBilibili()
    website_douyin_obj = WebSiteDouYin()
    website_juejin_obj = WebSiteJueJin()
    website_weread_obj = WebSiteWeRead()
    website_kuaishou_obj = WebSiteKuaiShou()

    run_task(website_sspai_obj.run)
    run_task(website_36kr_obj.run)
    run_task(website_bilibili_obj.run)
    run_task(website_douyin_obj.run)
    run_task(website_juejin_obj.run)
    run_task(website_weread_obj.run)
    run_task(website_kuaishou_obj.run)


if __name__ == "__main__":
    main()
