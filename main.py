# -*- coding: utf-8 -*-

import concurrent.futures
import time

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
        return True
    except Exception as e:
        debug_print(f"任务执行失败: {str(e)}", website_name)
        return False


def execute_tasks_batch(websites_to_run, timeout_seconds, max_workers):
    successful_tasks = set()
    failed_tasks = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_website = {
            executor.submit(run_website_task, website_obj, website_name): website_name
            for website_obj, website_name in websites_to_run
        }

        done_futures = set()
        start_time = time.time()
        timeout_occurred = False
        
        while len(done_futures) < len(future_to_website) and not timeout_occurred:
            elapsed_time = time.time() - start_time
            if elapsed_time >= timeout_seconds:
                debug_print(f"批次执行超时（已执行{elapsed_time:.1f}秒）")
                timeout_occurred = True
                break
                
            remaining_time = min(60, timeout_seconds - elapsed_time)
            if remaining_time <= 0:
                timeout_occurred = True
                break
                
            done, pending = concurrent.futures.wait(
                future_to_website.keys() - done_futures, 
                timeout=remaining_time,
                return_when=concurrent.futures.FIRST_COMPLETED
            )
            
            for future in done:
                done_futures.add(future)
                website_name = future_to_website[future]
                
                try:
                    success = future.result()
                    if success:
                        successful_tasks.add(website_name)
                        debug_print(f"✓ {website_name} 任务成功完成")
                    else:
                        failed_tasks.add(website_name)
                        debug_print(f"✗ {website_name} 任务执行失败")
                except Exception as e:
                    failed_tasks.add(website_name)
                    debug_print(f"✗ {website_name} 任务异常: {str(e)}")

        remaining_futures = set(future_to_website.keys()) - done_futures
        if remaining_futures:
            debug_print("检测到任务执行超时")
            timeout_tasks = {future_to_website[f] for f in remaining_futures}
            debug_print(f"以下任务执行超时: {', '.join(timeout_tasks)}")
            failed_tasks.update(timeout_tasks)

            for future in remaining_futures:
                website_name = future_to_website[future]
                if future.cancel():
                    debug_print(f"{website_name} 任务已取消，标记为失败")
                else:
                    debug_print(f"{website_name} 任务无法取消（可能正在执行），标记为失败")
                    if website_name not in failed_tasks:
                        failed_tasks.add(website_name)
            
            debug_print(f"超时处理完成，失败任务数: {len(failed_tasks)}")

    debug_print(f"批次执行完成，成功: {len(successful_tasks)}, 失败: {len(failed_tasks)}")
    return successful_tasks, failed_tasks


def main():
    debug_print("开始执行所有网站任务")

    all_websites = [
        (WebSiteSSPai(), "SSPAI"),
        (WebSite36Kr(), "36KR"),
        (WebSiteBilibili(), "BILIBILI"),
        (WebSiteDouYin(), "DOUYIN"),
        (WebSiteJueJin(), "JUEJIN"),
        (WebSiteWeRead(), "WEREAD"),
        (WebSiteKuaiShou(), "KUAISHOU"),
    ]

    timeout_seconds = 120  # 每轮任务最多执行2分钟
    max_retry_rounds = 3  # 最多重试3轮
    retry_delay = 30  # 重试间隔30秒

    successful_tasks = set()
    websites_to_run = all_websites.copy()
    retry_round = 0

    while websites_to_run and retry_round <= max_retry_rounds:
        if retry_round == 0:
            debug_print(f"第1轮执行，共 {len(websites_to_run)} 个任务")
        else:
            debug_print(f"第{retry_round + 1}轮重试，共 {len(websites_to_run)} 个任务")
            if retry_delay > 0:
                debug_print(f"等待 {retry_delay} 秒后开始重试...")
                time.sleep(retry_delay)

        max_workers = min(len(websites_to_run), 7)
        round_successful, round_failed = execute_tasks_batch(
            websites_to_run, timeout_seconds, max_workers
        )
        
        debug_print(f"第{retry_round + 1}轮结果 - 成功: {len(round_successful) if round_successful else 0}, 失败: {len(round_failed) if round_failed else 0}")
        if round_failed:
            debug_print(f"失败任务详情: {list(round_failed)}")

        successful_tasks.update(round_successful)

        if round_failed:
            debug_print(f"本轮失败任务: {', '.join(round_failed)}")

            failed_website_names = round_failed
            websites_to_run = []

            for website_obj, website_name in all_websites:
                if website_name in failed_website_names:
                    if website_name == "SSPAI":
                        websites_to_run.append((WebSiteSSPai(), website_name))
                    elif website_name == "36KR":
                        websites_to_run.append((WebSite36Kr(), website_name))
                    elif website_name == "BILIBILI":
                        websites_to_run.append((WebSiteBilibili(), website_name))
                    elif website_name == "DOUYIN":
                        websites_to_run.append((WebSiteDouYin(), website_name))
                    elif website_name == "JUEJIN":
                        websites_to_run.append((WebSiteJueJin(), website_name))
                    elif website_name == "WEREAD":
                        websites_to_run.append((WebSiteWeRead(), website_name))
                    elif website_name == "KUAISHOU":
                        websites_to_run.append((WebSiteKuaiShou(), website_name))
                        
            debug_print(f"准备重试 {len(websites_to_run)} 个任务")
        else:
            websites_to_run = []
            debug_print("本轮所有任务执行成功")

        retry_round += 1
        debug_print(f"准备进入第{retry_round + 1}轮，待执行任务数: {len(websites_to_run)}")

    all_website_names = {name for _, name in all_websites}
    final_failed = all_website_names - successful_tasks

    if final_failed:
        debug_print(f"经过 {max_retry_rounds + 1} 轮尝试，以下任务仍然失败: {', '.join(final_failed)}")
        debug_print(f"成功完成 {len(successful_tasks)}/{len(all_website_names)} 个任务")
    else:
        debug_print(f"所有 {len(all_website_names)} 个任务均成功完成")

    debug_print("所有网站任务执行完成")


if __name__ == "__main__":
    main()
