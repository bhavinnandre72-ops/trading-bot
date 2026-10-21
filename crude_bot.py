from datetime import datetime, timedelta
import time
import pandas as pd
from SmartApi import SmartConnect
import pyotp
import requests

# ----------------- क्रेडेंशियल्स -----------------
API_KEY = "ienEXsyV"
CLIENT_ID = "8253694"
PWD = "Ji72"
TOTP_SECRET = "D4YN4THBA3VFIW5C7YLUQFINVIE"

TELEGRAM_TOKEN = "8667131376:AAFRsq79krKkfHr8OFzD0cVh6vooie6jYcI"
TELEGRAM_CHAT_ID = "1486399523"


def send_telegram(message):
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {
      "chat_id": TELEGRAM_CHAT_ID,
      "text": message,
      "parse_mode": "Markdown",
  }
  try:
    requests.post(url, json=payload)
  except Exception as e:
    print(f"Telegram Error: {e}")


# ----------------- SmartAPI कनेक्ट -----------------
try:
  smartApi = SmartConnect(api_key=API_KEY)
  totp = pyotp.TOTP(TOTP_SECRET).now()
  data = smartApi.generateSession(CLIENT_ID, PWD, totp)
  print("Crude Options Bot Connected!")
  send_telegram("✅ *क्रूड ऑईल ऑप्शन्स बॉट लाईव्ह सुरू झाला आहे!*")
except Exception as e:
  print(f"Login Failed: {e}")
  send_telegram("❌ *क्रूड ऑईल ऑप्शन्स बॉट कनेक्शन अयशस्वी!*")


# ----------------- RSI मोजण्याचे फंक्शन -----------------
def calculate_rsi(prices, window=14):
  delta = prices.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
  rs = gain / loss
  rsi = 100 - (100 / (1 + rs))
  return rsi.iloc[-1]


# ----------------- मुख्य लॉजिक (क्रूड ऑईल ऑप्शन्स) -----------------
trade_done_today = False

while True:
  now = datetime.now()
  current_time = now.strftime("%H:%M")

  # क्रूड ऑईल मार्केट चालू वेळ: सकाळी ०९:०० ते रात्री ११:३० दरम्यान
  if "09:00" <= current_time <= "23:30" and not trade_done_today:
    try:
      # ऐतिहासिक डेटा फेच करणे (RSI आणि स/र साठी)
      to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
      from_date = (datetime.now() - timedelta(days=2)).strftime(
          "%Y-%m-%d %H:%M"
      )

      historic_param = {
          "exchange": "MCX",
          "symboltoken": "260335",
          "interval": "ONE_HOUR",
          "fromdate": from_date,
          "todate": to_date,
      }

      history = smartApi.getCandleData(historic_param)

      if history and "data" in history:
        df = pd.DataFrame(
            history["data"],
            columns=["Date", "Open", "High", "Low", "Close", "Volume"],
        )
        df["Close"] = df["Close"].astype(float)

        current_price = df["Close"].iloc[-1]
        rsi_val = round(calculate_rsi(df["Close"]), 2)

        # ATM स्ट्राइक प्राईस काढणे (५० च्या फरकाने, जसे ऑप्शन चेनमध्ये आहे)
        atm_strike = round(current_price / 50) * 50

        # सपोर्ट आणि रेजिस्टेंस लेव्हल्स
        support = round(df["Low"].tail(10).min(), 2)
        resistance = round(df["High"].tail(10).max(), 2)

        # कॅन्डलस्टिक पॅटर्न आणि ऑप्शन सिलेक्ट करणे (अप्टन असेल तर CE, डाऊनट्रेंड तर PE)
        prev_close = df["Close"].iloc[-2]
        if current_price > prev_close:
          pattern = "Bullish Engulfing / Hammer"
          option_type = f"{atm_strike} CE (कॉल ऑप्शन)"
          signal = "BUY CALL (LONG)"
        else:
          pattern = "Bearish Pattern"
          option_type = f"{atm_strike} PE (पुट ऑप्शन)"
          signal = "BUY PUT (SHORT)"

        # टेलिग्रामवर सविस्तर ऑप्शन ट्रेड अलर्ट पाठवणे
        trade_msg = (
            f"🛢 *क्रूड ऑईल ऑप्शन्स ट्रेड अलर्ट (MCX)*\n\n"
            f"📈 *क्रूड लाईव्ह भाव:* ₹{current_price}\n"
            f"🎯 *निवडलेली ATM स्ट्राइक:* CRUDEOIL {option_type}\n"
            f"📊 *RSI (14):* `{rsi_val}`\n"
            f"🕯 *पॅटर्न:* {pattern}\n"
            f"🛡 *सपोर्ट:* ₹{support}\n"
            f"🚀 *रेजिस्टेंस:* ₹{resistance}\n"
            f"🎯 *सिस्टम सिग्नल:* *{signal}*\n"
            f"⏱ *वेळ:* `{now.strftime('%H:%M:%S')}`\n\n"
            f"_हा ट्रेड क्रूड ऑईल ऑप्शन्सच्या स्ट्राइक प्राईस आणि टेक्निकल"
            f" सेटअपवर आधारित आहे._"
        )

        send_telegram(trade_msg)
        trade_done_today = True

    except Exception as e:
      print(f"Error: {e}")

  # रात्री १२:०० वाजता स्टेटस रिसेट करणे
  if current_time == "00:00":
    trade_done_today = False

  time.sleep(60)
  
