# main.py —— 马年吉祥物 每30秒全平台监控（只推 Telegram，Render专用）
import feedparser, requests, time, schedule, hashlib, re, json

# ======== 读取 config.json（只需保留这几项）========
with open('config.json') as f:
    cfg = json.load(f)

BOT_TOKEN = cfg["BOT_TOKEN"].strip()
CHAT_ID   = cfg["CHAT_ID"].strip()
WEIBO_COOKIE = cfg.get("WEIBO_COOKIE", "").strip()

# 关键词（可继续加）
KEYWORDS = [
    "马年吉祥物", "2026吉祥物", "生肖马吉祥物", "央视马年吉祥物",
    "春晚吉祥物", "丙午年吉祥物", "龙马精神", "马宝", "马年形象","吉祥物"
]

sent_cache = set()   # 防重复

def tg(msg, url=""):
    if not BOT_TOKEN or not CHAT_ID: return
    text = f"马年吉祥物秒报！\n\n{msg}"
    if url: text += f"\n\n链接：{url}"
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False},
            timeout=8
        )
    except: pass

def notify(source, title, content="", url=""):
    message = f"【{source}】{title}\n{content.strip()[:400]}"
    tg(message, url)

# ============ 三大平台监控函数（已极致精简）============
def check_rss():
    urls = [
        "http://news.cctv.com/rss/china.xml",
        "http://www.cctv.com/rss/culture.xml",
        "http://www.xinhuanet.com/rss/culture.xml",
    ]
    for url in urls:
        try:
            feed = feedparser.parse(url, request_headers={'User-Agent': 'Mozilla/5.0'})
            for e in feed.entries[:6]:
                text = e.title + (e.get("summary",""))
                uid = hashlib.md5(e.link.encode()).hexdigest()
                if uid in sent_cache: continue
                if any(k in text for k in KEYWORDS):
                    notify("官媒", e.title, text, e.link)
                    sent_cache.add(uid)
        except: pass

def check_weibo():
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": WEIBO_COOKIE}
    apis = [
        "https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D马年吉祥物",
        "https://m.weibo.cn/api/container/getIndex?containerid=1076031224379070",  # 央视春晚官方
    ]
    for api in apis:
        try:
            r = requests.get(api, headers=headers, timeout=10)
            for card in r.json().get("data", {}).get("cards", []):
                if "mblog" not in card: continue
                b = card["mblog"]
                text = re.sub('<[^<]+?>', '', b["text"])
                uid = b["id"]
                if uid in sent_cache: continue
                if any(k in text for k in KEYWORDS):
                    link = f"https://m.weibo.cn/detail/{uid}"
                    nickname = b["user"]["screen_name"]
                    notify("微博", f"@{nickname}", text, link)
                    sent_cache.add(uid)
        except: pass

def check_douyin():
    headers = {"User-Agent": "Mozilla/5.0"}
    search = "https://www.douyin.com/aweme/v1/web/search/item/?keyword=马年吉祥物&count=10"
    try:
        r = requests.get(search, headers=headers, timeout=10)
        for item in r.json().get("data", [])[:8]:
            aweme = item.get("aweme_info") or item
            desc = aweme.get("desc", "")
            uid = aweme.get("aweme_id")
            if not uid or uid in sent_cache: continue
            if any(k in desc for k in KEYWORDS):
                author = aweme.get("author", {}).get("nickname", "抖音用户")
                notify("抖音", f"@{author}", desc, aweme.get("share_url",""))
                sent_cache.add(uid)
    except: pass

# =============== 主任务：每30秒执行一次 ===============
def job():
    print(f"[{time.strftime('%H:%M:%S')}] 30秒轮询检查中...", flush=True)
    check_rss()
    check_weibo()
    check_douyin()

schedule.every(30).seconds.do(job)

# 启动即检查一次
job()
print("马年吉祥物 30秒级监控已启动！Render 24h 永不掉线！")

# 主循环
while True:
    schedule.run_pending()
    time.sleep(1)
