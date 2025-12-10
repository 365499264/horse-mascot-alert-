import requests
import json
import re

# ==================== 配置区 ====================
API_URL = "https://api.getoneapi.com/api/weibo/fetch_user_post"

# 如果这个接口需要 Authorization header，请在这里填入你的 key
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer qZFrs8gWuh88kglbOqkQrleYJnO2PGXG0e2NIQAePxyEB2hxzUqdFbq6zUjl10Bi",   # 如果需要就取消注释并填入
}

# 要查询的用户（这里以你示例中的春晚账号为例）
payload = {
    "uid": "",                                          # 可以留空，接口会从 share_text 解析
    "share_text": "https://weibo.com/u/3506728370",    # 用户主页链接
    "since_id": ""                                      # 第一次请求留空
}
# ================================================


def get_first_weibo():
    resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
    
    if resp.status_code != 200:
        print(f"请求失败，状态码：{resp.status_code}")
        print(resp.text)
        return
    
    data = resp.json()
    
    # 简单判断接口返回是否成功
    if data.get("code") != 200:
        print("接口返回错误：", data.get("message"))
        return
    
    cards = data["data"]["data"]["cards"]
    if not cards:
        print("没有获取到微博数据")
        return
    
    first_card = cards[0]          # 第一条就是最新的那条
    mblog = first_card["mblog"]
    
    # 1. 微博正文（已经带话题、@、链接等原始 HTML 形式）
    text = mblog["text"]
    
    # 2. 微博的 bid（短链后缀）
    bid = mblog["bid"]
    
    # 3. 构造几类常用永久链接（任选其一即可）
    # 移动端链接（最常用）
    m_link = f"https://m.weibo.cn/status/{bid}"
    # PC 端链接
    pc_link = f"https://weibo.com/{mblog['user']['id']}/{bid}"
    # scheme 字段里也自带一个（通常是移动端）
    scheme_link = first_card.get("scheme", "")
    
    print("=== 第一条微博 ===")
    print("发布者   :", mblog["user"]["screen_name"])
    print("发布时间 :", mblog["created_at"])
    print("正文     :\n", text)
    print("\n链接（移动端） :", m_link)
    print("链接（PC端）   :", pc_link)
    if scheme_link:
        print("链接（scheme）:", scheme_link)
    print("-" * 50)


if __name__ == "__main__":
    get_first_weibo()
