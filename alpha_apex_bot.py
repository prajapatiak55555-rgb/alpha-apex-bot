import pandas as pd
import numpy as np
import requests
import datetime

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8973233256:AAGu3FsMR1C6hzr9xoPDD4W7f2NZtu_ijE0"
TELEGRAM_CHAT_ID = "8762446105"

def send_telegram_alert(message):
    """Telegram par unique format mein message bhejne ka function"""
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
    """Binance Public API se Crypto M5 candles fetch karne ke liye"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
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

def analyze_alpha_apex(df, pair_name):
    """AlphaApex Core Strategy Logic Engine"""
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
    
    # Volume condition (Spike > 1.2x SMA20)
    vol_spike = latest['volume'] > (1.2 * latest['vol_sma20'])
    
    # --- STRATEGY SIGNAL GENERATION ---
    # BUY Signal
    if latest['close'] > latest['ema20'] and vol_spike and lower_wick_ratio >= 0.40:
        sl_price = round(latest['low'] * 0.998, 2)
        tp_price = round(latest['close'] + (latest['close'] - sl_price) * 2.5, 2)
        
        return {
            "asset": pair_name,
            "type": "BUY / LONG 🟢",
            "price": latest['close'],
            "sl": sl_price,
            "tp": tp_price,
            "wick": round(lower_wick_ratio * 100, 1),
            "vol_mult": round(latest['volume'] / latest['vol_sma20'], 2)
        }
        
    # SELL Signal
    elif latest['close'] < latest['ema20'] and vol_spike and upper_wick_ratio >= 0.40:
        sl_price = round(latest['high'] * 1.002, 2)
        tp_price = round(latest['close'] - (sl_price - latest['close']) * 2.5, 2)
        
        return {
            "asset": pair_name,
            "type": "SELL / SHORT 🔴",
            "price": latest['close'],
            "sl": sl_price,
            "tp": tp_price,
            "wick": round(upper_wick_ratio * 100, 1),
            "vol_mult": round(upper_wick_ratio * 100, 1),
            "vol_mult": round(latest['volume'] / latest['vol_sma20'], 2)
        }
        
    return None

def main():
    print(f"[{datetime.datetime.now()}] Multi-Asset Scanning Started...")
    
    # Monitored Crypto Pairs
    crypto_symbols = {
        "BTCUSDT": "BTC/USD (Bitcoin)",
        "ETHUSDT": "ETH/USD (Ethereum)",
        "SOLUSDT": "SOL/USD (Solana)",
        "XRPUSDT": "XRP/USD (Ripple)"
    }
    
    # Scan Cryptos
    for symbol, display_name in crypto_symbols.items():
        try:
            df = fetch_crypto_candles(symbol)
            signal = analyze_alpha_apex(df, display_name)
            
            if signal:
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
                    f"Check MT5 Chart -> Confirm Context -> Execute Order.\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"⏰ *Time:* {datetime.datetime.now().strftime('%d %b %Y | %I:%M %p')} IST"
                )
                send_telegram_alert(msg)
            else:
                print(f"No setup for {display_name}")
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")
            
    print(f"[{datetime.datetime.now()}] Scan Complete.")

if __name__ == "__main__":
    main()
            
