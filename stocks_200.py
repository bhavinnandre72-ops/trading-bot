import time
import requests
import pandas as pd

# १. तुमच्या बॉटची माहिती
TOKEN = "8731401312:AAEQwWyzlDfGXUQeT3f0ZrKkkabi98xOvrQ"
CHAT_ID = "8731401312"  # किंवा तुमचा स्वतःचा पर्सनल चॅट आयडी इथे टाकू शकता

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

# २. तुमचे २०० स्टॉक्सची यादी (उदा. काही स्टॉक्स इथे दिले आहेत, तुम्ही तुमचे २०० स्टॉक्स टाकू शकता)
stocks_list = ["RELIANCE", "TCS", "INFY", "TATAMOTORS", "SBIN"] 

def check_tiranga_daily_strategy():
    print("Daily Tiranga Strategy स्कॅनिंग सुरू आहे...")
    
    for stock in stocks_list:
        # इथे तुम्ही तुमच्या ब्रोकर API (उदा. Angel One SmartAPI) वरून 
        # त्या स्टॉकचा 'Daily (1D)' टाईमफ्रेमचा डेटा (OHLCV) फेच कराल.
        
        # --- लॉजिक चे उदहारण ---
        # df = get_daily_data(stock)
        
        # EMA कॅल्क्युलेशन (Daily Close नुसार)
        # df['EMA_5'] = df['close'].ewm(span=5, adjust=False).mean()   # भगवा (Orange)
        # df['EMA_13'] = df['close'].ewm(span=13, adjust=False).mean() # पांढरा (White)
        # df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean() # हिरवा (Green)
        
        # क्रॉसओव्हर कंडिशन: जेव्हा EMA 5 (भगवा), EMA 13 (पांढरा) ला वरच्या बाजूने क्रॉस करेल आणि EMA 13 हा EMA 26 पेक्षा वर असेल
        # if df.iloc[-2]['EMA_5'] <= df.iloc[-2]['EMA_13'] and df.iloc[-1]['EMA_5'] > df.iloc[-1]['EMA_13'] and df.iloc[-1]['EMA_13'] > df.iloc[-1]['EMA_13']:
        #     candle_low = df.iloc[-1]['low']  # हा तुमचा Stop Loss असेल
        #     
        #     msg = (f"🚨 *Daily Tiranga Strategy Alert* 🚨\n\n"
        #            f"📌 *Stock:* {stock}\n"
        #            f"⏰ *Timeframe:* Daily (1D)\n"
        #            f"🟢 *Signal:* Bullish Crossover (EMA 5 crosses EMA 13)\n"
        #            f"🛑 *Stop Loss (Low):* {candle_low}")
        #     
        #     send_telegram_alert(msg)
            
    print("स्कॅनिंग पूर्ण झाले.")

# कोड रन करण्यासाठी
if __name__ == "__main__":
    # आधी एक टेस्ट मेसेज पाठवून तपासा
    send_telegram_alert("🚀 *Tiranga Strategy Bot* is ready for Daily 200 Stocks Scanning!")
    # check_tiranga_daily_strategy()
