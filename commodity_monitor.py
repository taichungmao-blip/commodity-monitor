import os
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 環境變數
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")

# 監控清單 (威剛已修正為 .TWO)
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
        latest_date = df['date'].max()
        today_df = df[df['date'] == latest_date]
        net = (today_df['buy'].sum() - today_df['sell'].sum()) / 1000
        return ("🟢" if net > 0 else "🔴"), int(net)
    except: return "⚪", 0

def run_full_monitor():
    # 1. 抓取全球趨勢指標 (BDRY, MU, Oil)
    bdry = yf.Ticker("BDRY").history(period="40d")
    mu = yf.Ticker("MU").history(period="5d")
    oil = yf.Ticker("CL=F").history(period="5d")
    
    # 趨勢定義
    bdi_trend_up = bdry['Close'].iloc[-1] > bdry['Close'].rolling(20).mean().iloc[-1]
    mu_trend_up = mu['Close'].pct_change().iloc[-1] > 0
    oil_trend_up = oil['Close'].iloc[-1] > oil['Close'].rolling(20).mean().iloc[-1]

    msg = f"🚀 **全產業策略監控報** ({datetime.now().strftime('%m/%d')})\n---\n"

    groups = [("💾 記憶體", MEMORY, mu_trend_up), ("🚢 散裝航運", SHIPPING, bdi_trend_up), ("🛢️ 塑化原料", PLASTIC, oil_trend_up)]
    
    for g_name, stocks, trend_up in groups:
        msg += f"**【{g_name}】**"
        for sid, name in stocks.items():
            # 威剛特殊處理：3260 使用 .TWO 格式
            yf_sid = f"{sid}.TW" if sid != "3260" else "3260.TWO"
            s_df = yf.Ticker(yf_sid).history(period="40d")
            
            if s_df.empty:
                msg += f"\n📌 {name}: 數據獲取異常"
                continue
            
            price = s_df['Close'].iloc[-1]
            ma20 = s_df['Close'].rolling(20).mean().iloc[-1]
            bias = ((price - ma20) / ma20) * 100
            icon, net = get_chip(sid)
            is_buy = (icon == "🟢")

            # --- 策略應對核心邏輯 ---
            if bias > 10: 
                strategy = "✋ 過熱不追"
            elif trend_up and is_buy: 
                strategy = "🚀 雙多共振"
            elif not trend_up and is_buy: 
                strategy = "💎 逆勢抄底"
            elif trend_up and not is_buy: 
                strategy = "⚠️ 警戒拉回"
            else: 
                strategy = "📉 雙弱觀望"

            msg += f"\n📌 {name}: {price:.1f} ({bias:+.1f}%) | 法人:{icon} | {strategy}"
        msg += "\n\n"

    # 3. 發送至 Discord
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg[:1900]})

if __name__ == "__main__":
    run_full_monitor()
