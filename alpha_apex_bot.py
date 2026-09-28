import pandas as pd
import numpy as np
import requests
import datetime
import yfinance as yf

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8973233256:AAGu3FsMR1C6hzr9xoPDD4W7f2NZtu_ijE0"
TELEGRAM_CHAT_ID = "8762446105"

def send_telegram_alert(message):
    """Telegram alert sender"""
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

def fetch_crypto_candles(symbol):
    """Fetch M5 candles from Binance for Cryptos"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
    res = requests.get(url, timeout=10)
    data = res.json()
    
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    return df

def fetch_traditional_candles(ticker_symbol):
    """Fetch M5 candles via Yahoo Finance for Gold & Indices"""
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="1d", interval="5m")
    if df.empty:
        return None
    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 
        'Low': 'low', 'Close': 'close', 'Volume': 'volume'
    })
    return df

def analyze_alpha_apex(df, pair_name):
    """AlphaApex Core Strategy Logic Engine"""
    if df is None or len(df) < 20:
        return None
        
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['vol_sma20'] = df['volume'].rolling(window=20).mean()
    
    latest = df.iloc[-1]
    
    candle_range = latest['high'] - latest['low']
    if candle_range == 0:
        return None
        
    lower_wick = min(latest['open'], latest['close']) - latest['low']
    upper_wick = latest['high'] - max(latest['open'], latest['close'])
    
    lower_wick_ratio = lower_wick / candle_range
    upper_wick_ratio = upper_wick / candle_range
    
    vol_avg = latest['vol_sma20'] if latest['vol_sma20'] > 0 else 1
    vol_spike = latest['volume'] > (1.2 * vol_avg)
    
    # BUY Signal
    if latest['close'] > latest['ema20'] and vol_spike and lower_wick_ratio >= 0.40:
        sl_price = round(latest['low'] * 0.998, 2)
        tp_price = round(latest['close'] + (latest['close'] - sl_price) * 2.5, 2)
        
        return {
            "asset": pair_name,
            "type": "BUY / LONG 🟢",
            "price": round(latest['close'], 2),
            "sl": sl_price,
            "tp": tp_price,
            "wick": round(lower_wick_ratio * 100, 1),
            "vol_mult": round(latest['volume'] / vol_avg, 2)
        }
        
    # SELL Signal
    elif latest['close'] < latest['ema20'] and vol_spike and upper_wick_ratio >= 0.40:
        sl_price = round(latest['high'] * 1.002, 2)
        tp_price = round(latest['close'] - (sl_price - latest['close']) * 2.5, 2)
        
        return {
            "asset": pair_name,
            "type": "SELL / SHORT 🔴",
            "price": round(latest['close'], 2),
            "sl": sl_price,
            "tp": tp_price,
            "wick": round(upper_wick_ratio * 100, 1),
            "vol_mult": round(latest['volume'] / vol_avg, 2)
        }
        
    return None

def main():
    print(f"[{datetime.datetime.now()}] Scanning All Assets...")
    
    # 1. Crypto Pairs
    crypto_symbols = {
        "BTCUSDT": "BTC/USD (Bitcoin)",
        "ETHUSDT": "ETH/USD (Ethereum)",
        "SOLUSDT": "SOL/USD (Solana)",
        "XRPUSDT": "XRP/USD (Ripple)"
    }
    
    # 2. Gold & Major US Indices
    traditional_assets = {
        "GC=F": "XAU/USD (Gold Spot)",
        "^DJI": "US30 (Dow Jones)",
        "^IXIC": "NAS100 (Nasdaq 100)"
    }
    
    # Scan Crypto
    for symbol, display_name in crypto_symbols.items():
        try:
            df = fetch_crypto_candles(symbol)
            signal = analyze_alpha_apex(df, display_name)
            if signal:
                send_signal_alert(signal)
            else:
                print(f"No setup for {display_name}")
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            
    # Scan Gold & Indices
    for ticker, display_name in traditional_assets.items():
        try:
            df = fetch_traditional_candles(ticker)
            signal = analyze_alpha_apex(df, display_name)
            if signal:
                send_signal_alert(signal)
            else:
                print(f"No setup for {display_name}")
        except Exception as e:
            print(f"Error scanning {display_name}: {e}")

def send_signal_alert(signal):
    msg = (
        f"⚡ *[ ALPHA-APEX INSTITUTIONAL ALERT ]* ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Asset:* `{signal['asset']}` (M5)\n"
        f"🎯 *Direction:* {signal['type']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 *Entry Price:* `${signal['price']}`\n"
        f"🛡️ *Stop Loss:* `${signal['sl']}`\n"
        f"🎯 *Target TP:* `${signal['tp']}`\n"
        f"⚖️ *Risk-Reward:* 1 : 2.50\n\n"
        f"📈 *ANALYSIS METRICS*\n"
        f"• Wick Absorption : `{signal['wick']}%` 🎯\n"
        f"• Volume Spike    : `{signal['vol_mult']}x` SMA20 💥\n\n"
        f"⚠️ *ACTION REQUIRED:*\n"
        f"Open Exness MT5 -> Confirm Chart -> Execute Position.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ *Time:* {datetime.datetime.now().strftime('%d %b %Y | %I:%M %p')} IST"
    )
    send_telegram_alert(msg)

if __name__ == "__main__":
    main()
    
