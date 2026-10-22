from datetime import datetime, timedelta
import multiprocessing
import os
import time
from flask import Flask
import pandas as pd
from smartapi.smartConnect import SmartConnect
import pyotp
import requests

# ----------------- फ्लॅस्क वेब सर्व्हेर (Render साठी) -----------------
app = Flask(__name__)


@app.route("/")
def home():
  return "Trading Bot is Active!"


def run_web():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


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
  }
  try:
    response = requests.post(url, json=payload)
    print("Telegram Status Code:", response.status_code)
  except Exception as e:
    print(f"Telegram Error: {e}")


# ----------------- १. निफ्टी बॉट फंक्शन -----------------
def run_nifty():
  send_telegram("🚀 [SYSTEM CONNECTED] Nifty 50 Options Bot Is Live!")
  trade_done_today = False

  while True:
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    if "09:15" <= current_time <= "15:30" and not trade_done_today:
      try:
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)
        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])

        to_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        from_date = (datetime.now() - timedelta(days=2)).strftime(
            "%Y-%m-%d %H:%M"
        )

        historic_param = {
            "exchange": "NSE",
            "symboltoken": "99926000",
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
          atm_strike = round(current_price / 50) * 50
          prev_close = df["Close"].iloc[-2]

          if current_price > prev_close:
            signal = f"BUY NIFTY {atm_strike} CE (CALL)"
          else:
            signal = f"BUY NIFTY {atm_strike} PE (PUT)"

          msg = (
              f"📊 निफ्टी ऑप्शन्स ट्रेड अलर्ट\n\n"
              f"📈 निफ्टी लाईव्ह भाव: {current_price}\n"
              f"🎯 सिस्टम सिग्नल: {signal}\n"
              f"⏱ वेळ: {now.strftime('%H:%M:%S')}"
          )
          send_telegram(msg)
          trade_done_today = True
      except Exception as e:
        print(f"Nifty Error: {e}")

    if current_time == "00:00":
      trade_done_today = False
    time.sleep(60)


# ----------------- २. क्रूड ऑईल बॉट फंक्शन -----------------
def run_crude():
  os.system("python crude_bot.py")


# ----------------- ३. नॅचरल गॅस बॉट फंक्शन -----------------
def run_natgas():
  os.system("python natgas_bot.py")


# ----------------- मुख्य मल्टिप्रोसेसिंग -----------------
if __name__ == "__main__":
  p_web = multiprocessing.Process(target=run_web)
  p1 = multiprocessing.Process(target=run_nifty)
  p2 = multiprocessing.Process(target=run_crude)
  p3 = multiprocessing.Process(target=run_natgas)

  p_web.start()
  p1.start()
  p2.start()
  p3.start()

  p_web.join()
  p1.join()
  p2.join()
  p3.join()
