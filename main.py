#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 微博监控 → 每30秒检查一次 → 控制台 print 完整日志 + 只推新微博到 Telegram

import requests
import time
from datetime import datetime

# ==================== 微博接口配置 ====================
API_URL = "https://api.getoneapi.com/api/weibo/fetch_user_post"
HEADERS = {"Content-Type": "application/json"}
# 如果需要鉴权，在这里加 Authorization
HEADERS["Authorization"] = "Bearer qZFrs8gWuh88kglbOqkQrleYJnO2PGXG0e2NIQAePxyEB2hxzUqdFbq6zUjl10Bi"

PAYLOAD = {
    "uid": "",
    "share_text": "https://weibo.com/u/3506728370",   # 春晚官方号
    "since_id": ""
}

# ==================== Telegram 配置（必填） ====================
TG_BOT_TOKEN = "8514974639:AAGGhbc9xRdFug23dqKrYpAdyhb81w1BxHc"   # 改成你的 Bot Token
TG_CHANNEL   = "-1003365789340"                          # 改成你的频道（带@）

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TG_CHANNEL,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=data, timeout=10)
        if r.status_code == 200:
            print(f"[{now()}] Telegram 推送成功")
        else:
            print(f"[{now()}] Telegram 推送失败: {r.text}")
    except Exception as e:
        print(f"[{now()}] Telegram 异常: {e}")

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def escape_md(text: str) -> str:
    """Telegram MarkdownV2 必须转义的字符"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join('\\' + c if c in escape_chars else c for c in text)

# ==================== 主逻辑 ====================
last_bid = None   # 记录已推送过的最新 bid

def check_weibo():
    global last_bid
    print(f"[{now()}] 正在请求微博接口...")
    
    try:
        r = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, timeout=20)
        
        if r.status_code != 200:
            print(f"[{now()}] 请求失败，状态码：{r.status_code}")
            return

        data = r.json()
        if data.get("code") != 200:
            print(f"[{now()}] 接口返回错误：{data.get('message')}")
            return

        cards = data["data"]["data"]["cards"]
        if not cards:
            print(f"[{now()}] 未获取到任何微博")
            return

        first = cards[0]["mblog"]
        bid = first["bid"]
        name = first["user"]["screen_name"]
        created_at = first["created_at"]
        text = first["text"].strip()
        m_link = f"https://m.weibo.cn/status/{bid}"
        pc_link = f"https://weibo.com/{first['user']['id']}/{bid}"

        print(f"[{now()}] 获取成功，最新微博 bid: {bid}（{name}）")

        # 判断是否为新微博
        if last_bid == bid:
            print(f"[{now()}] 无新微博（已是最新）\n")
            return

        # 是新微博 → 打印醒目提示 + 推送到 Telegram
        clean_text = html_to_plain_text(text)   # 去掉HTML标签，保留文字
        print("\n" + "="*70)
        print(" " * 20 + "检测到新微博！正在推送 Telegram...")
        print("="*70)
        print(f"博主：{name}")
        print(f"时间：{created_at}")
        print(f"正文：\n{clean_text}\n")
        print(f"手机链接 → {m_link}")
        print(f"电脑链接 → {pc_link}")
        print("="*70 + "\n")

        # MarkdownV2 格式消息（完美支持加粗、链接、转义）
        tg_message = f"""*新微博提醒！*

*博主：* {escape_md(name)}
*时间：* {escape_md(created_at)}

*正文：*
{escape_md(clean_text)}

*查看链接：*
• [手机端查看]({m_link})
• [电脑端查看]({pc_link})"""

        send_telegram(tg_message)
        last_bid = bid

    except Exception as e:
        print(f"[{now()}] 异常：{e}\n")



# ==================== 启动 ====================
if __name__ == "__main__":
    print("微博监控已启动（每30秒检查一次）")
    print("控制台会显示所有日志，只有新微博才会推送到 Telegram\n")
    
    check_weibo()  # 启动后立即检查一次
    
    while True:
        time.sleep(30)
        check_weibo()
