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
TOTP_KEY = "D4YNATHBA3VFIW5C7YUQPJNVIE"

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
            print("एंजेल वन लॉगिन यशस्वी झाले.")
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

def get_atm_strike(spot_price, index_name):
    """स्पॉट प्राईसवरून ATM स्ट्राइक प्राईस काढणे (निफ्टी ५० च्या पटीत, सेन्सेक्स १०० च्या पटीत)"""
    if index_name == "NIFTY":
        return round(spot_price / 50) * 50
    elif index_name == "SENSEX":
        return round(spot_price / 100) * 100
    return spot_price

def evaluate_strategy_rules(signal_type, current_iv, spot_price, index_name):
    """
    स्ट्रॅटेजीच्या नियमांनुसार:
    - IV > 15 असल्यास: Delta >= 0.60 ची ITM स्ट्राइक (Buy CE / Buy PE)
    - IV < 15 असल्यास: ATM स्ट्राइक (Sell PE / Sell CE)
    """
    atm_strike = get_atm_strike(spot_price, index_name)
    
    if signal_type == "UP_BREAKOUT":
        if current_iv > 15:
            action = "BUY CE"
            strike_desc = "ITM Strike (Delta >= 0.60)"
        else:
            action = "SELL PE"
            strike_desc = f"ATM Strike ({atm_strike})"
            
    elif signal_type == "DOWN_BREAKDOWN":
        if current_iv > 15:
            action = "BUY PE"
            strike_desc = "ITM Strike (Delta >= 0.60)"
        else:
            action = "SELL CE"
            strike_desc = f"ATM Strike ({atm_strike})"
    else:
        return None, None, None

    return action, strike_desc, atm_strike

# ================= 2. मुख्य पेपर ट्रेडिंग आणि स्ट्रॅटेजी लूप =================
def run_paper_trading_strategy():
    if not angel_smart_login():
        return

    paper_capital = 180000.0  # दिलेले पेपर ट्रेडिंग कॅपिटल
    send_telegram_alert(
        f"🚀 *15 Mins Breakout Strategy (Paper Trading)*\n"
        f"• Capital: ₹{paper_capital:,.2f}\n"
        f"• Indices: Nifty & Sensex\n"
        f"• IV & Delta Rules & Risk Management Active."
    )

    indices = {
        "NIFTY": {"exchange": "NSE", "token": "99926000"},
        "SENSEX": {"exchange": "BSE", "token": "99919000"}
    }

    # ट्रेड आणि रिस्क मॅनेजमेंटचे व्हेरिएबल्स
    trade_history = []  # उदा. ["PROFIT", "LOSS"]
    max_trades = 3

    while len(trade_history) < max_trades:
        try:
            current_time = time.strftime('%H:%M:%S')
            
            # नियम: सलग दोन प्रॉफिट किंवा सलग दोन लॉस झाल्यास तिसरी एंट्री घेऊ नका
            if len(trade_history) == 2:
                if trade_history[0] == trade_history[1]:
                    send_telegram_alert(f"⚠️ *Trading Stopped for Today:* सलग दोन ट्रेड एकाच निकालात ({(trade_history[0])}) गेल्यामुळे नियम क्र. ३ किंवा ४ नुसार आजचे ट्रेड बंद केले आहेत.")
                    break
            
            # सकाळी ९:३० ते दुपारी २:३० दरम्यान ट्रेड मॉनिटर करणे
            if "09:30:00" <= current_time <= "14:30:00":
                for index_name, data in indices.items():
                    # [टीप]: प्रत्यक्षात इथे ब्रोकर API द्वारे लाइव्ह डेटा, 15-मिनिट झोन आणि IV वैल्यू फेच करायची असते.
                    # उदाहरणार्थ:
                    # spot_price = get_live_market_data(data["exchange"], data["token"])
                    # current_iv = get_live_iv(...)
                    # signal_type = check_breakout(...)
                    
                    # (जेव्हा सिग्नल जनरेट होईल तेव्हा खालीलप्रमाणे टेलिग्राम अलर्ट येईल)
                    # if signal_type:
                    #     action, strike_desc, atm_strike = evaluate_strategy_rules(signal_type, current_iv, spot_price, index_name)
                    #     
                    #     # रिस्क आणि स्टॉप लॉस मर्यादा (₹१,५०० ते ₹२,००० च्या आत)
                    #     alert_msg = (
                    #         f"📊 *PAPER TRADING SIGNAL (Trade #{len(trade_history) + 1})*\n"
                    #         f"• Index: {index_name}\n"
                    #         f"• Signal: {signal_type}\n"
                    #         f"• Action: *{action}*\n"
                    #         f"• Strike Info: {strike_desc}\n"
                    #         f"• Spot Price: {spot_price}\n"
                    #         f"• Current IV: {current_iv}\n"
                    #         f"• Stop Loss Limit: ₹1,500 - ₹2,000\n"
                    #         f"• Time: {current_time}"
                    #     )
                    #     send_telegram_alert(alert_msg)
                    #     
                    #     # ट्रेडनंतर १५ मिनिटांचा ब्रेक आणि रिझल्ट रेकॉर्ड करण्याची सोय
                    #     trade_history.append("PROFIT") # (उदाहरणार्थ ट्रेड निकाल)
                    #     time.sleep(900)  # १५ मिनिटांचा ब्रेक
                    pass

            time.sleep(60)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_paper_trading_strategy()
    
