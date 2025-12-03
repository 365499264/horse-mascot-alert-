# main.py —— 马年情报 + four.meme 最近2周 meme 币查询（CA + 市值）终极版

import feedparser, requests, time, schedule, hashlib, re, json, datetime

# ==================== 配置 ====================
with open('config.json') as f:
    cfg = json.load(f)

BOT_TOKEN    = cfg["BOT_TOKEN"].strip()
CHAT_ID      = cfg["CHAT_ID"].strip()
WEIBO_COOKIE = cfg.get("WEIBO_COOKIE", "").strip()

# ==================== 监控关键词组（命中后自动查 2周 meme 币） ====================
MONITOR_GROUPS = {
    "马年吉祥物": ["马年吉祥物", "2026吉祥物", "生肖马吉祥物", "央视马年吉祥物", "春晚吉祥物", "丙午年吉祥物", "龙马精神", "马宝"],
    "春晚导演/主持人": ["于蕾", "刘德华", "春晚导演组", "春晚彩排", "沈腾", "马丽", "尼格买提"],
    "龙年收尾": ["龙辰", "福龙", "2025吉祥物"],
    "其他爆料": ["春晚内部", "吉祥物泄露", "央视内部人士"]
}

# 重点关注微博账号（全推最新动态）
FOCUS_USERS = {
    "1224379070": "央视春晚官方",
    "2656274875": "央视新闻",
    "1913763837": "新华社",
    "1974808274": "人民日报",
    "3937335371": "春晚报道",
    "1642511402": "我们的太空",
    "1195230310": "全球时报",
    "1878375263": "于蕾",           # 总导演
    "1192329373": "俞敏",           # 副总导演
    "1739776437": "张若昀",
    "1618051664": "秦岚",
    "1264036041": "黄晓明",
    "1195037010": "杨幂",
    "2803301701": "央视舞台美术",
    "5044161781": "央视特效",
    "3217755664": "北京奥运开闭幕式团队",
    "1798836271": "冯巩",
    "1192262372": "蔡明",
    "3935268157": "央视兔年吉祥物团队",
}

sent_cache = set()

def tg(text):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False}, timeout=10)
    except: pass

def match_keyword(text):
    for group_name, keywords in MONITOR_GROUPS.items():
        for kw in keywords:
            if kw in text:
                return group_name, kw
    return None, None

# ==================== 新增：查询 four.meme 最近2周发射代币 ====================
def query_four_meme(keyword):
    """去 Bitquery 搜索关键词相关新 token，抓最近2周发射的 CA + 市值"""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # 计算2周前时间
        two_weeks_ago = datetime.datetime.now() - datetime.timedelta(weeks=2)
        since_time = two_weeks_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        api_url = "https://graphql.bitquery.io"
        query = """
        query {
          EVM(network: bsc, dataset: realtime) {
            DEXTrades(
              limit: {count: 10}
              orderBy: {descendingByField: "Block_Time"}
              where: {
                Transaction: {Block: {Time: {since: "%s"}}}
                Trade: {
                  Dex: {ProtocolName: {is: "fourmeme_v1"}}
                  Currency: {Symbol: {icontains: "%s"}}
                  Side: {AmountInUSD: {gt: "1000"}}  # 只抓市值>1K的
                }
              }
            ) {
              Trade {
                Currency { SmartContract { Address } Symbol Name }
                Price
                Market { MarketCap }
                Volume { AmountInUSD }
              }
              Block { Time }
            }
          }
        }
        """ % (since_time, keyword)

        r = requests.post(api_url, json={"query": query}, headers=headers, timeout=15)
        data = r.json().get("data", {}).get("EVM", {}).get("DEXTrades", [])
        
        tokens = []
        for trade in data:
            ca = trade["Trade"]["Currency"]["SmartContract"]["Address"]
            symbol = trade["Trade"]["Currency"]["Symbol"]
            name = trade["Trade"]["Currency"]["Name"]
            price = trade["Trade"]["Price"]
            mcap = trade["Trade"]["Market"]["MarketCap"]
            volume = trade["Trade"]["Volume"]["AmountInUSD"]
            launch_time = trade["Block"]["Time"][:10]  # YYYY-MM-DD
            tokens.append(f"• {name} ({symbol}) - 发射: {launch_time}\n  CA: {ca[:10]}...{ca[-4:]}\n  价格: ${price:.8f} | 市值: ${mcap:,.0f} | 24h量: ${volume:,.0f}\n  four.meme: https://four.meme/token/{ca}")
        
        if tokens:
            return "\n\n🔥 相关新 meme 币（最近2周发射）:\n" + "\n".join(tokens[:5])  # 限5个防太长
        else:
            return "\n\n🔍 four.meme 上最近2周暂无相关新 token"
    except Exception as e:
        return f"\n\n❌ four.meme 查询异常: {str(e)[:100]}"

# ==================== 原监控函数（推送后自动查 2周 meme 币） ====================
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
                        meme_info = query_four_meme(kw)  # 查2周
                        tg(f"官媒\n命中：【{group}】→ {kw}\n{e.title}\n\n原文：{e.link}{meme_info}")
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
                        meme_info = query_four_meme(kw)  # 查2周
                        tg(f"微博实时\n命中：【{g}】→ {kw}\n@{b['user']['screen_name']}\n{text}\n\n链接：{link}{meme_info}")
                        sent_cache.add(uid)
        except: pass

    # 2. 重点账号（全推 + 查 meme 币，如果有关键词）
    for uid, name in FOCUS_USERS.items():
        api = f"https://m.weibo.cn/api/container/getIndex?containerid=107603{uid}"
        try:
            r = requests.get(api, headers=headers, timeout=10)
            for card in r.json().get("data", {}).get("cards", []):
                if "mblog" not in card: continue
                b = card["mblog"]
                text = re.sub('<[^<]+?>', '', b["text"])
                g, kw = match_keyword(text)
                uid_full = b["id"]
                if uid_full not in sent_cache:
                    link = f"https://m.weibo.cn/detail/{uid_full}"
                    meme_info = query_four_meme(kw) if kw else "\n\n🔍 无关键词，跳过 meme 币查询"
                    tg(f"重点账号\n{name}最新动态\n{text}\n\n链接：{link}{meme_info}")
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
                        meme_info = query_four_meme(kw)  # 查2周
                        tg(f"抖音爆了\n命中：【{g}】→ {kw}\n@{author}\n{desc}\n\n链接：{share}{meme_info}")
                        sent_cache.add(aid)
        except: pass

def check_baidu_hot():
    try:
        r = requests.get("https://top.baidu.com/api/board?tab=realtime", timeout=8)
        for item in r.json().get("data", {}).get("cards", [{}])[0].get("content", [])[:15]:
            word = item.get("word","")
            g, kw = match_keyword(word)
            if g and word not in sent_cache:
                meme_info = query_four_meme(kw)  # 查2周
                tg(f"百度热搜冲榜\n命中：【{g}】→ {kw}\n# {word}{meme_info}")
                sent_cache.add(word)
    except: pass

# ==================== 每30秒执行一次 ====================
def job():
    print(f"[{time.strftime('%H:%M:%S')}] 多源30秒轮询 + four.meme 2周监控...", flush=True)
    check_rss()
    check_weibo()
    check_douyin()
    check_baidu_hot()

schedule.every(30).seconds.do(job)
job()
print("马年情报 + four.meme 最近2周 meme 币自动猎手 已启动！情报一出，CA + 市值秒推！")

while True:
    schedule.run_pending()
    time.sleep(1)
