#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import json
import hashlib
from datetime import datetime

# ==================== 配置区 ====================
API_URL = "https://api.getoneapi.com/api/weibo/fetch_user_post"

HEADERS = {
    "Content-Type": "application/json",
     "Authorization": "Bearer qZFrs8gWuh88kglbOqkQrleYJnO2PGXG0e2NIQAePxyEB2hxzUqdFbq6zUjl10Bi",
}

# 要监控的微博用户（这里以春晚官方账号为例）
PAYLOAD = {
    "uid": "",
    "share_text": "https://weibo.com/u/3506728370",   # 任意有效的用户主页链接即可
    "since_id": ""
}

# 推送方式（这里默认只打印到控制台，想推送到手机请把下面几个函数之一取消注释并填好 key）
def send_message(title: str, content: str):
    """默认只打印，想推送到手机请自行选择下面任意一种方式打开并填 key"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 新微博推送")
    print("=" * 50)
    print(title)
    print("-" * 50)
    print(content)
    print("=" * 50)

# ----------------- 以下推送方式任选其一（需要时取消注释） -----------------
# 1. Server 酱（https://sct.ftqq.com）
# def send_message(title: str, content: str):
#     sckey = "SCTxxxxxxxxxx"
#     requests.post(f"https://sctapi.ftqq.com/{sckey}.send", data={
#         "title": title,
#         "desp": content
#     })

# 2. PushPlus（http://www.pushplus.plus）
# def send_message(title: str, content: str):
#     token = "your_pushplus_token"
#     requests.post("http://www.pushplus.plus/send", json={
#         "token": token,
#         "title": title,
#         "content": content,
#         "template": "txt"
#     })

# 3. 企业微信机器人
# def send_message(title: str, content: str):
#     webhook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxx"
#     requests.post(webhook, json={
#         "msgtype": "text",
#         "text": {"content": f"{title}\n\n{content}"}
#     })
# ========================================================================

# 用来记录上次已经推送过的最新微博 id（或 bid）
last_bid = None

def get_first_weibo():
    global last_bid
    
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("code") != 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 接口返回错误：{data.get('message')}")
            return

        cards = data.get("data", {}).get("data", {}).get("cards", [])
        if not cards:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 未获取到微博数据")
            return

        first_card = cards[0]
        mblog = first_card["mblog"]
        current_bid = mblog["bid"]                     # 微博的唯一短码
        user_name = mblog["user"]["screen_name"]
        created_at = mblog["created_at"]
        text = mblog["text"].strip()

        # 构造几类永久链接（任选其一）
        m_link = f"https://m.weibo.cn/status/{current_bid}"
        pc_link = f"https://weibo.com/{mblog['user']['id']}/{current_bid}"

        # 第一次运行或发现新微博时才推送
        if last_bid is None or current_bid != last_bid:
            title = f"【{user_name}】发布了新微博"
            content = f"时间：{created_at}\n" \
                      f"正文：{text}\n\n" \
                      f"手机查看：{m_link}\n" \
                      f"电脑查看：{pc_link}"

            send_message(title, content)
            
            # 更新记录，防止重复推送
            last_bid = current_bid
        # else:  # 可选：静默模式下什么都不打印
        #     print(f"[{datetime.now().strftime('%H:%M:%S')}] 无新微博（最新 bid: {current_bid}）")

    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 请求异常：{e}")


if __name__ == "__main__":
    print("微博最新一条监控已启动，每 30 秒检查一次（Ctrl+C 停止）\n")
    
    # 第一次先立刻执行一次（快速看到当前最新一条）
    get_first_weibo()
    
    while True:
        time.sleep(30)
        get_first_weibo()
