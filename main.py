from datetime import datetime, timedelta
import os
import threading
import time
from flask import Flask
import pandas as pd
from SmartApi.smartConnect import SmartConnect
import pyotp
import requests

app = Flask(__name__)


@app.route("/")
def home():
  return "Advanced VWAP Scalping Bot Status: ONLINE (Active with Sensex)"


# ----------------- क्रेडेंशियल्स -----------------
API_KEY = "ienEXsyV"
CLIENT_ID = "8253694"
PWD = "7172"
TOTP_SECRET = "D4YN4THBA3VFIW5C7YLUQFINVIE"

TELEGRAM_TOKEN = "8667131376:AAFRsq79krKkfHr8OFzD0cVh6vooie6jYcI"
TELEGRAM_CHAT_ID = "1486399523"


def send_telegram(message):
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Telegram Error: {e}")


# सुरक्षितपणे TOTP जनरेट करण्याचे फंक्शन (Padding Error Fix)
def get_totp_token():
  try:
    clean_secret = TOTP_SECRET.strip().replace(" ", "").upper()
    missing_padding = len(clean_secret) % 8
    if missing_padding:
      clean_secret += "=" * (8 - missing_padding)
    return pyotp.TOTP(clean_secret).now()
  except Exception as e:
    print(f"TOTP Generation Error: {e}")
    return None


# ----------------- VWAP & RSI इंडिकेटर कॅल्क्युलेशन्स -----------------
def calculate_indicators(df):
  typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
  df["VWAP"] = (typical_price * df["Volume"]).cumsum() / df["Volume"].cumsum()

  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / loss
  df["RSI"] = 100 - (100 / (1 + rs))

  return df


# ----------------- OI (Open Interest) फिल्टर -----------------
def check_oi_filter(smartApi, symboltoken, exchange="NSE"):
  try:
    search_data = smartApi.getMarketData(
        {"mode": "FULL", "exchangeTokens": {exchange: [symboltoken]}}
    )
    if search_data and "data" in search_data:
      return True
  except Exception as e:
    print(f"OI Fetch Error: {e}")
  return True


# ----------------- १. NIFTY 50 TRADING ENGINE (VWAP + RSI) -----------------
def run_nifty():
  time.sleep(3)
  send_telegram("🚀 [VWAP SCALPING BOT ONLINE] Nifty, Sensex, Crude & NatGas Active!")

  last_candle_time = None
  daily_trades = 0
  max_trades = 3
  active_position = None

  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if current_time == "09:15":
        daily_trades = 0
        active_position = None

      if "09:15" <= current_time <= "15:25":
        smartApi = SmartConnect(api_key=API_KEY)
        totp_code = get_totp_token()
        if not totp_code:
          time.sleep(30)
          continue

        data = smartApi.generateSession(CLIENT_ID, PWD, totp_code)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")

          history = smartApi.getCandleData({
              "exchange": "NSE",
              "symboltoken": "99926000",
              "interval": "FIVE_MINUTE",
              "fromdate": from_date,
              "todate": to_date,
          })

          if history and "data" in history and len(history["data"]) > 30:
            df = pd.DataFrame(
                history["data"],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            df[["Open", "High", "Low", "Close", "Volume"]] = df[
                ["Open", "High", "Low", "Close", "Volume"]
            ].astype(float)
            df = calculate_indicators(df)

            curr = df.iloc[-1]
            current_candle_time = curr["Date"]
            current_price = curr["Close"]
            vwap_val = curr["vwap"] if "vwap" in curr else curr["VWAP"]

            if active_position:
              if (
                  active_position["type"] == "CE"
                  and current_price <= active_position["sl"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price >= active_position["sl"]
              ):
                send_telegram(
                    f"🔴 [NIFTY SL HIT]\nExit Price: ₹{current_price}"
                )
                active_position = None
              elif (
                  active_position["type"] == "CE"
                  and current_price >= active_position["target"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price <= active_position["target"]
              ):
                send_telegram(
                    f"🟢 [NIFTY TARGET HIT] 🎉\nExit Price: ₹{current_price}"
                )
                active_position = None
              elif current_time >= "15:20":
                send_telegram(f"⏰ [AUTO SQUARE-OFF] Nifty at ₹{current_price}")
                active_position = None

            elif (
                daily_trades < max_trades
                and current_candle_time != last_candle_time
            ):
              oi_valid = check_oi_filter(smartApi, "99926000", "NSE")

              ce_cond = current_price > vwap_val and curr["RSI"] > 50 and oi_valid
              pe_cond = current_price < vwap_val and curr["RSI"] < 50 and oi_valid

              if ce_cond:
                atm_strike = round(current_price / 50) * 50
                sl = current_price - 25
                target = current_price + 45
                daily_trades += 1
                active_position = {
                    "type": "CE",
                    "entry": current_price,
                    "sl": sl,
                    "target": target,
                }
                last_candle_time = current_candle_time
                send_telegram(
                    f"🎯 [BUY NIFTY {atm_strike} CE (VWAP)]\nPrice:"
                    f" ₹{current_price}\nSL: {sl} | Target:"
                    f" {target}\nTrades: [{daily_trades}/3]"
                )

              elif pe_cond:
                atm_strike = round(current_price / 50) * 50
                sl = current_price + 25
                target = current_price - 45
                daily_trades += 1
                active_position = {
                    "type": "PE",
                    "entry": current_price,
                    "sl": sl,
                    "target": target,
                }
                last_candle_time = current_candle_time
                send_telegram(
                    f"🎯 [BUY NIFTY {atm_strike} PE (VWAP)]\nPrice:"
                    f" ₹{current_price}\nSL: {sl} | Target:"
                    f" {target}\nTrades: [{daily_trades}/3]"
                )

    except Exception as e:
      print(f"Nifty Error: {e}")

    time.sleep(30)


# ----------------- २. SENSEX TRADING ENGINE (VWAP + RSI) -----------------
def run_sensex():
  time.sleep(5)
  last_candle_time = None
  daily_trades = 0
  max_trades = 3
  active_position = None

  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if current_time == "09:15":
        daily_trades = 0
        active_position = None

      if "09:15" <= current_time <= "15:25":
        smartApi = SmartConnect(api_key=API_KEY)
        totp_code = get_totp_token()
        if not totp_code:
          time.sleep(30)
          continue

        data = smartApi.generateSession(CLIENT_ID, PWD, totp_code)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")

          history = smartApi.getCandleData({
              "exchange": "BSE",
              "symboltoken": "99919000",
              "interval": "FIVE_MINUTE",
              "fromdate": from_date,
              "todate": to_date,
          })

          if history and "data" in history and len(history["data"]) > 30:
            df = pd.DataFrame(
                history["data"],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            df[["Open", "High", "Low", "Close", "Volume"]] = df[
                ["Open", "High", "Low", "Close", "Volume"]
            ].astype(float)
            df = calculate_indicators(df)

            curr = df.iloc[-1]
            current_candle_time = curr["Date"]
            current_price = curr["Close"]
            vwap_val = curr["vwap"] if "vwap" in curr else curr["VWAP"]

            if active_position:
              if (
                  active_position["type"] == "CE"
                  and current_price <= active_position["sl"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price >= active_position["sl"]
              ):
                send_telegram(
                    f"🔴 [SENSEX SL HIT]\nExit Price: ₹{current_price}"
                )
                active_position = None
              elif (
                  active_position["type"] == "CE"
                  and current_price >= active_position["target"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price <= active_position["target"]
              ):
                send_telegram(
                    f"🟢 [SENSEX TARGET HIT] 🎉\nExit Price: ₹{current_price}"
                )
                active_position = None
              elif current_time >= "15:20":
                send_telegram(f"⏰ [AUTO SQUARE-OFF] Sensex at ₹{current_price}")
                active_position = None

            elif (
                daily_trades < max_trades
                and current_candle_time != last_candle_time
            ):
              oi_valid = check_oi_filter(smartApi, "99919000", "BSE")

              ce_cond = current_price > vwap_val and curr["RSI"] > 50 and oi_valid
              pe_cond = current_price < vwap_val and curr["RSI"] < 50 and oi_valid

              if ce_cond:
                atm_strike = round(current_price / 100) * 100
                sl = current_price - 40
                target = current_price + 80
                daily_trades += 1
                active_position = {
                    "type": "CE",
                    "entry": current_price,
                    "sl": sl,
                    "target": target,
                }
                last_candle_time = current_candle_time
                send_telegram(
                    f"📈 [BUY SENSEX {atm_strike} CE (VWAP)]\nPrice:"
                    f" ₹{current_price}\nSL: {sl} | Target:"
                    f" {target}\nTrades: [{daily_trades}/3]"
                )

              elif pe_cond:
                atm_strike = round(current_price / 100) * 100
                sl = current_price + 40
                target = current_price - 80
                daily_trades += 1
                active_position = {
                    "type": "PE",
                    "entry": current_price,
                    "sl": sl,
                    "target": target,
                }
                last_candle_time = current_candle_time
                send_telegram(
                    f"📈 [BUY SENSEX {atm_strike} PE (VWAP)]\nPrice:"
                    f" ₹{current_price}\nSL: {sl} | Target:"
                    f" {target}\nTrades: [{daily_trades}/3]"
                )

    except Exception as e:
      print(f"Sensex Error: {e}")

    time.sleep(30)


# ----------------- ३. CRUDE OIL TRADING ENGINE (VWAP + RSI) -----------------
def run_crude():
  time.sleep(10)
  last_candle_time = None
  daily_trades = 0
  max_trades = 3
  active_position = None

  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if current_time == "10:00":
        daily_trades = 0
        active_position = None

      if "10:00" <= current_time <= "23:15":
        smartApi = SmartConnect(api_key=API_KEY)
        totp_code = get_totp_token()
        if not totp_code:
          time.sleep(30)
          continue

        data = smartApi.generateSession(CLIENT_ID, PWD, totp_code)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")

          history = smartApi.getCandleData({
              "exchange": "MCX",
              "symboltoken": "225547",
              "interval": "FIVE_MINUTE",
              "fromdate": from_date,
              "todate": to_date,
          })

          if history and "data" in history and len(history["data"]) > 30:
            df = pd.DataFrame(
                history["data"],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            df[["Open", "High", "Low", "Close", "Volume"]] = df[
                ["Open", "High", "Low", "Close", "Volume"]
            ].astype(float)
            df = calculate_indicators(df)

            curr = df.iloc[-1]
            current_candle_time = curr["Date"]
            current_price = curr["Close"]
            vwap_val = curr["vwap"] if "vwap" in curr else curr["VWAP"]

            if active_position:
              if (
                  active_position["type"] == "CE"
                  and current_price <= active_position["sl"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price >= active_position["sl"]
              ):
                send_telegram(
                    f"🔴 [CRUDE OIL SL HIT] Exited at ₹{current_price}"
                )
                active_position = None
              elif (
                  active_position["type"] == "CE"
                  and current_price >= active_position["target"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price <= active_position["target"]
              ):
                send_telegram(
                    f"🟢 [CRUDE OIL TARGET HIT] 🎉 Exited at ₹{current_price}"
                )
                active_position = None

            elif (
                daily_trades < max_trades
                and current_candle_time != last_candle_time
            ):
              if current_price > vwap_val and curr["RSI"] > 50:
                sl = current_price - 20
                target = current_price + 35
                daily_trades += 1
                active_position = {
                    "type": "CE",
                    "entry": current_price,
                    "sl": sl,
                    "target": target,
                }
                last_candle_time = current_candle_time
                send_telegram(
                    f"🛢️ [BUY CRUDE OIL CE (VWAP)]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}"
                )
              elif current_price < vwap_val and curr["RSI"] < 50:
                sl = current_price + 20
                target = current_price - 35
                daily_trades += 1
                active_position = {
                    "type": "PE",
                    "entry": current_price,
                    "sl": sl,
                    "target": target,
                }
                last_candle_time = current_candle_time
                send_telegram(
                    f"🛢️ [BUY CRUDE OIL PE (VWAP)]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}"
                )

    except Exception as e:
      print(f"Crude Error: {e}")

    time.sleep(30)


# ----------------- ४. NATURAL GAS TRADING ENGINE (VWAP + RSI) -----------------
def run_natgas():
  time.sleep(15)
  last_candle_time = None
  daily_trades = 0
  max_trades = 3
  active_position = None

  while True:
    try:
      now = datetime.now()
      current_time = now.strftime("%H:%M")

      if current_time == "10:00":
        daily_trades = 0
        active_position = None

      if "10:00" <= current_time <= "23:15":
        smartApi = SmartConnect(api_key=API_KEY)
        totp_code = get_totp_token()
        if not totp_code:
          time.sleep(30)
          continue

        data = smartApi.generateSession(CLIENT_ID, PWD, totp_code)

        if data and "data" in data and "jwtToken" in data["data"]:
          smartApi.setAccessToken(data["data"]["jwtToken"])
          to_date = now.strftime("%Y-%m-%d %H:%M")
          from_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")

          history = smartApi.getCandleData({
              "exchange": "MCX",
              "symboltoken": "225721",
              "interval": "FIVE_MINUTE",
              "fromdate": from_date,
              "todate": to_date,
          })

          if history and "data" in history and len(history["data"]) > 30:
            df = pd.DataFrame(
                history["data"],
                columns=["Date", "Open", "High", "Low", "Close", "Volume"],
            )
            df[["Open", "High", "Low", "Close", "Volume"]] = df[
                ["Open", "High", "Low", "Close", "Volume"]
            ].astype(float)
            df = calculate_indicators(df)

            curr = df.iloc[-1]
            current_candle_time = curr["Date"]
            current_price = curr["Close"]
            vwap_val = curr["vwap"] if "vwap" in curr else curr["VWAP"]

            if active_position:
              if (
                  active_position["type"] == "CE"
                  and current_price <= active_position["sl"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price >= active_position["sl"]
              ):
                send_telegram(
                    f"🔴 [NATURAL GAS SL HIT] Exited at ₹{current_price}"
                )
                active_position = None
              elif (
                  active_position["type"] == "CE"
                  and current_price >= active_position["target"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price <= active_position["target"]
              ):
                send_telegram(
                    f"🟢 [NATURAL GAS TARGET HIT] 🎉 Exited at"
                    f" ₹{current_price}"
                )
                active_position = None

            elif (
                daily_trades < max_trades
                and current_candle_time != last_candle_time
            ):
              if current_price > vwap_val and curr["RSI"] > 50:
                sl = current_price - 2
                target = current_price + 4
                daily_trades += 1
                active_position = {
                    "type": "CE",
                    "entry": current_price,
                    "sl": sl,
                    "target": target,
                }
                last_candle_time = current_candle_time
                send_telegram(
                    f"🔥 [BUY NATURAL GAS CE (VWAP)]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}"
                )
              elif current_price < vwap_val and curr["RSI"] < 50:
                sl = current_price + 2
                target = current_price - 4
                daily_trades += 1
                active_position = {
                    "type": "PE",
                    "entry": current_price,
                    "sl": sl,
                    "target": target,
                }
                last_candle_time = current_candle_time
                send_telegram(
                    f"🔥 [BUY NATURAL GAS PE (VWAP)]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}"
                )

    except Exception as e:
      print(f"NatGas Error: {e}")

    time.sleep(30)


# ----------------- MAIN START
