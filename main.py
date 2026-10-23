from datetime import datetime, timedelta
import os
import threading
import time
from flask import Flask
import pandas as pd
from SmartApi.smartConnect import SmartConnect
import pyotp
import requests

# ----------------- फ्लॅस्क वेब सर्व्हेर -----------------
app = Flask(__name__)


@app.route("/")
def home():
  return "Trading Bot Status: ONLINE (5-Min TF Active)"


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
    res = requests.post(url, json=payload, timeout=10)
    print("Telegram Response:", res.status_code)
  except Exception as e:
    print(f"Telegram Delivery Error: {e}")


# ----------------- १. निफ्टी ५० (5-Min) -----------------
def run_nifty():
  time.sleep(3)
  send_telegram(
      "🚀 [5-MIN BOT ONLINE] Nifty, Sensex, Crude & NatGas 5-Min Strategy"
      " Active!"
  )

  last_candle_time = None
  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if "09:15" <= current_time <= "15:30":
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")

          historic_param = {
              "exchange": "NSE",
              "symboltoken": "99926000",
              "interval": "FIVE_MINUTE",  # ५ मिनिटांची कॅण्डल
              "fromdate": from_date,
              "todate": to_date,
          }

          history = smartApi.getCandleData(historic_param)
          if history and "data" in history and len(history["data"]) > 1:
            df = pd.DataFrame(
                history["data"],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            df["Close"] = df["Close"].astype(float)

            current_candle_time = df["Date"].iloc[-1]
            current_price = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]

            # जर नवीन ५ मिनिटांची कॅण्डल आली असेल तरच अलर्ट पाठवा
            if current_candle_time != last_candle_time:
              atm_strike = round(current_price / 50) * 50
              signal = (
                  f"BUY NIFTY {atm_strike} CE"
                  if current_price > prev_close
                  else f"BUY NIFTY {atm_strike} PE"
              )

              msg = (
                  f"📊 [NIFTY 5-MIN ALERT]\n\n"
                  f"📈 स्पोर्ट भाव: ₹{current_price}\n"
                  f"🎯 सिग्नल: {signal}\n"
                  f"⏱ कॅण्डल वेळ: {current_candle_time}"
              )
              send_telegram(msg)
              last_candle_time = current_candle_time

    except Exception as e:
      print(f"Nifty Error: {e}")

    time.sleep(60)   दर मिनिटाला चेक करेल


# ----------------- २. सेन्सेक्स (5-Min) -----------------
def run_sensex():
  time.sleep(10)
  last_candle_time = None
  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if "09:15" <= current_time <= "15:30":
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")

          historic_param = {
              "exchange": "BSE",
              "symboltoken": "99919000",
              "interval": "FIVE_MINUTE",
              "fromdate": from_date,
              "todate": to_date,
          }

          history = smartApi.getCandleData(historic_param)
          if history and "data" in history and len(history["data"]) > 1:
            df = pd.DataFrame(
                history["data"],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            df["Close"] = df["Close"].astype(float)

            current_candle_time = df["Date"].iloc[-1]
            current_price = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]

            if current_candle_time != last_candle_time:
              atm_strike = round(current_price / 100) * 100
              signal = (
                  f"BUY SENSEX {atm_strike} CE"
                  if current_price > prev_close
                  else f"BUY SENSEX {atm_strike} PE"
              )

              msg = (
                  f"📊 [SENSEX 5-MIN ALERT]\n\n"
                  f"📈 स्पोर्ट भाव: ₹{current_price}\n"
                  f"🎯 सिग्नल: {signal}\n"
                  f"⏱ कॅण्डल वेळ: {current_candle_time}"
              )
              send_telegram(msg)
              last_candle_time = current_candle_time

    except Exception as e:
      print(f"Sensex Error: {e}")

    time.sleep(60)


# ----------------- ३. क्रुड ऑइल (5-Min) -----------------
def run_crude():
  time.sleep(15)
  last_candle_time = None
  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if "10:00" <= current_time <= "23:30":
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")

          historic_param = {
              "exchange": "MCX",
              "symboltoken": "225547",
              "interval": "FIVE_MINUTE",
              "fromdate": from_date,
              "todate": to_date,
          }

          history = smartApi.getCandleData(historic_param)
          if history and "data" in history and len(history["data"]) > 1:
            df = pd.DataFrame(
                history["data"],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            df["Close"] = df["Close"].astype(float)

            current_candle_time = df["Date"].iloc[-1]
            current_price = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]

            if current_candle_time != last_candle_time:
              signal = (
                  f"BUY CRUDEOIL CE"
                  if current_price > prev_close
                  else f"BUY CRUDEOIL PE"
              )

              msg = (
                  f"🛢️ [CRUDE OIL 5-MIN ALERT]\n\n"
                  f"📈 भाव: ₹{current_price}\n"
                  f"🎯 सिग्नल: {signal}\n"
                  f"⏱ कॅण्डल वेळ: {current_candle_time}"
              )
              send_telegram(msg)
              last_candle_time = current_candle_time

    except Exception as e:
      print(f"Crude Error: {e}")

    time.sleep(60)


# ----------------- ४. नॅचरल गॅस (5-Min) -----------------
def run_natgas():
  time.sleep(20)
  last_candle_time = None
  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if "10:00" <= current_time <= "23:30":
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")

          historic_param = {
              "exchange": "MCX",
              "symboltoken": "225721",
              "interval": "FIVE_MINUTE",
              "fromdate": from_date,
              "todate": to_date,
          }

          history = smartApi.getCandleData(historic_param)
          if history and "data" in history and len(history["data"]) > 1:
            df = pd.DataFrame(
                history["data"],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            df["Close"] = df["Close"].astype(float)

            current_candle_time = df["Date"].iloc[-1]
            current_price = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]

            if current_candle_time != last_candle_time:
              signal = (
                  f"BUY NATURALGAS CE"
                  if current_price > prev_close
                  else f"BUY NATURALGAS PE"
              )

              msg = (
                  f"🔥 [NATURAL GAS 5-MIN ALERT]\n\n"
                  f"📈 भाव: ₹{current_price}\n"
                  f"🎯 सिग्नल: {signal}\n"
                  f"⏱ कॅण्डल वेळ: {current_candle_time}"
              )
              send_telegram(msg)
              last_candle_time = current_candle_time

    except Exception as e:
      print(f"NatGas Error: {e}")

    time.sleep(60)


# ----------------- मुख्य एक्झिक्युशन -----------------
if __name__ == "__main__":
  threading.Thread(target=run_nifty, daemon=True).start()
  threading.Thread(target=run_sensex, daemon=True).start()
  threading.Thread(target=run_crude, daemon=True).start()
  threading.Thread(target=run_natgas, daemon=True).start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
          
