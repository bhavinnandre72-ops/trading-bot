from datetime import datetime
import time
from SmartApi import SmartConnect
import pyotp
import requests

# ----------------- क्रेडेंशियल्स -----------------
API_KEY = "iemEXsyV"
CLIENT_ID = "B253694"
PWD = "7172"
TOTP_SECRET = "D4YNATHBA3VFIW5C7YUQPJNVIE"

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
  print("Angel One SmartAPI Successfully Connected!")
  send_telegram("✅ *Angel One Cloud Live API Connected!*")
except Exception as e:
  print(f"Login Failed: {e}")
  send_telegram("❌ *Angel One API Connection Failed!*")

# ----------------- लाईव्ह डेटा & पेपर ट्रेडिंग -----------------
trade_done_today = False

while True:
  now = datetime.now()
  current_time = now.strftime("%H:%M")

  # दररोज सकाळी ०९:३० वाजता Angel One कडून लाईव्ह डेटा घेऊन ट्रेड ट्रिगर करणे
  if current_time == "09:30" and not trade_done_today:
    try:
      ltp_data = smartApi.ltpData("NSE", "NIFTY", "99926000")
      nifty_live = float(ltp_data["data"]["ltp"])
      atm_strike = round(nifty_live / 50) * 50

      trade_msg = (
          f"📊 *एन्जेल वन लाईव्ह पेपर ट्रेड (Nifty 50)*\n\n"
          f"📈 *निफ्टी लाईव्ह भाव:* ₹{nifty_live}\n"
          f"🎯 *निवडलेली ATM स्ट्राइक:* NIFTY {atm_strike} CE\n"
          f"📦 *क्वांटिटी:* 65 Units (1 Lot)\n"
          f"⏱ *एन्ट्री वेळ:* `{now.strftime('%H:%M:%S')}`\n\n"
          f"_हा मेसेज एन्जेल वनच्या रिअल-टाईम लाईव्ह डेटावर आधारित आहे._"
      )

      send_telegram(trade_msg)
      trade_done_today = True

    except Exception as e:
      print(f"Error fetching live LTP: {e}")

  if current_time == "00:00":
    trade_done_today = False

  time.sleep(30)
    
