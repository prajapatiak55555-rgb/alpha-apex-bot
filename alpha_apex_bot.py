import pandas as pd
import numpy as np
import requests
import datetime
import yfinance as yf

# ==========================================
# ⚙️ TELEGRAM & RISK CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "8973233256:AAGu3FsMR1C6hzr9xoPDD4W7f2NZtu_ijE0"
TELEGRAM_CHAT_ID = "8762446105"

ACCOUNT_RISK_USD = 10.0  # Risk amount per trade ($10 USD)
LAST_ALERTS = {}         # Cooldown tracker to prevent spam

def send_telegram_alert(message):
    """Delivers high-confluence institutional alerts to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ Telegram alert sent successfully!")
        else:
            print(f"❌ Telegram Error: {res.text}")
    except Exception as e:
        print(f"⚠️ Telegram Connection Exception: {e}")

# ==========================================
# 🕒 SESSION & RISK CALCULATORS
# ==========================================
def is_active_session(is_crypto=False):
    """Filters low-volatility Asian/Off-market hours for Gold & Indices"""
    if is_crypto:
        return True
    
    # Active Forex & Index Trading Hours (UTC)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    current_hour = now_utc.hour
    
    # Active Trading Window: London (07:00 UTC) to New York Close (20:00 UTC)
    return 7 <= current_hour <= 20

def calculate_lot_size(entry, sl, asset_name):
    """Calculates precision position size for exact defined USD Risk"""
    sl_distance = abs(entry - sl)
    if sl_distance == 0:
        return "N/A"
    
    if "BTC" in asset_name:
        lots = ACCOUNT_RISK_USD / sl_distance
        return f"`{round(lots, 3)}` BTC"
    elif "Gold" in asset_name or "XAU" in asset_name:
        # 1.00 Lot Gold = 100 oz ($1 price move = $100 profit/loss)
        lots = ACCOUNT_RISK_USD / (sl_distance * 100)
        return f"`{max(0.01, round(lots, 2))}` Lots"
    else:
        lots = ACCOUNT_RISK_USD / (sl_distance * 10)
        return f"`{max(0.01, round(lots, 2))}` Lots"

# ==========================================
# 🧬 INSTITUTIONAL ENGINE (SMC / FVG)
# ==========================================
def detect_smc_confluence(df):
    """Detects Liquidity Sweeps (Stop Hunts) and Fair Value Gaps (FVG)"""
    if len(df) < 15:
        return {"fvg_bullish": False, "fvg_bearish": False, "sweep_low": False, "sweep_high": False}
    
    # 1. Fair Value Gap (3-Candle Imbalance)
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    fvg_bullish = c3['low'] > c1['high']
    fvg_bearish = c3['high'] < c1['low']
    
    # 2. Liquidity Sweep (Sweeping prior 12 candles range)
    prev_low = df.iloc[-14:-1]['low'].min()
    prev_high = df.iloc[-14:-1]['high'].max()
    
    sweep_low = (c3['low'] < prev_low) and (c3['close'] > prev_low)
    sweep_high = (c3['high'] > prev_high) and (c3['close'] < prev_high)
    
    return {
        "fvg_bullish": fvg_bullish,
        "fvg_bearish": fvg_bearish,
        "sweep_low": sweep_low,
        "sweep_high": sweep_high
    }

# ==========================================
# 📊 DATA FETCHERS
# ==========================================
def fetch_crypto_candles(symbol, interval="5m"):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=50"
    res = requests.get(url, timeout=10)
    data = res.json()
    df = pd.DataFrame(data, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    return df

def fetch_traditional_candles(ticker_symbol, interval="5m"):
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="1d" if interval in ["5m", "15m"] else "5d", interval=interval)
    if df.empty:
        return None
    return df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})

# ==========================================
# 👑 SUPER PRO MAX CORE STRATEGY LOGIC
# ==========================================
def analyze_super_pro_max(df_m5, df_m15, pair_name):
    if df_m5 is None or len(df_m5) < 20 or df_m15 is None or len(df_m15) < 20:
        return None
        
    # Moving Averages & Volume Metrics
    df_m5['ema20'] = df_m5['close'].ewm(span=20, adjust=False).mean()
    df_m5['vol_sma20'] = df_m5['volume'].rolling(window=20).mean()
    df_m15['ema20'] = df_m15['close'].ewm(span=20, adjust=False).mean()
    
    latest_m5, latest_m15 = df_m5.iloc[-1], df_m15.iloc[-1]
    candle_range = latest_m5['high'] - latest_m5['low']
    if candle_range == 0:
        return None
        
    lower_wick = (min(latest_m5['open'], latest_m5['close']) - latest_m5['low']) / candle_range
    upper_wick = (latest_m5['high'] - max(latest_m5['open'], latest_m5['close'])) / candle_range
    vol_avg = latest_m5['vol_sma20'] if latest_m5['vol_sma20'] > 0 else 1
    vol_spike = latest_m5['volume'] > (1.2 * vol_avg)
    
    # SMC Confluence Check
    smc = detect_smc_confluence(df_m5)
    
    # --- BUY / LONG SETUP ---
    if (latest_m5['close'] > latest_m5['ema20']) and (latest_m15['close'] > latest_m15['ema20']) and vol_spike and lower_wick >= 0.40:
        sl_price = round(latest_m5['low'] * 0.998, 2)
        risk = latest_m5['close'] - sl_price
        tp1 = round(latest_m5['close'] + (risk * 1.5), 2)
        tp2 = round(latest_m5['close'] + (risk * 2.5), 2)
        
        tags = ["M5/M15 EMA Alignment ✅"]
        if smc['sweep_low']: tags.append("Liquidity Sweep (Stop Hunt) 🎯")
        if smc['fvg_bullish']: tags.append("Fair Value Gap (FVG) Zone 🔥")
        
        return {
            "asset": pair_name, "type": "BUY / LONG 🟢", "price": round(latest_m5['close'], 2),
            "sl": sl_price, "tp1": tp1, "tp2": tp2, "wick": round(lower_wick * 100, 1),
            "vol_mult": round(latest_m5['volume'] / vol_avg, 2), "confluence": " | ".join(tags)
        }
        
    # --- SELL / SHORT SETUP ---
    elif (latest_m5['close'] < latest_m5['ema20']) and (latest_m15['close'] < latest_m15['ema20']) and vol_spike and upper_wick >= 0.40:
        sl_price = round(latest_m5['high'] * 1.002, 2)
        risk = sl_price - latest_m5['close']
        tp1 = round(latest_m5['close'] - (risk * 1.5), 2)
        tp2 = round(latest_m5['close'] - (risk * 2.5), 2)
        
        tags = ["M5/M15 EMA Alignment ✅"]
        if smc['sweep_high']: tags.append("Liquidity Sweep (Stop Hunt) 🎯")
        if smc['fvg_bearish']: tags.append("Fair Value Gap (FVG) Zone 🔥")
        
        return {
            "asset": pair_name, "type": "SELL / SHORT 🔴", "price": round(latest_m5['close'], 2),
            "sl": sl_price, "tp1": tp1, "tp2": tp2, "wick": round(upper_wick * 100, 1),
            "vol_mult": round(latest_m5['volume'] / vol_avg, 2), "confluence": " | ".join(tags)
        }
    return None

# ==========================================
# 🚀 ASSET PROCESSOR & ANTI-SPAM LOGIC
# ==========================================
def process_asset(display_name, fetch_func, symbol, is_crypto=False):
    if not is_active_session(is_crypto):
        print(f"Skipping {display_name}: Outside active volatility window.")
        return

    now = datetime.datetime.now()
    if display_name in LAST_ALERTS:
        time_diff = (now - LAST_ALERTS[display_name]).total_seconds() / 60
        if time_diff < 20:
            print(f"Skipping {display_name}: Cooldown active ({int(20 - time_diff)} mins left)")
            return

    df_m5 = fetch_func(symbol, interval="5m")
    df_m15 = fetch_func(symbol, interval="15m")
    signal = analyze_super_pro_max(df_m5, df_m15, display_name)
    
    if signal:
        LAST_ALERTS[display_name] = now
        lot_guide = calculate_lot_size(signal['price'], signal['sl'], display_name)
        
        msg = (
            f"👑 *[ ALPHA-APEX SUPER PRO MAX ULTIMATE ]* 👑\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Asset:* `{signal['asset']}`\n"
            f"🎯 *Direction:* {signal['type']}\n"
            f"🧬 *Confluences:*\n`{signal['confluence']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 *Entry Price:* `${signal['price']}`\n"
            f"🛡️ *Stop Loss:* `${signal['sl']}`\n"
            f"🎯 *TP1 (1:1.5):* `${signal['tp1']}` *(Take 50% & Move SL to Entry)*\n"
            f"🚀 *TP2 (1:2.5):* `${signal['tp2']}` *(Final Target)*\n"
            f"💰 *Calculated Position:* {lot_guide} *(for ${int(ACCOUNT_RISK_USD)} Risk)*\n\n"
            f"📈 *VOLUME & WICK METRICS*\n"
            f"• Wick Rejection : `{signal['wick']}%` 🎯\n"
            f"• Volume Expansion: `{signal['vol_mult']}x` SMA20 💥\n\n"
            f"⚠️ *EXECUTION INSTRUCTIONS:*\n"
            f"1. Open Exness MT5 -> Check Chart Setup.\n"
            f"2. Place Limit/Market order using calculated lot size.\n"
            f"3. Set SL & TP1 immediately.\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏰ *Time:* {datetime.datetime.now().strftime('%d %b %Y | %I:%M %p')} IST"
        )
        send_telegram_alert(msg)
    else:
        print(f"No high-confluence setup for {display_name}")

def main():
    print(f"[{datetime.datetime.now()}] Ultimate Super Pro Max Engine Scanning...")
    
    cryptos = {
        "BTCUSDT": "BTC/USD (Bitcoin)",
        "ETHUSDT": "ETH/USD (Ethereum)",
        "SOLUSDT": "SOL/USD (Solana)",
        "XRPUSDT": "XRP/USD (Ripple)"
    }
    
    traditional = {
        "GC=F": "XAU/USD (Gold)",
        "^DJI": "US30 (Dow Jones)",
        "^IXIC": "NAS100 (Nasdaq)"
    }
    
    for symbol, name in cryptos.items():
        try: process_asset(name, fetch_crypto_candles, symbol, is_crypto=True)
        except Exception as e: print(f"Error scanning {name}: {e}")
            
    for ticker, name in traditional.items():
        try: process_asset(name, fetch_traditional_candles, ticker, is_crypto=False)
        except Exception as e: print(f"Error scanning {name}: {e}")

if __name__ == "__main__":
    main()
        
