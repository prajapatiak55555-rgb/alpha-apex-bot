import pandas as pd
import numpy as np
import requests
import datetime

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_BOT_TOKEN = "8973233256:AAGu3FsMR1C6hzr9xoPDD4W7f2NZtu_ijE0"
TELEGRAM_CHAT_ID = "8762446105"

def send_telegram_alert(message):
    """Telegram par alert notification bhejne ke liye function"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram alert sent successfully!")
        else:
            print(f"Failed to send Telegram alert: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def main():
    print(f"[{datetime.datetime.now()}] Alpha Apex Bot execution started...")
    
    # Market Data Fetching (CoinGecko API)
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        btc_price = data.get('bitcoin', {}).get('usd', 0)
        btc_change = data.get('bitcoin', {}).get('usd_24h_change', 0)
        
        # Test signal / Market Status message
        status_msg = (
            f"🚀 *ALPHA APEX BOT ACTIVE* 🚀\n\n"
            f"**Asset:** BTCUSD\n"
            f"**Price:** ${btc_price}\n"
            f"**24h Change:** {btc_change:.2f}%\n\n"
            f"📌 *Status:* Bot is running on schedule and monitoring signals!"
        )
        
        # Always send heartbeat notification on run
        send_telegram_alert(status_msg)
            
    except Exception as e:
        print(f"Error executing strategy: {e}")
        
    print(f"[{datetime.datetime.now()}] Execution completed.")

if __name__ == "__main__":
    main()
    
