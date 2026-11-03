import time
import requests
from SmartApi import SmartConnect
import pandas as pd
import numpy as np
import pyotp

# ================= 1. कॉन्फिगरेशन आणि लॉगिन सेटिंग्स =================
API_KEY = "IanEntxv"
CLIENT_ID = "BZ33694"
MPIN = "7172"
TOTP_KEY = "D4VNATABAIVFIVGC7VJQPJWZIE"

# टेलिग्राम बॉटची माहिती (कॉन्टॅक्ट)
TELEGRAM_BOT_TOKEN = "8947131376:AAE_0i)ffjHLDkUk_bkx5J84P8RFCIQ144"
TELEGRAM_CHAT_ID = "1480169123"

# स्मार्ट एपीआय कनेक्शन
obj = SmartConnect(api_Key=API_KEY)

def send_telegram_alert(message):
    try:
        uri = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(uri, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def angel_smart_login():
    try:
        current_totp = pyotp.TOTP(TOTP_KEY).now()
        data = obj.generateSession(CLIENT_ID, MPIN, current_totp)
        
        if data and data["status"]:
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
        if ltp_data and ltp_data["status"]:
            return ltp_data["data"]["ltp"]
    except Exception as e:
        print(f"LTP Fetch Error: {e}")
    return None

def get_atm_strike(spot_price, step=50):
    """ स्पॉट प्राईसवरून ATM स्ट्राइक शोधण्यासाठी (उदा. Nifty साठी स्टेप 50) """
    return round(spot_price / step) * step

# ================= 2. नवीन प्राईस ॲक्शन स्ट्रॅटेजी बॉट लॉजिक =================
def run_price_action_strategy():
    send_telegram_alert("🚀 *[TEST]* बोट सुरू होत आहे...")
    
    if not angel_smart_login():
        send_telegram_alert("⚠️ *[SYSTEM ERROR]* लॉगिन यशस्वी झाले नाही.")
        return

    virtual_capital = 20000.0  # फंड मर्यादा
    send_telegram_alert("✅ *[PAPER TRADING ONLINE]* नवीन प्राईस ॲक्शन स्ट्रॅटेजी सक्रिय")

    indices = {
        "NIFTY": {"exchange": "NSE", "token": "99926000", "step": 50},
        "BANKNIFTY": {"exchange": "NSE", "token": "99926009", "step": 100},
        "SENSEX": {"exchange": "BSE", "token": "99919000", "step": 100}
    }

    trade_count = 0
    max_trades = 2  # दिवसभरात 1 ते 2 एंट्री

    while trade_count < max_trades:
        try:
            for index_name, data in indices.items():
                current_spot_price = get_live_market_data(data["exchange"], data["token"])
                if not current_spot_price:
                    continue

                # टीप: प्रत्यक्ष डेटा घेण्यासाठी ऐतिहासिक कॅण्डल (15 मिनिट व 5 मिनिट) API द्वारे फेच कराव्यात.
                # येथे स्ट्रॅटेजीचे कोडिंग स्ट्रक्चर खालीलप्रमाणे लागू केले आहे:

                # 1. पहिली 15 मिनिटांची कॅण्डल (9:15 ते 9:30) सोडून द्यायची.
                # 2. त्यानंतर येणारी पहिली 'लाल' (Red) 15 मिनिटांची कॅण्डल शोधायची.
                # 3. त्या लाल कॅण्डलचा High आणि Low मार्क करायचा.
                
                # समजा 5 मिनिटांच्या टाईमफ्रेमवर ब्रेकआऊट मिळाला:
                breakout_side = None  # 'UP' किंवा 'DOWN' (तांत्रिक गणनेनुसार ठर Sound होईल)
                current_candle_color = "GREEN"  # किंवा "RED"
                implied_volatility = 18.0  # हा डेटा ऑप्शन चेनमधून घ्यावा (IV)

                atm_strike = get_atm_strike(current_spot_price, data["step"])

                # अपसाईड ब्रेकआऊट नियम (Up Side Breakout)
                if breakout_side == "UP" and current_candle_color == "GREEN":
                    if implied_volatility >= 18:
                        # Call Buy (IV 18 च्या वर)
                        alert_msg = f"🟢 *[CALL BUY SIGNAL]*\nइंडेक्स: {index_name}\nस्ट्राइक: ATM {atm_strike} CE\nकारण: अपसाईड ब्रेकआऊट व IV >= 18\nटारगेट/एसएलयूपी: ₹1500 (1:1)"
                        send_telegram_alert(alert_msg)
                        trade_count += 1
                    elif implied_volatility < 15:
                        # Call Sell (IV 15 च्या खाली)
                        alert_msg = f"🔴 *[CALL SELL SIGNAL]*\nइंडेक्स: {index_name}\nस्ट्राइक: ATM {atm_strike} CE\nकारण: अपसाईड ब्रेकआऊट व IV < 15\nटारगेट/एसएलयूपी: ₹1500 (1:1)"
                        send_telegram_alert(alert_msg)
                        trade_count += 1

                # डाऊनसाईड ब्रेकआऊट नियम (Down Side Breakout)
                elif breakout_side == "DOWN" and current_candle_color == "RED":
                    if implied_volatility >= 18:
                        # Put Buy (IV 18 च्या वर)
                        alert_msg = f"🟢 *[PUT BUY SIGNAL]*\nइंडेक्स: {index_name}\nस्ट्राइक: ATM {atm_strike} PE\nकारण: डाऊनसाईड ब्रेकआऊट व IV >= 18\nटारगेट/एसएलयूपी: ₹1500 (1:1)"
                        send_telegram_alert(alert_msg)
                        trade_count += 1
                    elif implied_volatility < 15:
                        # Put Sell (IV 15 च्या खाली)
                        alert_msg = f"🔴 *[PUT SELL SIGNAL]*\nइंडेक्स: {index_name}\nस्ट्राइक: ATM {atm_strike} PE\nकारण: डाऊनसाईड ब्रेकआऊट व IV < 15\nटारगेट/एसएलयूपी: ₹1500 (1:1)"
                        send_telegram_alert(alert_msg)
                        trade_count += 1

            time.sleep(60) # दर 1 मिनिटाने मार्केट तपासेल

        except Exception as e:
            print(f"Error in trading loop: {e}")
            time.sleep(30)

if __name__ == "__main__":
    run_price_action_strategy()
    
