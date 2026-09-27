import pandas as pd
import numpy as np
import requests
import datetime

def main():
    print(f"[{datetime.datetime.now()}] Alpha Apex Bot execution started...")
    
    # 1. Fetch market data (Example using CoinGecko public API)
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        btc_price = data.get('bitcoin', {}).get('usd', 0)
        btc_change = data.get('bitcoin', {}).get('usd_24h_change', 0)
        eth_price = data.get('ethereum', {}).get('usd', 0)
        eth_change = data.get('ethereum', {}).get('usd_24h_change', 0)
        
        print(f"Bitcoin (BTC): ${btc_price} ({btc_change:.2f}%)")
        print(f"Ethereum (ETH): ${eth_price} ({eth_change:.2f}%)")
        
        # 2. Simple Trading Logic / Signal Generation Example
        if btc_change > 2.0:
            signal = "BULLISH 🚀"
        elif btc_change < -2.0:
            signal = "BEARISH 📉"
        else:
            signal = "NEUTRAL ⚖️"
            
        print(f"Market Sentiment Signal: {signal}")
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        
    print(f"[{datetime.datetime.now()}] Execution completed successfully.")

if __name__ == "__main__":
    main()
  
