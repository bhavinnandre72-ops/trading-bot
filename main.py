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

def get_atm_strike(spot_price, index_name):
    """स्पॉट प्राईसवरून ATM स्ट्राइक प्राईस काढण्यासाठी (निफ्टीसाठी ५० च्या पटीत, सेन्सेक्ससाठी १०० च्या पटीत)"""
    if index_name == "NIFTY":
        return round(spot_price / 50) * 50
    elif index_name == "SENSEX":
        return round(spot_price / 100) * 100
    return spot_price

def calculate_parabolic_sar(high, low, af=0.02, max_af=0.2):
    psar = low.copy()
    bullish = True
    hp = high.iloc[0]
    lp = low.iloc[0]
    af_val = af
    
    psar.iloc[0] = lp
    for i in range(1, len(high)):
        if bullish:
            psar.iloc[i] = psar.iloc[i-1] + af_val * (hp - psar.iloc[i-1])
            if low.iloc[i] < psar.iloc[i]:
                bullish = False
                psar.iloc[i] = hp
                lp = low.iloc[i]
                af_val = af
            else:
                if high.iloc[i] > hp:
                    hp = high.iloc[i]
                    af_val = min(af_val + af, max_af)
        else:
            psar.iloc[i] = psar.iloc[i-1] - af_val * (psar.iloc[i-1] - lp)
            if high.iloc[i] > psar.iloc[i]:
                bullish = True
                psar.iloc[i] = lp
                hp = high.iloc[i]
                af_val = af
            else:
                if low.iloc[i] < lp:
                    lp = low.iloc[i]
                    af_val = min(af_val + af, max_af)
    return psar

def check_strategy_signals(df):
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
    df['SAR'] = calculate_parabolic_sar(df['high'], df['low'])

    i = -2  # शेवटची पूर्ण झालेली 1 मिनिटाची कॅन्डल
    
    close = df['close'].iloc[i]
    open_p = df['open'].iloc[i]
    high = df['high'].iloc[i]
    low = df['low'].iloc[i]
    volume = df['volume'].iloc[i]
    vol_ma = df['Volume_MA20'].iloc[i]
    
    ma5_curr = df['MA5'].iloc[i]
    ma20_curr = df['MA20'].iloc[i]
    ma5_prev = df['MA5'].iloc[i-1]
    ma20_prev = df['MA20'].iloc[i-1]
    sar = df['SAR'].iloc[i]

    is_green = close > open_p
    is_red = close < open_p

    # 1. अपसाईड सिग्नल (Buy / CE)
    if (ma5_prev <= ma20_prev and ma5_curr > ma20_curr) and is_green and (sar < low) and (volume > vol_ma):
        return "BUY (CE)", close, low

    # 2. डाऊनसाईड सिग्नल (Sell / PE)
    elif (ma5_prev >= ma20_prev and ma5_curr < ma20_curr) and is_red and (sar > high) and (volume > vol_ma):
        return "SELL (PE)", close, high

    return None, 0, 0

# ================= 2. लाईव्ह मॉनिटरिंग आणि अलर्ट लूप =================
def run_scalping_bot():
    if not angel_smart_login():
        return

    send_telegram_alert("🚀 *Scalping Bot Active (1-Min Timeframe)*\n• MA 5/20, Parabolic SAR & Volume Filter\n• ATM Strike & Telegram Alerts Enabled.")

    indices = {
        "NIFTY": {"exchange": "NSE", "token": "99926000"},
        "SENSEX": {"exchange": "BSE", "token": "99919000"}
    }

    while True:
        try:
            for index_name, data in indices.items():
                # तुमच्या ब्रोकरच्या API द्वारे 1 मिनिटाचा कॅन्डल डेटा मिळवा:
                # df = obj.getCandleData(data["exchange"], data["token"], ...)
                
                # सिग्नल तपासणी (डेटा जोडल्यानंतर ही ओळ अनकमेंट करा)
                # signal, spot_price, sl_price = check_strategy_signals(df)
                
                # if signal:
                #     atm_strike = get_atm_strike(spot_price, index_name)
                #     option_type = "CE" if "BUY" in signal else "PE"
                #     current_time = time.strftime('%Y-%m-%d %H:%M:%S')
                #     
                #     alert_text = (
                #         f"📊 *STRATEGY SIGNAL DETECTED*\n"
                #         f"• Index: {index_name}\n"
                #         f"• Spot Price: {spot_price}\n"
                #         f"• **ATM Strike:** {atm_strike} {option_type}\n"
                #         f"• Action: {signal}\n"
                #         f"• Stop Loss: {sl_price}\n"
                #         f"• Time: {current_time}"
                #     )
                #     send_telegram_alert(alert_text)
                pass

            time.sleep(60)  # प्रत्येक 1 मिनिटाच्या कॅन्डलसाठी प्रतीक्षा
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_scalping_bot()
    
