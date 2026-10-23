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
  return "Trading Bot Status: ONLINE (Nifty, Sensex, Crude & NatGas)"


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


# ----------------- १. निफ्टी ५० टास्क -----------------
def run_nifty():
  time.sleep(3)
  send_telegram(
      "🚀 [SYSTEM ONLINE] Bhavin Multi-Market Trading Bot Active (Nifty, Sensex,"
      " Crude, NatGas)!"
  )

  nifty_done = False
  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if "09:15" <= current_time <= "15:30" and not nifty_done:
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")

          historic_param = {
              "exchange": "NSE",
              "symboltoken": "99926000",
              "interval": "ONE_HOUR",
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
            current_price = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]

            atm_strike = round(current_price / 50) * 50
            signal = (
                f"BUY NIFTY {atm_strike} CE"
                if current_price > prev_close
                else f"BUY NIFTY {atm_strike} PE"
            )

            msg = (
                f"📊 [NIFTY 50 ALERT]\n\n"
                f"📈 स्पोर्ट भाव: ₹{current_price}\n"
                f"🎯 सिग्नल: {signal}\n"
                f"⏱ वेळ: {now.strftime('%I:%M:%S %p')}"
            )
            send_telegram(msg)
            nifty_done = True

      if current_time == "00:00":
        nifty_done = False
    except Exception as e:
      print(f"Nifty Error: {e}")
    time.sleep(60)


# ----------------- २. सेन्सेक्स टास्क -----------------
def run_sensex():
  time.sleep(10)
  sensex_done = False
  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if "09:15" <= current_time <= "15:30" and not sensex_done:
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")

          historic_param = {
              "exchange": "BSE",
              "symboltoken": "99919000",
              "interval": "ONE_HOUR",
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
            current_price = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]

            atm_strike = round(current_price / 100) * 100
            signal = (
                f"BUY SENSEX {atm_strike} CE"
                if current_price > prev_close
                else f"BUY SENSEX {atm_strike} PE"
            )

            msg = (
                f"📊 [SENSEX ALERT]\n\n"
                f"📈 स्पोर्ट भाव: ₹{current_price}\n"
                f"🎯 सिग्नल: {signal}\n"
                f"⏱ वेळ: {now.strftime('%I:%M:%S %p')}"
            )
            send_telegram(msg)
            sensex_done = True

      if current_time == "00:00":
        sensex_done = False
    except Exception as e:
      print(f"Sensex Error: {e}")
    time.sleep(60)


# ----------------- ३. क्रुड ऑइल टास्क (MCX) -----------------
def run_crude():
  time.sleep(15)
  crude_done = False
  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      # MCX मार्केट वेळ सामान्यतः सकाळी १० ते रात्री ११:३० पर्यंत असते
      if "10:00" <= current_time <= "23:30" and not crude_done:
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")

          # Crude Oil साठी MCX टोकन वापरा (उदा. क्रूड ऑइल फ्युचर्स टोकन)
          historic_param = {
              "exchange": "MCX",
              "symboltoken": (
                  "225547"
              ),  # तुमच्याकडील योग्य क्रूड टोकन इथे टाकू शकता
              "interval": "ONE_HOUR",
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
            current_price = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]

            signal = (
                f"BUY CRUDEOIL CE"
                if current_price > prev_close
                else f"BUY CRUDEOIL PE"
            )

            msg = (
                f"🛢️ [CRUDE OIL ALERT]\n\n"
                f"📈 भाव: ₹{current_price}\n"
                f"🎯 सिग्नल: {signal}\n"
                f"⏱ वेळ: {now.strftime('%I:%M:%S %p')}"
            )
            send_telegram(msg)
            crude_done = True

      if current_time == "00:00":
        crude_done = False
    except Exception as e:
      print(f"Crude Error: {e}")
    time.sleep(60)


# ----------------- ४. नॅचरल गॅस टास्क (MCX) -----------------
def run_natgas():
  time.sleep(20)
  natgas_done = False
  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if "10:00" <= current_time <= "23:30" and not natgas_done:
        smartApi = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")

          # Natural Gas साठी MCX टोकन वापरा
          historic_param = {
              "exchange": "MCX",
              "symboltoken": (
                  "225721"
              ),  # तुमच्याकडील योग्य नॅचरल गॅस टोकन इथे टाकू शकता
              "interval": "ONE_HOUR",
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
            current_price = df["Close"].iloc[-1]
            prev_close = df["Close"].iloc[-2]

            signal = (
                f"BUY NATURALGAS CE"
                if current_price > prev_close
                else f"BUY NATURALGAS PE"
            )

            msg = (
                f"🔥 [NATURAL GAS ALERT]\n\n"
                f"📈 भाव: ₹{current_price}\n"
                f"🎯 सिग्नल: {signal}\n"
                f"⏱ वेळ: {now.strftime('%I:%M:%S %p')}"
            )
            send_telegram(msg)
            natgas_done = True

      if current_time == "00:00":
        natgas_done = False
    except Exception as e:
      print(f"NatGas Error: {e}")
    time.sleep(60)


# ----------------- मुख्य एक्झिक्युशन -----------------
if __name__ == "__main__":
  # सर्व चार मार्केट्ससाठी स्वतंत्र थ्रेड्स सुरू करा
  threading.Thread(target=run_nifty, daemon=True).start()
  threading.Thread(target=run_sensex, daemon=True).start()
  threading.Thread(target=run_crude, daemon=True).start()
  threading.Thread(target=run_natgas, daemon=True).start()

  # फ्लॅस्क वेब सर्व्हेर सुरू करा
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
  
