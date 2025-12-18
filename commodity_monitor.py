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

def fetch_safe(symbol, name):
    """安全抓取數據，失敗不崩潰"""
    try:
        print(f"正在抓取 {name} ({symbol})...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="60d")
        if df.empty or len(df) < 2: return None
        return df
    except Exception as e:
        print(f"{name} 抓取失敗: {e}")
        return None

def run_full_monitor():
    msg = f"🚀 **全產業綜合投資儀表板** ({datetime.now().strftime('%m/%d')})\n"
    
    # 1. 抓取全球指標
    bdry = fetch_safe("BDRY", "散裝指標")
    oil = fetch_safe("CL=F", "原油價格")
    mu = fetch_safe("MU", "美光科技")
    sox = fetch_safe("^SOX", "費半指數")

    # 組合標題摘要
    headers = []
    if bdry is not None: headers.append(f"🚢BDRY:{bdry['Close'].iloc[-1]:.1f}")
    if oil is not None: headers.append(f"🛢️油:{oil['Close'].iloc[-1]:.1f}")
    if mu is not None: headers.append(f"💻美光:{mu['Close'].pct_change().iloc[-1]*100:+.1f}%")
    msg += " | ".join(headers) + "\n---\n"

    # 2. 掃描族群
    groups = [("💾 記憶體電子", MEMORY), ("🚢 散裝航運", SHIPPING), ("🛢️ 塑化原料", PLASTIC)]
    
    for g_name, stocks in groups:
        msg += f"\n**【{g_name}】**"
        for sid, name in stocks.items():
            s_df = fetch_safe(f"{sid}.TW", name)
            if s_df is None:
                msg += f"\n📌 {name}: 數據獲取異常"
                continue
            
            price = s_df['Close'].iloc[-1]
            ma20 = s_df['Close'].rolling(20).mean().iloc[-1]
            bias = ((price - ma20) / ma20) * 100
            icon, net = get_chip(sid)
            
            msg += f"\n📌 {name}: {price:.1f} (乖離{bias:+.1f}%) | 法人:{icon}{net:+}"
            
            # 策略建議邏輯 (修正了之前的 AttributeError)
            if g_name == "💾 記憶體電子" and mu is not None:
                if mu['Close'].pct_change().iloc[-1] * 100 > 3 and icon == "🟢": msg += " ✨[美光強勢]"
            if g_name == "🚢 散裝航運" and bdry is not None:
                if bdry['Close'].iloc[-1] > bdry['Close'].rolling(20).mean().iloc[-1] and icon == "🟢": msg += " 🚀[雙多]"

    # 3. 發送
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg[:1900]})

if __name__ == "__main__":
    run_full_monitor()
