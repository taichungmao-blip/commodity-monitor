import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 環境變數
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")

# 監控清單
SHIPPING = {"2606": "裕民", "2637": "慧洋-KY", "2605": "新興"}
PLASTIC = {"1301": "台塑", "1303": "南亞", "1304": "台聚", "1308": "亞聚"}
MEMORY = {"2408": "南亞科", "2344": "華邦電", "3260": "威剛"}

def get_chip(sid):
    url = "https://api.finmindtrade.com/api/v4/data"
    start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    params = {"dataset": "TaiwanStockInstitutionalInvestorsBuySell", "data_id": sid, "start_date": start, "token": FINMIND_TOKEN}
    try:
        resp = requests.get(url, params=params).json()
        df = pd.DataFrame(resp["data"])
        if df.empty: return "⚪", 0
        latest = df[df['date'] == df['date'].max()]
        net = (latest['buy'].sum() - latest['sell'].sum()) / 1000
        return ("🟢" if net > 0 else "🔴"), int(net)
    except: return "⚪", 0

def fetch_safe_data(symbol, period="60d"):
    """安全抓取數據，失敗時回傳 None 防止崩潰"""
    try:
        data = yf.Ticker(symbol).history(period=period)
        if data.empty: return None
        return data
    except: return None

def run_full_monitor():
    msg = f"🚀 **全產業綜合投資儀表板** ({datetime.now().strftime('%m/%d')})\n"
    
    # 1. 抓取全球指標 (加入防錯)
    bdry = fetch_safe_data("BDRY") # 散裝替代指標
    oil = fetch_safe_data("CL=F")   # 原油
    mu = fetch_safe_data("MU")     # 美光
    sox = fetch_safe_data("^SOX")  # 費半

    # 指標狀態摘要
    indicators = []
    if bdry is not None: indicators.append(f"🚢BDRY:{bdry['Close'].iloc[-1]:.1f}")
    if oil is not None: indicators.append(f"🛢️油價:{oil['Close'].iloc[-1]:.1f}")
    if mu is not None: indicators.append(f"💻美光:{mu['Close'].pct_change().iloc[-1]*100:+.1f}%")
    msg += " | ".join(indicators) + "\n---\n"

    # 2. 掃描三大族群
    groups = [("💾 記憶體電子", MEMORY), ("🚢 散裝航運", SHIPPING), ("🛢️ 塑化原料", PLASTIC)]
    
    for g_name, stocks in groups:
        msg += f"\n**【{g_name}】**"
        for sid, name in stocks.items():
            s_data = fetch_safe_data(f"{sid}.TW")
            if s_data is None:
                msg += f"\n📌{name}: 數據讀取中斷"
                continue
            
            price = s_data['Close'].iloc[-1]
            ma20 = s_data['Close'].rolling(20).mean().iloc[-1]
            bias = ((price - ma20) / ma20) * 100
            icon, net = get_chip(sid)
            
            msg += f"\n📌{name}: {price:.1f} ({bias:+.1f}%) | 法人:{icon}{net:+}"
            
            # 策略建議
            if g_name == "💾 記憶體電子" and mu is not None and mu.history(period="2d")['Close'].pct_change().iloc[-1]*100 > 3:
                msg += " ✨[美光帶動]"
            if g_name == "🚢 散裝航運" and bdry is not None and bdry['Close'].iloc[-1] > bdry['Close'].rolling(20).mean().iloc[-1]:
                if icon == "🟢": msg += " 🚀[雙多]"

    # 3. 發送 (Discord 訊息過長會自動截斷處理)
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg[:2000]})

if __name__ == "__main__":
    run_full_monitor()
