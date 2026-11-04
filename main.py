import time
import requests
from SmartApi import SmartConnect
import pandas as pd
import numpy as np
import pyotp

# ================= 1. कॉन्फिगरेशन आणि लॉगिन क्रेडेन्शियल्स =================
API_KEY = "iemEXsyV"
CLIENT_ID = "B253694"
MPIN = "7172"
TOTP_KEY = "D4YNATABAIVFIV5C7VJQPJNVIE"

# टेलिग्राम बॉटची माहिती
TELEGRAM_BOT_TOKEN = "8667131376:AAE_b_p7lhL0xuK_bkxYJOAPMUFR9CIBLX0"
TELEGRAM_CHAT_ID = "1486399523"

# स्मार्ट एपीआय कनेक्शन
obj = SmartConnect(api_key=API_KEY)

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def angel_smart_login():
    try:
        current_totp = pyotp.TOTP(TOTP_KEY).now()
        data = obj.generateSession(CLIENT_ID, MPIN, current_totp)
        
        if data and data.get("status"):
            print("लॉगिन यशस्वी झाले.")
            return True
        else:
            error_msg = f"⚠️ *[LOGIN FAILED]* कारण: {data}"
            send_telegram_alert(error_msg)
            print("लॉगिन अयशस्वी:", data)
            return False
    except Exception as e:
        error_msg = f"⚠️ *[LOGIN EXCEPTION]* एरर: {e}"
        send_telegram_alert(error_msg)
        print(f"Login Exception: {e}")
        return False

def get_live_market_data(exchange, symbol_token):
    try:
        ltp_data = obj.ltpData(exchange, symbol_token, symbol_token)
        if ltp_data and ltp_data.get("status"):
            return ltp_data["data"]["ltp"]
    except Exception as e:
        print(f"LTP Fetch Error: {e}")
    return None

def get_atm_strike(spot_price, step=50):
    """स्पॉट प्राईसवरून ATM स्ट्राइक प्राईस राऊंड ऑफ करण्यासाठी (निफ्टीसाठी ५० च्या पटीत)"""
    return round(spot_price / step) * step

# ================= 2. पेपर ट्रेडिंग ऑटोमॅटिक लॉजिक =================
def run_paper_trading_bot():
    send_telegram_alert("🚀 *[TEST]* बॉट चालू होत आहे...")

    if not angel_smart_login():
        send_telegram_alert("⚠️ *[SYSTEM ERROR]* एंजेल वन लॉगिन झाले नाही.")
        return

    virtual_capital = 15000.0  # पेपर ट्रेडिंग कॅपिटल
    send_telegram_alert("✅ *[PAPER TRADING ONLINE]* बॉट सक्रिय झाला आहे.")

    indices = {
        "NIFTY": {"exchange": "NSE", "token": "99926000", "support": 22000}
    }
    
    trade_count = 0
    max_trades = 3  
    
    while trade_count < max_trades:
        try:
            for index_name, data in indices.items():
                current_spot_price = get_live_market_data(data["exchange"], data["token"])
                if not current_spot_price:
                    continue

                support_level = data["support"]
                print(f"Monitoring {index_name} | LTP: {current_spot_price}")

                # सपोर्ट लेव्हल जवळ आल्यावर ट्रेड
                if abs(current_spot_price - support_level) <= 20:
                    trade_count += 1
                    entry_time = time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # ATM स्ट्राइक प्राईस कॅल्क्युलेट करणे
                    atm_strike = get_atm_strike(current_spot_price, step=50)
                    option_type = "CE" 
                    
                    entry_price = current_spot_price
                    stop_loss = entry_price - 30
                    target = entry_price + 90  # 1:3 रिस्क-टू-रिवाड नुसार

                    # टेलिग्रामवर ATM स्ट्राइक सहित अलर्ट पाठवणे
                    alert_msg = (
                        f"📊 *TRADE ENTRY DETECTED*\n"
                        f"• Index: {index_name}\n"
                        f"• Spot Price: {entry_price}\n"
                        f"• **ATM Strike:** {atm_strike} {option_type}\n"
                        f"• Entry Time: {entry_time}\n"
                        f"• Stop Loss: {stop_loss}\n"
                        f"• Target: {target}"
                    )
                    send_telegram_alert(alert_msg)
                    
                    print(f"Trade Taken: {atm_strike} {option_type} at Spot {entry_price}")
                    time.sleep(60) 

            time.sleep(10)
        except Exception as e:
            print(f"Main Loop Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_paper_trading_bot()
    
