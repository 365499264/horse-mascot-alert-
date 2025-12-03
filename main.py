# main.py —— 两步推送版：先新闻，后代币（Render专用）

import feedparser, requests, time, schedule, hashlib, re, json, datetime
from bs4 import BeautifulSoup

# ==================== 配置 ====================
with open('config.json') as f:
    cfg = json.load(f)

BOT_TOKEN    = cfg["BOT_TOKEN"].strip()
CHAT_ID      = cfg["CHAT_ID"].strip()
WEIBO_COOKIE = cfg.get("WEIBO_COOKIE", "").strip()
BITQUERY_KEY = cfg.get("BITQUERY_API_KEY", "").strip()  # 免费key即可

MONITOR_GROUPS = {
    "马年吉祥物": ["马年吉祥物", "2026吉祥物", "生肖马吉祥物", "央视马年吉祥物", "春晚吉祥物", "丙午年吉祥物", "龙马精神", "马宝", "马馺馺", "馺馺"]
    # 继续加你想要的
}

FOCUS_USERS = { "1224379070": "央视春晚官方", "2656274875": "央视新闻", ... }  # 保持你之前的

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

# ==================== 查询 four.meme 最近2周代币（独立函数）===================
def query_four_meme(keyword):
    if not BITQUERY_KEY:
        return "BITQUERY_API_KEY 未配置，跳过代币查询"

    try:
        two_weeks_ago = (datetime.datetime.now() - datetime.timedelta(weeks=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        query = '''
        {
          EVM(network: bsc) {
            DEXTrades(
              limit: {count: 10}
              orderBy: {descendingByField: "Block_Time"}
              where: {
                Transaction: {Block: {Time: {since: "%s"}}}
                Trade: {
                  Dex: {ProtocolName: {in: ["fourmeme_v1", "four.meme"]}}
                  Currency: {Symbol: {icontains: "%s"}}
                }
              }
            ) {
              Trade {
                Currency { SmartContract { Address } Symbol Name }
                Price Market { MarketCap }
                Volume { AmountInUSD }
              }
              Block { Time }
            }
          }
        }
        ''' % (two_weeks_ago, keyword)

        r = requests.post("https://graphql.bitquery.io",
                          json={"query": query},
                          headers={"X-API-KEY": BITQUERY_KEY, "User-Agent": "Mozilla/5.0"},
                          timeout=15)

        if r.status_code != 200 or not r.text.strip():
            return "four.meme 查询失败（网络/限额）"

        data = r.json().get("data", {}).get("EVM", {}).get("DEXTrades", [])
        if not data:
            return f"最近2周内未发现包含 “{keyword}” 的新代币"

        lines = []
        for t in data[:6]:
            ca = t["Trade"]["Currency"]["SmartContract"]["Address"]
            name = t["Trade"]["Currency"]["Name"]
            symbol = t["Trade"]["Currency"]["Symbol"]
            price = t["Trade"]["Price"] or 0
            mcap = t["Trade"]["Market"]["MarketCap"] or 0
            launch = t["Block"]["Time"][:10]
            lines.append(f"• {name} ({symbol})\n  发射: {launch}\n  CA: {ca}\n  价格 ${price:.10f} | 市值 ${mcap:,.0f}\n  https://four.meme/token/{ca}")

        return "【抢跑代币】“" + keyword + "”相关新币（最近2周）:\n\n" + "\n\n".join(lines)

    except Exception as e:
        return f"代币查询出错: {str(e)[:80]}"

# ==================== 所有监控函数：先发新闻，3秒后发代币 ====================
def trigger_alert(source, title, content, url, hit_kw):
    uid = hashlib.md5(url.encode()).hexdigest()
    if uid in sent_cache: return
    sent_cache.add(uid)

    # 第一条：纯新闻
    news = f"【{source}官宣】\n命中关键词：{hit_kw}\n{title}\n{content.strip()[:600]}\n\n原文：{url}"
    tg(news)

    # 第二条：延迟3秒发代币（避免被当成刷屏）
    time.sleep(3)
    token_msg = query_four_meme(hit_kw)
    tg(token_msg)

# 示例：所有check函数里命中后调用 trigger_alert 即可（下面以微博为例）
def check_weibo():
    # ... 你的原有抓取逻辑
    # 命中后这样调用：
    # trigger_alert("微博", f"@{nickname}", text, link, hit_kw)

# 其他平台同理（rss、抖音、百度热搜）都改成 trigger_alert 即可

# ==================== 每30秒轮询 ====================
def job():
    print(f"[{time.strftime('%H:%M:%S')}] 30秒轮询中...", flush=True)
    # check_rss()
    # check_weibo()
    # check_douyin()
    # check_baidu_hot()

schedule.every(30).seconds.do(job)
job()
print("双推送版已启动：先新闻 → 3秒后代币，永不混淆！")

while True:
    schedule.run_pending()
    time.sleep(1)
