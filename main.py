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

MONITOR_GROUPS = {
    "马年吉祥物": ["马年吉祥物", "2026吉祥物", "生肖马吉祥物", "央视马年吉祥物", "春晚吉祥物", "丙午年吉祥物", "龙马精神", "马宝", "马馺馺", "吉祥马", "吉祥物"]
}

FOCUS_USERS = {
    "1224379070": "央视春晚官方",
    "3506728370": "春晚",
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

# ==================== 示例监控（微博重点账号）===================
def check_weibo():
    headers = {"User-Agent": "Mozilla/5.0", "Cookie": WEIBO_COOKIE}
    for uid, name in FOCUS_USERS.items():
        api = f"https://m.weibo.cn/api/container/getIndex?containerid=107603{uid}"
        try:
            r = requests.get(api, headers=headers, timeout=10)
            for card in r.json().get("data", {}).get("cards", []):
                if "mblog" not in card: continue
                b = card["mblog"]
                text = re.sub('<[^<]+?>', '', b["text"])
                g, kw = match_keyword(text)
                link = f"https://m.weibo.cn/detail/{b['id']}"
                if g or uid == "1224379070":  # 央视春晚官方全推
                    trigger_alert("重点账号" if uid != "1224379070" else "央视春晚官方",
                                  f"@{b['user']['screen_name']}", text, link, kw or "官方动态")
        except:
            pass

# ==================== 主循环 ====================
def job():
    print(f"[{time.strftime('%H:%M:%S')}] 30秒轮询中...")
    check_weibo()
    # 继续加 check_rss(), check_douyin() 等

schedule.every(30).seconds.do(job)
job()
print("终极修复版已启动！三保险代币查询 + 双推送，无任何语法错误！")

while True:
    schedule.run_pending()
    time.sleep(1)
