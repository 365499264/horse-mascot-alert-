#!/usr/bin/env python3
# main.py  （RSS + 可扩展的微博 / 抖音占位 + Telegram + 邮件）
import feedparser
import requests
import time
import schedule
import hashlib
import re
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==================== 这里全部从 config.json 读取 ====================
with open('config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

BOT_TOKEN      = cfg.get("BOT_TOKEN", "")
CHAT_ID        = cfg.get("CHAT_ID", "")
EMAIL_FROM     = cfg.get("EMAIL_FROM", "")
EMAIL_TO       = cfg.get("EMAIL_TO", "")
EMAIL_PASSWORD = cfg.get("EMAIL_PASSWORD", "")
SMTP_SERVER    = cfg.get("SMTP_SERVER", "")
SMTP_PORT      = cfg.get("SMTP_PORT", 465)
WEIBO_COOKIE   = cfg.get("WEIBO_COOKIE", "")
RSS_FEEDS      = cfg.get("RSS_FEEDS", [])  # 可选，示例: ["https://example.com/rss"]
KEYWORDS       = cfg.get("KEYWORDS", ["马年吉祥物","2026吉祥物","生肖马吉祥物","央视马年吉祥物","春晚吉祥物","丙午年吉祥物","龙马精神"])

# 持久化已发送记录（防止重发）
SENT_CACHE_FILE = 'sent_cache.json'
if os.path.exists(SENT_CACHE_FILE):
    try:
        with open(SENT_CACHE_FILE, 'r', encoding='utf-8') as f:
            sent_cache = set(json.load(f))
    except Exception:
        sent_cache = set()
else:
    sent_cache = set()

def save_sent_cache():
    try:
        with open(SENT_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(sent_cache), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def send_telegram(msg, url=""):
    if not BOT_TOKEN or not CHAT_ID:
        print("telegram: 未配置 BOT_TOKEN 或 CHAT_ID，跳过")
        return
    text = f"马年吉祥物情报！\n\n{msg}"
    if url:
        text += f"\n\n链接：{url}"
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False},
                      timeout=10)
    except Exception as e:
        print("telegram 发送失败：", e)

def send_email(subject, body, url=""):
    if not EMAIL_FROM or not EMAIL_TO or not EMAIL_PASSWORD or not SMTP_SERVER:
        print("email: 未配置邮件必要信息，跳过")
        return
    msg = MIMEMultipart()
    msg["From"], msg["To"], msg["Subject"] = EMAIL_FROM, EMAIL_TO, subject
    content = body + (f"\n\n原文链接：{url}" if url else "")
    msg.attach(MIMEText(content, "plain", "utf-8"))
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
    except Exception as e:
        print("email 发送失败：", e)

def notify(source, title, content, url=""):
    msg = f"【{source}】{title}\n\n{content.strip()[:600]}"
    print("通知：", msg.replace("\n", " ")[:200], " ...")
    send_telegram(msg, url)
    send_email(f"【马年吉祥物】{title}", content.strip(), url)

# ----------------- RSS 检查 -----------------
def make_fingerprint(title, link):
    key = (title or "") + (link or "")
    return hashlib.sha1(key.encode('utf-8')).hexdigest()

def match_keywords(text, keywords):
    if not text:
        return False
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return True
    return False

def check_rss():
    if not RSS_FEEDS:
        print("check_rss: 没有配置 RSS_FEEDS，跳过")
        return
    for feed_url in RSS_FEEDS:
        try:
            d = feedparser.parse(feed_url)
            for entry in d.entries:
                title = entry.get('title', '') or ''
                summary = entry.get('summary', '') or entry.get('description', '') or ''
                link = entry.get('link', '') or ''
                combined = title + "\n" + summary
                if match_keywords(combined, KEYWORDS):
                    fp = make_fingerprint(title, link)
                    if fp in sent_cache:
                        continue
                    notify("RSS", title, summary, link)
                    sent_cache.add(fp)
                    save_sent_cache()
        except Exception as e:
            print(f"check_rss: 解析失败 {feed_url} -> {e}")

# ----------------- 微博 检查（占位） -----------------
def check_weibo():
    # 微博抓取依赖你的 WEIBO_COOKIE：具体实现可能需要移动端/AJAX 接口或使用第三方 API
    # 这里做简单占位：打印提示并跳过。若你需要我实现具体抓取逻辑，请把目标用户/关键词和 cookie 提供给我。
    if not WEIBO_COOKIE:
        print("check_weibo: 未配置 WEIBO_COOKIE，跳过")
        return
    print("check_weibo: 已配置 WEIBO_COOKIE，但当前代码为占位。若需我实现抓取，请回复并提供目标（例如用户 id 或搜索关键词）。")

# ----------------- 抖音 检查（占位） -----------------
def check_douyin():
    # 抖音抓取通常需要逆向移动端或使用官方/第三方 API，容易变动且可能受限。
    # 这里先占位：如果有具体账号/关键词和可用的 API，我可以实现。
    print("check_douyin: 当前为占位实现。若需我补全，请提供目标账号或可用接口说明。")

# ========== 调度 ==========
def job():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 检查中...")
    try:
        check_rss()
    except Exception as e:
        print("job: check_rss 出错：", e)
    try:
        check_weibo()
    except Exception as e:
        print("job: check_weibo 出错：", e)
    try:
        check_douyin()
    except Exception as e:
        print("job: check_douyin 出错：", e)

# 每 7 分钟检查一次
schedule.every(7).minutes.do(job)

if __name__ == "__main__":
    job()
    print("马年吉祥物 24h 监控已启动！")
    while True:
        schedule.run_pending()
        time.sleep(1)