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
  print("Crude Oil Bot: Angel One API Connected!")
  send_telegram("✅ *Crude Oil Live Bot Connected!*")
except Exception as e:
  print(f"Login Failed: {e}")
  send_telegram("❌ *Crude Oil Bot API Connection Failed!*")

# ----------------- लाईव्ह डेटा & पेपर ट्रेडिंग -----------------
trade_done_today = False

while True:
  now = datetime.now()
  current_time = now.strftime("%H:%M")

  # क्रूड ऑईलसाठी सकाळी ९:१५ वाजता किंवा हव्या त्या वेळी लाईव्ह डेटा फेच करणे
  if current_time == "09:15" and not trade_done_today:
    try:
      # MCX Crude Oil Live Price (MCX Token for Crude Oil)
      ltp_data = smartApi.ltpData("MCX", "CRUDEOIL", "260335")
      crude_live = float(ltp_data["data"]["ltp"])

      trade_msg = (
          f"🛢 *क्रूड ऑईल लाईव्ह पेपर ट्रेड (MCX)*\n\n"
          f"📈 *क्रूड ऑईल लाईव्ह भाव:* ₹{crude_live}\n"
          f"🎯 *कॉन्ट्रैक्ट:* CRUDEOIL FUTURE\n"
          f"📦 *क्वांटिटी:* 1 Lot (100 Barrels)\n"
          f"⏱ *एन्ट्री वेळ:* `{now.strftime('%H:%M:%S')}`\n\n"
          f"_हा मेसेज MCX क्रूड ऑईलच्या रिअल-टाईम लाईव्ह डेटावर आधारित आहे._"
      )

      send_telegram(trade_msg)
      trade_done_today = True

    except Exception as e:
      print(f"Error fetching Crude LTP: {e}")

  # रात्री १२:०० वाजता स्टेटस रिसेट करणे
  if current_time == "00:00":
    trade_done_today = False

  time.sleep(30)
    
