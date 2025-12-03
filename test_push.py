# 文件名: test_push.py   （直接上传到 PythonAnywhere，和 main.py 同目录就行）

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import time

# 读取你的 config.json（和主脚本共用同一份配置）
with open('config.json') as f:
    cfg = json.load(f)

BOT_TOKEN      = cfg.get("BOT_TOKEN", "")
CHAT_ID        = cfg.get("CHAT_ID", "")
EMAIL_FROM     = cfg.get("EMAIL_FROM", "")
EMAIL_TO       = cfg.get("EMAIL_TO", "")
EMAIL_PASSWORD = cfg.get("EMAIL_PASSWORD", "")
SMTP_SERVER    = cfg.get("SMTP_SERVER", "smtp.163.com")
SMTP_PORT      = cfg.get("SMTP_PORT", 465)

test_time = time.strftime("%Y-%m-%d %H:%M:%S")

# 1. 测试 Telegram 推送
def test_telegram():
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram 配置缺失，跳过")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": f" 马年吉祥物监控测试成功！\n\n时间：{test_time}\n配置完全正常！",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.json().get("ok"):
            print("Telegram 推送成功！")
        else:
            print("Telegram 推送失败：", r.text)
    except Exception as e:
        print("Telegram 异常：", e)

# 2. 测试邮箱推送
def test_email():
    if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:
        print("邮箱配置缺失，跳过")
        return
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Subject"] = "【测试成功】马年吉祥物监控配置正常"

    body = f"""
马年吉祥物监控测试邮件

测试时间：{test_time}

恭喜！你的邮箱推送配置完全正确！
等吉祥物一公布，你会第一时间收到邮件和 Telegram 双推送～
    """
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        server.quit()
        print("邮箱推送成功！")
    except Exception as e:
        print("邮箱发送失败：", e)

# 执行测试
print("开始测试推送（Telegram + 邮箱）...\n")
test_telegram()
test_email()
print("\n测试完成！去频道和邮箱看看吧～")