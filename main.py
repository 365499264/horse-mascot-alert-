# main.py —— 多信息源 + 每30秒 + 显示命中关键词 + 原链接（终极版）

import feedparser, requests, time, schedule, hashlib, re, json

# ==================== 配置 ====================
with open('config.json') as f:
    cfg = json.load(f)

BOT_TOKEN    = cfg["BOT_TOKEN"].strip()
CHAT_ID      = cfg["CHAT_ID"].strip()
WEIBO_COOKIE = cfg.get("WEIBO_COOKIE", "").strip()

# ==================== 你要监控的所有关键词组 ====================
# 每个子列表算一个“情报主题”，命中后会显示这个组的名字
MONITOR_GROUPS = {
    "马年吉祥物": ["马年吉祥物", "2026吉祥物", "生肖马吉祥物", "央视马年吉祥物", "春晚吉祥物", "丙午年吉祥物", "龙马精神", "马宝","吉祥物"],
    "春晚导演/主持人": ["于蕾", "刘德华", "春晚导演组", "春晚彩排", "沈腾", "马丽", "尼格买提"],
    "龙年收尾": ["龙辰", "福龙", "2025吉祥物"],
    "其他爆料": ["春晚内部", "吉祥物泄露", "央视内部人士"]   # 继续加就行
}

# 重点关注微博账号（必看）
FOCUS_USERS = {
    "1224379070": "央视春晚官方",
    "2656274875": "央视新闻",
    "1913763837": "新华社",
    # 加更多： "微博ID": "备注名字"
}

sent_cache = set()

def tg(text):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False}, timeout=10)
    except: pass

# 返回命中的关键词组名称
def match_keyword(text):
    for group_name, keywords in MONITOR_GROUPS.items():
        for kw in keywords:
            if kw in text:
                return group_name, kw
    return None, None

# ==================== 各平台监控 ====================
def check_rss():
    urls = ["http://news.cctv.com/rss/china.xml", "http://www.cctv.com/rss/culture.xml",
            "http://www.xinhuanet.com/rss/culture.xml"]
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:6]:
                content = e.title + e.get("summary","")
                group, kw = match_keyword(content)
                if group:
                    uid = hashlib.md5(e.link.encode()).hexdigest()
                    if uid not in sent_cache:
                        tg(f"官媒\n命中关键词：【{group}】→ {kw}\n{e.title}\n\n原文：{e.link}")
                        sent_cache.add(uid)
        except: pass

def check_weibo():
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": WEIBO_COOKIE}
    # 1. 关键词实时流
    for group_name, kws in MONITOR_GROUPS.items():
        q = kws[0]
        api = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{q}"
        try:
            r = requests.get(api, headers=headers, timeout=10)
            for card in r.json().get("data", {}).get("cards", []):
                if "mblog" not in card: continue
                b = card["mblog"]
                text = re.sub('<[^<]+?>', '', b["text"])
                g, kw = match_keyword(text)
                if g:
                    uid = b["id"]
                    if uid not in sent_cache:
                        link = f"https://m.weibo.cn/detail/{uid}"
                        tg(f"微博实时\n命中：【{g}】→ {kw}\n@{b['user']['screen_name']}\n{text}\n\n链接：{link}")
                        sent_cache.add(uid)
        except: pass

    # 2. 重点账号最新微博（不看关键词，全推）
    for uid, name in FOCUS_USERS.items():
        api = f"https://m.weibo.cn/api/container/getIndex?containerid=107603{uid}"
        try:
            r = requests.get(api, headers=headers, timeout=10)
            for card in r.json().get("data", {}).get("cards", []):
                if "mblog" not in card: continue
                b = card["mblog"]
                text = re.sub('<[^<]+?>', '', b["text"])
                uid_full = b["id"]
                if uid_full not in sent_cache:
                    link = f"https://m.weibo.cn/detail/{uid_full}"
                    tg(f"重点账号\n{name}（官方）最新动态\n{text}\n\n链接：{link}")
                    sent_cache.add(uid_full)
        except: pass

def check_douyin():
    headers = {"User-Agent": "Mozilla/5.0"}
    for group_name, kws in MONITOR_GROUPS.items():
        q = kws[0]
        url = f"https://www.douyin.com/aweme/v1/web/search/item/?keyword={q}&count=8"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            for item in r.json().get("data", []):
                aweme = item.get("aweme_info") or item
                desc = aweme.get("desc", "")
                g, kw = match_keyword(desc)
                if g:
                    aid = aweme.get("aweme_id")
                    if aid and aid not in sent_cache:
                        author = aweme.get("author", {}).get("nickname", "抖音用户")
                        share = aweme.get("share_url", "无链接")
                        tg(f"抖音爆了\n命中：【{g}】→ {kw}\n@{author}\n{desc}\n\n链接：{share}")
                        sent_cache.add(aid)
        except: pass

def check_baidu_hot():
    try:
        r = requests.get("https://top.baidu.com/api/board?tab=realtime", timeout=8)
        for item in r.json().get("data", {}).get("cards", [{}])[0].get("content", [])[:15]:
            word = item.get("word","")
            g, kw = match_keyword(word)
            if g and word not in sent_cache:
                tg(f"百度热搜冲榜\n命中：【{g}】→ {kw}\n# {word}")
                sent_cache.add(word)
    except: pass

# ==================== 每30秒执行一次 ====================
def job():
    print(f"[{time.strftime('%H:%M:%S')}] 多源30秒轮询...", flush=True)
    check_rss()
    check_weibo()
    check_douyin()
    check_baidu_hot()

schedule.every(30).seconds.do(job)
job()
print("多信息源 + 命中关键词高亮 + 原链接推送 已启动！")

while True:
    schedule.run_pending()
    time.sleep(1)
