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
        data = requests.get(url, params=params).json()["data"]
        df = pd.DataFrame(data)
        latest = df[df['date'] == df['date'].max()]
        net = (latest['buy'].sum() - latest['sell'].sum()) / 1000
        return ("🟢" if net > 0 else "🔴"), int(net)
    except: return "⚪", 0

def run_full_monitor():
    # 1. 抓取全球核心指標
    print("正在更新全球指標數據...")
    bdry = yf.Ticker("BDRY").history(period="5d") # 散裝
    oil = yf.Ticker("CL=F").history(period="5d")  # 塑化
    mu = yf.Ticker("MU").history(period="5d")     # 記憶體龍頭
    sox = yf.Ticker("^SOX").history(period="5d")  # 半導體大盤

    # 計算變動
    mu_chg = mu['Close'].pct_change().iloc[-1] * 100
    sox_chg = sox['Close'].pct_change().iloc[-1] * 100
    oil_chg = oil['Close'].pct_change().iloc[-1] * 100

    msg = f"🚀 **全產業綜合投資儀表板** ({datetime.now().strftime('%m/%d')})\n"
    msg += f"💻 電子: 美光 {mu_chg:+.1f}% | 費半 {sox_chg:+.1f}%\n"
    msg += f"🚢 航運: BDRY {bdry['Close'].iloc[-1]:.2f}\n"
    msg += f"🛢️ 塑化: 原油 {oil_chg:+.1f}%\n"
    msg += "---"

    # 2. 掃描三大族群
    groups = [("💾 記憶體電子", MEMORY), ("🚢 散裝航運", SHIPPING), ("🛢️ 塑化原料", PLASTIC)]
    
    for g_name, stocks in groups:
        msg += f"\n\n**【{g_name}】**"
        for sid, name in stocks.items():
            s_data = yf.Ticker(f"{sid}.TW").history(period="40d")
            price = s_data['Close'].iloc[-1]
            ma20 = s_data['Close'].rolling(20).mean().iloc[-1]
            bias = ((price - ma20) / ma20) * 100
            icon, net = get_chip(sid)
            
            msg += f"\n📌{name}: {price:.1f} (乖離{bias:+.1f}%) | 法人:{icon}{net:+}"
            
            # 智慧策略建議
            if g_name == "💾 記憶體電子" and mu_chg > 3 and icon == "🟢":
                msg += " ✨[美光帶動]"
            if g_name == "🚢 散裝航運" and bdry['Close'].iloc[-1] > bdry['Close'].rolling(20).mean().iloc[-1] and icon == "🟢":
                msg += " 🚀[雙多共振]"
            if bias < -10:
                msg += " 📉[乖離過大-注意反彈]"

    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

if __name__ == "__main__":
    run_full_monitor()
