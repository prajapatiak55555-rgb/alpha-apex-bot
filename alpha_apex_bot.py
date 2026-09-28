import pandas as pd
import numpy as np
import requests
import datetime
import yfinance as yf

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8973233256:AAGu3FsMR1C6hzr9xoPDD4W7f2NZtu_ijE0"
TELEGRAM_CHAT_ID = "8762446105"

# Account Risk Config for Lot Size Calculation
ACCOUNT_RISK_USD = 10.0  # Change according to your risk preference per trade ($10, $20, etc.)

# Memory to store last alert time to prevent Telegram spam
LAST_ALERTS = {}

def send_telegram_alert(message):
    """Telegram alert sender function"""
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

def is_active_session(is_crypto=False):
    """Filter non-crypto assets during off-market/low-volume hours"""
    if is_crypto:
        return True  # Crypto markets run 24/7
    
    # Check current time in UTC/IST for High Volatility Sessions
    # London: 13:00 - 17:00 IST | New York: 18:30 - 23:30 IST
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    current_hour = now_utc.hour
    
    # Active Forex/Index hours in UTC (approx 07:00 to 20:00 UTC)
    if 7 <= current_hour <= 20:
        return True
    return False

def calculate_lot_size(entry, sl, asset_name):
    """Calculate recommended MT5 position size for defined risk"""
    sl_distance = abs(entry - sl)
    if sl_distance == 0:
        return "N/A"
    
    # Rough lot sizing calculation logic based on asset type
    if "BTC" in asset_name:
        lots = ACCOUNT_RISK_USD / sl_distance
        return f"`{round(lots, 3)}` BTC"
    elif "Gold" in asset_name or "XAU" in asset_name:
        # 1 lot Gold = 100 oz ($1 move = $100 per 1.0 lot)
        lots = ACCOUNT_RISK_USD / (sl_distance * 100)
        return f"`{max(0.01, round(lots, 2))}` Lots"
    else:
        lots = ACCOUNT_RISK_USD / (sl_distance * 10)
        return f"`{max(0.01, round(lots, 2))}` Lots"

def fetch_crypto_candles(symbol, interval="5m"):
    """Fetch candles from Binance"""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=50"
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

def fetch_traditional_candles(ticker_symbol, interval="5m"):
    """Fetch candles from Yahoo Finance"""
    ticker = yf.Ticker(ticker_symbol)
    period = "1d" if interval in ["5m", "15m"] else "5d"
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        return None
    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 
        'Low': 'low', 'Close': 'close', 'Volume': 'volume'
    })
    return df

def analyze_alpha_apex(df_m5, df_m15, pair_name):
    """Core Strategy Logic with Multi-Timeframe Confluence"""
    if df_m5 is None or len(df_m5) < 20 or df_m15 is None or len(df_m15) < 20:
        return None
        
    # Moving Averages & Volume Metrics
    df_m5['ema20'] = df_m5['close'].ewm(span=20, adjust=False).mean()
    df_m5['vol_sma20'] = df_m5['volume'].rolling(window=20).mean()
    df_m15['ema20'] = df_m15['close'].ewm(span=20, adjust=False).mean()
    
    latest_m5 = df_m5.iloc[-1]
    latest_m15 = df_m15.iloc[-1]
    
    candle_range = latest_m5['high'] - latest_m5['low']
    if candle_range == 0:
        return None
        
    lower_wick = min(latest_m5['open'], latest_m5['close']) - latest_m5['low']
    upper_wick = latest_m5['high'] - max(latest_m5['open'], latest_m5['close'])
    
    lower_wick_ratio = lower_wick / candle_range
    upper_wick_ratio = upper_wick / candle_range
    
    vol_avg = latest_m5['vol_sma20'] if latest_m5['vol_sma20'] > 0 else 1
    vol_spike = latest_m5['volume'] > (1.2 * vol_avg)
    
    # Trend Confluence (M5 and M15 must agree)
    m5_bullish = latest_m5['close'] > latest_m5['ema20']
    m15_bullish = latest_m15['close'] > latest_m15['ema20']
    
    m5_bearish = latest_m5['close'] < latest_m5['ema20']
    m15_bearish = latest_m15['close'] < latest_m15['ema20']
    
    # --- BUY SIGNAL ---
    if m5_bullish and m15_bullish and vol_spike and lower_wick_ratio >= 0.40:
        sl_price = round(latest_m5['low'] * 0.998, 2)
        tp_price = round(latest_m5['close'] + (latest_m5['close'] - sl_price) * 2.5, 2)
        
        return {
            "asset": pair_name,
            "type": "BUY / LONG 🟢",
            "price": round(latest_m5['close'], 2),
            "sl": sl_price,
            "tp": tp_price,
            "wick": round(lower_wick_ratio * 100, 1),
            "vol_mult": round(latest_m5['volume'] / vol_avg, 2),
            "mtf": "M5 + M15 Bullish Alignment ✅"
        }
        
    # --- SELL SIGNAL ---
    elif m5_bearish and m15_bearish and vol_spike and upper_wick_ratio >= 0.40:
        sl_price = round(latest_m5['high'] * 1.002, 2)
        tp_price = round(latest_m5['close'] - (sl_price - latest_m5['close']) * 2.5, 2)
        
        return {
            "asset": pair_name,
            "type": "SELL / SHORT 🔴",
            "price": round(latest_m5['close'], 2),
            "sl": sl_price,
            "tp": tp_price,
            "wick": round(upper_wick_ratio * 100, 1),
            "vol_mult": round(latest_m5['volume'] / vol_avg, 2),
            "mtf": "M5 + M15 Bearish Alignment ✅"
        }
        
    return None

def process_asset(display_name, fetch_func, symbol, is_crypto=False):
    """Processes asset scanning and prevents duplicate spam alerts"""
    if not is_active_session(is_crypto):
        print(f"Skipping {display_name}: Market session inactive.")
        return

    # Check Anti-Spam Cool-off (20 Minutes threshold)
    now = datetime.datetime.now()
    if display_name in LAST_ALERTS:
        time_diff = (now - LAST_ALERTS[display_name]).total_seconds() / 60
        if time_diff < 20:
            print(f"Skipping {display_name}: Cooldown active ({int(20 - time_diff)} mins left)")
            return

    df_m5 = fetch_func(symbol, interval="5m")
    df_m15 = fetch_func(symbol, interval="15m")
    
    signal = analyze_alpha_apex(df_m5, df_m15, display_name)
    
    if signal:
        LAST_ALERTS[display_name] = now
        lot_guide = calculate_lot_size(signal['price'], signal['sl'], display_name)
        
        msg = (
            f"⚡ *[ ALPHA-APEX INSTITUTIONAL ALERT ]* ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Asset:* `{signal['asset']}`\n"
            f"🎯 *Direction:* {signal['type']}\n"
            f"🧬 *Confluence:* `{signal['mtf']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *Entry Price:* `${signal['price']}`\n"
            f"🛡️ *Stop Loss:* `${signal['sl']}`\n"
            f"🎯 *Target TP:* `${signal['tp']}`\n"
            f"⚖️ *Risk-Reward:* 1 : 2.50\n"
            f"💰 *Calculated Size:* {lot_guide} (for ${int(ACCOUNT_RISK_USD)} Risk)\n\n"
            f"📈 *ANALYSIS METRICS*\n"
            f"• Wick Absorption : `{signal['wick']}%` 🎯\n"
            f"• Volume Spike    : `{signal['vol_mult']}x` SMA20 💥\n\n"
            f"⚠️ *ACTION REQUIRED:*\n"
            f"Open Exness MT5 -> Check Chart -> Execute Trade.\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Time:* {datetime.datetime.now().strftime('%d %b %Y | %I:%M %p')} IST"
        )
        send_telegram_alert(msg)
    else:
        print(f"No high-confluence setup for {display_name}")

def main():
    print(f"[{datetime.datetime.now()}] Full Strategy Scan Started...")
    
    crypto_symbols = {
        "BTCUSDT": "BTC/USD (Bitcoin)",
        "ETHUSDT": "ETH/USD (Ethereum)",
        "SOLUSDT": "SOL/USD (Solana)",
        "XRPUSDT": "XRP/USD (Ripple)"
    }
    
    traditional_assets = {
        "GC=F": "XAU/USD (Gold Spot)",
        "^DJI": "US30 (Dow Jones)",
        "^IXIC": "NAS100 (Nasdaq 100)"
    }
    
    # Scan Cryptos
    for symbol, name in crypto_symbols.items():
        try:
            process_asset(name, fetch_crypto_candles, symbol, is_crypto=True)
        except Exception as e:
            print(f"Error scanning {name}: {e}")
            
    # Scan Gold & Indices
    for ticker, name in traditional_assets.items():
        try:
            process_asset(name, fetch_traditional_candles, ticker, is_crypto=False)
        except Exception as e:
            print(f"Error scanning {name}: {e}")

if __name__ == "__main__":
    main()
    
