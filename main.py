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

# टेलिग्राम बॉटची माहिती
TELEGRAM_BOT_TOKEN = "8947131376:AAE_0i)ffjHLDkUk_bkx5J84P8RFCIQ144"
TELEGRAM_CHAT_ID = "1480169123"

# स्मार्ट एपीआय कनेक्शन (TypeError एरर दूर करण्यासाठी 'api_key' पॅरामीटर योग्य पद्धतीने दिला आहे)
obj = SmartConnect(api_key=API_KEY)

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

def
