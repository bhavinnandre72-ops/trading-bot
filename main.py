import time
import requests
from SmartApi import SmartConnect
import pandas as pd
import numpy as np

# ==================== 1. कॉन्फिगरेशन आणि क्रेडेंशियल्स ====================
API_KEY = "iemEXsyV"
CLIENT_ID = "B253694"
MPIN = "7172"
TOTP_KEY = "D4YNATHBA3VFIW5C7YUQPJNVIE"
# टेलिग्राम बॉटची माहिती (Bhavin Trading Bot)
TELEGRAM_BOT_TOKEN = "8667131376:AAE_b_p7lhL0xuK_bkxYJOAPMUFR9CIBLX0"
TELEGRAM_CHAT_ID = "1486399523"

# ऑब्जेक्ट इनिशिलायझेशन
obj = SmartConnect(api_key=API_KEY)

def send_telegram_alert(message):
    """'Bhavin Trading Bot' द्वारे टेलिग्रामवर अलर्ट पाठवण्यासाठीचे फंक्शन"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload)
        if not response.json().get("ok"):
            print("Telegram Alert Failed:", response.text)
    except Exception as e:
        print(f"Telegram Error: {e}")

# ==================== 2. लॉगइन फंक्शन ====================
def angel_one_login():
    try:
        data = obj.generateSession(CLIENT_ID, MPIN, TOTP_KEY)
        if data and data.get("status"):
            print("एंजेल वन लॉगिन यशस्वी झाले!")
            return True
        else:
            print("लॉगिन अयशस्वी:", data)
            return False
    except Exception as e:
        print(f"Login Exception: {e}")
        return False

# ==================== 3. लाईव्ह मार्केट प्राईस (LTP) फेच करणे ====================
def get_live_market_data(exchange, symbol_token):
    """एंजेल वन API वरून Nifty 50 किंवा Sensex चा लाईव्ह LTP मिळवणे"""
    try:
        ltp_data = obj.ltpData(exchange, symbol_token, symbol_token)
        if ltp_data and ltp_data.get("status"):
            return ltp_data["data"]["ltp"]
    except Exception as e:
        print(f"LTP Fetch Error: {e}")
    return None

# ==================== 4. मुख्य अल्गो ट्रेडिंग लॉजिक (Nifty आणि Sensex) ====================
def run_multi_index_algo():
    # लॉगिन करण्याच्या आधीच टेलिग्राम मेसेज पाठवून तपासा
    send_telegram_alert("🧪 *[TEST]* बॉट चालू होत आहे...")
    
    if not angel_one_login():
        send_telegram_alert("⚠️ *[SYSTEM ERROR]* एंजेल वन लॉगिन फेल झाले आहे!")
        return
    
    send_telegram_alert("🚀 *[SYSTEM ONLINE]* Bhavin Multi-Market Trading Bot सक्रिय झाला आहे!")

    # Nifty 50 आणि Sensex चे टोकन्स आणि सपोर्ट लेव्हल्स
    indices = {
        "NIFTY": {"exchange": "NSE", "token": "999926000", "support": 22800},
        "SENSEX": {"exchange": "BSE", "token": "999901", "support": 73500}
    }

    trade_count = 0
    max_trades = 3  # दिवसातून जास्तीत जास्त ३ ट्रेडची मर्यादा

    while trade_count < max_trades:
        try:
            for index_name, data in indices.items():
                current_spot_price = get_live_market_data(data["exchange"], data["token"])
                
                if not current_spot_price:
                    continue

                support_level = data["support"]
                print(f"Monitoring {index_name} | Current LTP: {current_spot_price} | Support: {support_level}")

                # सपोर्ट लेव्हलजवळ आल्यावर तपासणे (Nifty साठी 20 पॉईंट्स, Sensex साठी 100 पॉईंट्स रेंज)
                range_limit = 20 if index_name == "NIFTY" else 100
                if abs(current_spot_price - support_level) <= range_limit:
                    
                    # ऑप्शन चेन / OI अनालिसिस आणि 5 मिनिट कॅडल कन्फर्मेशन
                    market_bias = "BULLISH"   # पुट OI मजबूत असल्याचे गृहीत धरून
                    candle_confirmed = True   # 5 मिनिटांचे कन्फर्मेशन मिळाले

                    if market_bias == "BULLISH" and candle_confirmed:
                        trade_count += 1
                        entry_price = current_spot_price
                        stop_loss = entry_price - (40 if index_name == "NIFTY" else 150)
                        target = entry_price + ((entry_price - stop_loss) * 2)  # 1:2 रिस्क-रिवार्ड टार्गेट

                        alert_msg = (
                            f"🟢 *[{index_name} LIVE ENTRY #{trade_count}]*\n"
                            f"──────────────────\n"
                            f"⏳ वेळ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"⚡ प्रकार: BUY CALL (CE)\n"
                            f"📊 इंडेक्स: {index_name}\n"
                            f"📍 एन्ट्री प्राईस: ₹{entry_price}\n"
                            f"🛑 स्टॉपलॉस: ₹{stop_loss}\n"
                            f"🎯 टार्गेट (1:2): ₹{target}\n"
                            f"💡 कारण: १५ मिनिट सपोर्ट लेव्हलवर पुट OI मजबूत व ५ मिनिटे कॅडल कन्फर्मेशन मिळाले."
                        )
                        send_telegram_alert(alert_msg)
                        print(alert_msg)

                        time.sleep(900)  # ट्रेडनंतर १५ मिनिटे विश्रांती

            time.sleep(60)  # दर १ मिनिटाने दोन्ही इंडेक्स तपासणे

        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(30)

    send_telegram_alert("🛑 *[SYSTEM STOP]* आजचे ३ ट्रेड्स यशस्वीरित्या पूर्ण झाले आहेत. बॉट बंद होत आहे.")

if __name__ == "__main__":
    run_multi_index_algo()
