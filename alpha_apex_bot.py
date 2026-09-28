import requests
import datetime
import pandas as pd
import numpy as np

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8973233256:AAGu3FsMR1C6hzr9xoPDD4W7f2NZtu_ijE0"
TELEGRAM_CHAT_ID = "8762446105"

def send_telegram_alert(message):
    """Telegram par signal message bhejne ka function"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("Telegram signal sent successfully!")
        else:
            print(f"Failed to send Telegram signal: {res.text}")
    except Exception as e:
        print(f"Telegram error: {e}")

def fetch_market_candles():
    """Binance Public API se BTCUSDT M5 candles fetch karne ke liye"""
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=50"
    res = requests.get(url, timeout=10)
    data = res.json()
    
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

def analyze_alpha_apex(df):
    """AlphaApex Core Strategy Logic Engine"""
    # 1. Moving Averages
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['vol_sma20'] = df['volume'].rolling(window=20).mean()
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Candle metrics
    candle_range = latest['high'] - latest['low']
    if candle_range == 0:
        return None
        
    lower_wick = min(latest['open'], latest['close']) - latest['low']
    upper_wick = latest['high'] - max(latest['open'], latest['close'])
    
    lower_wick_ratio = lower_wick / candle_range
    upper_wick_ratio = upper_wick / candle_range
    
    # Volume condition (Spike > 1.2x SMA20)
    vol_spike = latest['volume'] > (1.2 * latest['vol_sma20'])
    
    # --- STRATEGY SIGNAL GENERATION ---
    # BUY Signal: Bullish Trend + Volume Spike + >40% Lower Wick Absorption
    if latest['close'] > latest['ema20'] and vol_spike and lower_wick_ratio >= 0.40:
        sl_price = round(latest['low'] * 0.998, 2)
        tp_price = round(latest['close'] + (latest['close'] - sl_price) * 2.5, 2)
        
        return {
            "type": "BUY 🟢",
            "price": latest['close'],
            "sl": sl_price,
            "tp": tp_price,
            "wick": round(lower_wick_ratio * 100, 1),
            "vol_mult": round(latest['volume'] / latest['vol_sma20'], 2)
        }
        
    # SELL Signal: Bearish Trend + Volume Spike + >40% Upper Wick Absorption
    elif latest['close'] < latest['ema20'] and vol_spike and upper_wick_ratio >= 0.40:
        sl_price = round(latest['high'] * 1.002, 2)
        tp_price = round(latest['close'] - (sl_price - latest['close']) * 2.5, 2)
        
        return {
            "type": "SELL 🔴",
            "price": latest['close'],
            "sl": sl_price,
            "tp": tp_price,
            "wick": round(upper_wick_ratio * 100, 1),
            "vol_mult": round(latest['volume'] / latest['vol_sma20'], 2)
        }
        
    return None

def main():
    print(f"[{datetime.datetime.now()}] Analyzing Market Conditions...")
    try:
        df = fetch_market_candles()
        signal = analyze_alpha_apex(df)
        
        if signal:
            msg = (
                f"🚨 *ALPHA APEX TRADING SIGNAL* 🚨\n\n"
                f"**Asset:** BTCUSD (M5)\n"
                f"**Signal Type:** {signal['type']}\n"
                f"**Entry Price:** ${signal['price']}\n"
                f"**Suggested SL:** ${signal['sl']}\n"
                f"**Suggested TP (2.5 RR):** ${signal['tp']}\n\n"
                f"📊 *Metrics:* Wick Absorption: {signal['wick']}% | Volume: {signal['vol_mult']}x SMA\n"
                f"📌 *Action:* Exness MT5 app khol kar confirmation ke sath trade place karein."
            )
            send_telegram_alert(msg)
        else:
            print("No high-probability AlphaApex setup detected on this candle.")
            
    except Exception as e:
        print(f"Execution Error: {e}")

if __name__ == "__main__":
    main()
    
