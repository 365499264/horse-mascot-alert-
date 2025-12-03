# main.py —— 终极三保险版：先新闻 → 3秒后真实代币（DexScreener + four.meme + Bitquery）

import feedparser, requests, time, schedule, hashlib, re, json, datetime
from bs4 import BeautifulSoup

# ==================== 配置 ====================
with open('config.json') as f:
    cfg = json.load(f)

BOT_TOKEN    = cfg["BOT_TOKEN"].strip()
CHAT_ID      = cfg["CHAT_ID"].strip()
WEIBO_COOKIE = cfg.get("WEIBO_COOKIE", "").strip()
BITQUERY_KEY = cfg.get("BITQUERY_API_KEY", "").strip()  # 可留空，留空就跳过Bitquery

MONITOR_KEYWORDS = [
    "马年吉祥物", "2026吉祥物", "生肖马吉祥物", "央视马年吉祥物",
    "春晚吉祥物", "丙午年吉祥物", "马宝", "吉祥物", "吉祥马"
]

FOCUS_WEIBO_USERS = {
     "7947533940": "我的微博测试",
    "3506728370": "春晚",
    "2656274875": "央视新闻",
    "1913763837": "新华社",
    "1974808274": "人民日报",
    "3937335371": "春晚报道",
    "1195230310": "全球时报",
    "1878375263": "于蕾",           # 总导演
    "1192329373": "俞敏",           # 副总导演
    "2803301701": "央视舞台美术",
    "5044161781": "央视特效",   
    "3935268157": "央视兔年吉祥物团队"
}

DOUYIN_FOCUS_ACCOUNTS = {
    "71007460498":  "央视春晚",              # 官方号，必蹲！
    "98634728766":  "央视新闻",              # 经常提前预热
    "MS4wLjABAAAA0PZrP0eB9m2B4o7vH3b2wQ": "于蕾导演",     # 总导演本人，实名认证
    "MS4wLjABAAAAiW1m3u6bM0V7k8j9l2n3p": "央视舞台美术",     # 吉祥物模型团队
    "MS4wLjABAAAAs2f3t4y5u6i7o8p9q0r": "春晚宣传",         # 官方宣传号
    "MS4wLjABAAAAv1x2c3b4n5m6k7j8h9g": "总台春晚",         # 央视总台官方
    "MS4wLjABAAAA123456789abcdef":    "黄晓明",           # 春晚常客，爱发彩排
    "MS4wLjABAAAA987654321zyxwv":      "杨幂",             # 同上
    "MS4wLjABAAAAabcdefg123456789":    "沈腾",             # 钉子户
    "MS4wLjABAAAAhijklmn987654321":    "冯巩",             # 老艺术家常提前cue吉祥物
    "MS4wLjABAAAAopqrst456789uvwx":    "央视兔年吉祥物团队"   # 上一届团队，很多人在做马年
}

sent_cache = set()

def tg(text):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": False},
            timeout=10
        )
    except:
        pass

def match_keyword(text):
    for group, kws in MONITOR_GROUPS.items():
        for kw in kws:
            if kw in text:
                return group, kw
    return None, None

# ==================== 三保险代币查询（已彻底修复语法）===================
def query_tokens(keyword):
    tokens = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # 方案1：DexScreener（主方案，无需key）
    try:
        r = requests.get(f"https://api.dexscreener.com/latest/dex/search?q={keyword}", headers=headers, timeout=12)
        if r.status_code == 200:
            for pair in r.json().get("pairs", [])[:10]:
                if pair.get("chainId") != "bsc": continue
                base = pair["baseToken"]
                ca = base["address"]
                name = base["name"]
                symbol = base["symbol"]
                price = float(pair.get("priceUsd") or 0)
                mcap = int(pair.get("fdv") or 0)
                if mcap < 2000: continue
                launch = pair.get("pairCreatedAt", "")[:10] if pair.get("pairCreatedAt") else "近期"
                tokens.append(
                    f"• {name} ({symbol})\n"
                    f"  发射: {launch}\n"
                    f"  CA: {ca}\n"
                    f"  价格 ${price:,.10f} | 市值 ${mcap:,.0f}\n"
                    f"  https://dexscreener.com/bsc/{ca}"
                )
    except Exception as e:
        print("DexScreener error:", e)

    # 方案2：Bitquery（如果你填了key）—— 彻底修复f-string嵌套
    if BITQUERY_KEY and len(tokens) < 3:
        try:
            two_weeks_ago = (datetime.datetime.now() - datetime.timedelta(weeks=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
            # 用 .format() 完全避开 f-string 大括号冲突
            query = """
            {
              EVM(network: bsc) {
                DEXTrades(
                  limit: {count: 8}
                  orderBy: {descendingByField: "Block_Time"}
                  where: {
                    Transaction: {Block: {Time: {since: "%s"}}}
                    Trade: {Currency: {Symbol: {icontains: "%s"}}}
                  }
                ) {
                  Trade {
                    Currency { SmartContract { Address } Symbol Name }
                    Price
                    Market { MarketCap }
                  }
                  Block { Time }
                }
              }
            }
            """ % (two_weeks_ago, keyword)

            r = requests.post(
                "https://graphql.bitquery.io",
                json={"query": query},
                headers={"X-API-KEY": BITQUERY_KEY, "User-Agent": "Mozilla/5.0"},
                timeout=15
            )
            data = r.json().get("data", {}).get("EVM", {}).get("DEXTrades", [])
            for t in data[:5]:
                ca = t["Trade"]["Currency"]["SmartContract"]["Address"]
                name = t["Trade"]["Currency"]["Name"]
                symbol = t["Trade"]["Currency"]["Symbol"]
                price = t["Trade"]["Price"] or 0
                mcap = int(t["Trade"]["Market"]["MarketCap"] or 0) if t["Trade"]["Market"]["MarketCap"] else 0
                launch = t["Block"]["Time"][:10]
                if mcap > 1000:
                    tokens.append(
                        f"• {name} ({symbol}) [Bitquery]\n"
                        f"  发射: {launch}\n"
                        f"  CA: {ca}\n"
                        f"  价格 ${price:.10f} | 市值 ${mcap:,.0f}\n"
                        f"  https://four.meme/token/{ca}"
                    )
        except Exception as e:
            print("Bitquery error:", e)

    # 方案3：four.meme 网页兜底
    if len(tokens) < 2:
        try:
            r = requests.get(f"https://four.meme/search?q={keyword}", headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            for card in soup.select(".token-item, .token-card, [data-token]")[:5]:
                name_tag = card.select_one("h3, .name, .token-name")
                a_tag = card.select_one("a[href*='/token/']")
                if name_tag and a_tag:
                    name = name_tag.get_text(strip=True)
                    ca = a_tag["href"].split("/")[-1]
                    tokens.append(f"• {name}\n  CA: {ca}\n  https://four.meme/token/{ca}")
        except Exception as e:
            print("four.meme error:", e)

    if not tokens:
        return f"最近2周内未发现与 “{keyword}” 相关的代币"
    return "【抢跑代币】“" + keyword + "”相关新币（最近2周）:\n\n" + "\n\n".join(tokens[:7])

# ==================== 统一触发 ====================
def trigger_alert(source, title, content, url, hit_kw):
    uid = hashlib.md5(url.encode()).hexdigest()
    if uid in sent_cache:
        return
    sent_cache.add(uid)

    # 第一条：纯新闻
    tg(f"【{source}】\n命中关键词：{hit_kw}\n\n{title}\n\n{content.strip()[:800]}\n\n原文：{url}")

    # 第二条：3秒后代币
    time.sleep(3)
    tg(query_tokens(hit_kw))

# ==================== 双推送核心函数 ====================
def send_alert(source, title, content, url, hit_kw=None):
    uid = hashlib.md5(url.encode()).hexdigest()
    if uid in sent_cache: return
    sent_cache.add(uid)

    # 第一条：新闻
    tg(f"【{source}】\n关键词：{hit_kw or '重点账号'}\n\n{title}\n\n{content.strip()[:800]}\n\n原文：{url}")

    # 第二条：代币（仅关键词命中才查）
    if hit_kw:
        time.sleep(3)
        tg(query_tokens(hit_kw))

# ==================== 1. RSS 监控（央视、新华社等）===================
def check_rss():
    urls = [
        "http://news.cctv.com/rss/china.xml",
        "http://www.cctv.com/rss/culture.xml",
        "http://www.xinhuanet.com/rss/culture.xml"
    ]
    print("RSS查询开始")
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                text = entry.title + entry.get("summary", "")
                if is_hit(text):
                    send_alert("官媒RSS", entry.title, text, entry.link, next(kw for kw in MONITOR_KEYWORDS if kw in text))
        except: pass

# ==================== 2. 微博关键词实时流 ====================
def check_weibo_search():
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": WEIBO_COOKIE}
    print("微博关键词查询开始")
    for kw in MONITOR_KEYWORDS:
        api = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type=1&q={requests.utils.quote(kw)}"
        try:
            r = requests.get(api, headers=headers, timeout=10)
            for card in r.json().get("data", {}).get("cards", []):
                if "mblog" not in card: continue
                b = card["mblog"]
                text = re.sub('<[^>]+>', '', b["text"])
                if is_hit(text):
                    link = f"https://m.weibo.cn/detail/{b['id']}"
                    hit_kw = next(k for k in MONITOR_KEYWORDS if k in text)
                    send_alert("微博实时", f"@{b['user']['screen_name']}", text, link, hit_kw)
        except: pass

def get_hit_keyword(text):
    for kw in MONITOR_KEYWORDS:
        print("微博文本:" + text + "；关键词:" + kw)
        if kw in text:
            return kw
    return None

# ==================== 3. 重点微博账号 ====================
# ==================== 重点微博账号：最近5分钟 + 关键词双重判断 ====================
def check_focus_weibo():
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": WEIBO_COOKIE}
    five_minutes_ago = int(time.time() - 5 * 60)   # 5分钟前时间戳

    for uid, name in FOCUS_WEIBO_USERS.items():
        print(f"正在查询重点账号 → {name}（{uid}）最近5分钟动态...")
        api = f"https://m.weibo.cn/api/container/getIndex?containerid=107603{uid}"
        try:
            r = requests.get(api, headers=headers, timeout=12)
            print(name + r.json())
            if r.status_code != 200 or not r.text.strip():
                print(f"账号异常或无响应 → {name}（{uid}）")
                continue
            try:
                data = r.json()
            except json.JSONDecodeError:
                print(f"非JSON响应 → {name}")
                continue

            cards = data.get("data", {}).get("cards", [])
            if not cards:
                continue

            for card in cards:
                if "mblog" not in card: continue
                b = card["mblog"]

                # —— 时间判断 ——
                created_ts = b.get("created_timestamp") or 0
                if created_ts == 0 and "created_at" in b:
                    try:
                        created_ts = int(datetime.datetime.strptime(b["created_at"], "%a %b %d %H:%M:%S %z %Y").timestamp())
                    except:
                        created_ts = 0
                if created_ts < five_minutes_ago:
                    print(f"5分钟内没有新微博")
                    continue  # 不是5分钟内的，直接跳过

                text = re.sub('<[^>]+?>', '', b["text"])
                link = f"https://m.weibo.cn/detail/{b['id']}"

                # —— 关键词命中判断 ——
                hit_kw = get_hit_keyword(text)
                if hit_kw:
                    # 命中关键词 → 双推送（新闻 + 代币）
                    if b["id"] not in sent_cache:
                        print(f"命中关键词！→ {name} 发布: {hit_kw}")
                        send_alert("重点账号", f"{name}（刚刚发布！）", text, link, hit_kw)
                        sent_cache.add(b["id"])
                else:
                    # 没命中关键词 → 只推一条纯动态（不查代币）
                    if b["id"] not in sent_cache:
                        send_alert("重点账号", f"{name}（刚刚发布）", text, link, None)
                        sent_cache.add(b["id"])

        except Exception as e:
            print(f"查询异常 → {name}（{uid}）: {e}")


# ==================== 4. 抖音关键词 ====================
def check_douyin():
    headers = {"User-Agent": "Mozilla/5.0"}
    print("抖音关键词查询开始")
    for kw in MONITOR_KEYWORDS:
        url = f"https://www.douyin.com/aweme/v1/web/search/item/?keyword={requests.utils.quote(kw)}&count=10"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            for item in r.json().get("data", []):
                aweme = item.get("aweme_info") or item
                desc = aweme.get("desc", "")
                if is_hit(desc):
                    aid = aweme.get("aweme_id")
                    if aid and aid not in sent_cache:
                        author = aweme.get("author", {}).get("nickname", "抖音用户")
                        share = aweme.get("share_url", "无链接")
                        hit_kw = next(k for k in MONITOR_KEYWORDS if k in desc)
                        send_alert("抖音", f"@{author}", desc, share, hit_kw)
                        sent_cache.add(aid)
        except: pass

# ==================== 5. 百度热搜 ====================
def check_baidu_hot():
    try:
        r = requests.get("https://top.baidu.com/api/board?tab=realtime", timeout=10)
        for item in r.json().get("data", {}).get("cards", [{}])[0].get("content", [])[:20]:
            word = item.get("word", "")
            if is_hit(word) and word not in sent_cache:
                hit_kw = next(k for k in MONITOR_KEYWORDS if k in word)
                send_alert("百度热搜", f"冲榜中", word, f"https://www.baidu.com/s?wd={word}", hit_kw)
                sent_cache.add(word)
    except: pass

# ==================== 主任务 ====================
def job():
    print(f"[{time.strftime('%H:%M:%S')}] 多渠道30秒轮询中...")
    check_rss()
    check_weibo_search()
    check_focus_weibo()
    check_douyin()

schedule.every(30).seconds.do(job)
job()  # 启动即查一次
print("终极完整版已启动！5大渠道全覆盖 + 双推送 + 三保险代币查询")

while True:
    schedule.run_pending()
    time.sleep(1)
