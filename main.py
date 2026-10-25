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
  return "Advanced Scalping Bot Status: ONLINE (Error-Handled Active)"


# ----------------- क्रेडेंशियल्स -----------------
API_KEY = "ienEXsyV"
CLIENT_ID = "8253694"
PWD = "Ji72"
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


# सुरक्षितपणे TOTP जनरेट करण्याचे फंक्शन (Incorrect padding एरर टाळण्यासाठी)
def get_totp_token():
  try:
    # क्लिनिंग आणि पॅडिंग तपासणी
    clean_secret = TOTP_SECRET.strip().replace(" ", "")
    return pyotp.TOTP(clean_secret).now()
  except Exception as e:
    print(f"TOTP Generation Error: {e}")
    return None


# ----------------- तांत्रिक इंडिकेटर कॅल्क्युलेशन्स -----------------
def calculate_indicators(df):
  df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
  df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()

  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / loss
  df["RSI"] = 100 - (100 / (1 + rs))

  period = 10
  multiplier = 3
  df["ATR"] = (
      pd.concat([
          df["High"] - df["Low"],
          (df["High"] - df["Close"].shift()).abs(),
          (df["Low"] - df["Close"].shift()).abs(),
      ],
      axis=1,)
      .max(axis=1)
      .rolling(period)
      .mean()
  )

  hl2 = (df["High"] + df["Low"]) / 2
  df["Basic_UB"] = hl2 + (multiplier * df["ATR"])
  df["Basic_LB"] = hl2 - (multiplier * df["ATR"])
  df["Final_UB"] = df["Basic_UB"]
  df["Final_LB"] = df["Basic_LB"]

  for i in range(1, len(df)):
    if (
        df["Basic_UB"].iloc[i] < df["Final_UB"].iloc[i - 1]
        or df["Close"].iloc[i - 1] > df["Final_UB"].iloc[i - 1]
    ):
      df.loc[df.index[i], "Final_UB"] = df["Basic_UB"].iloc[i]
    else:
      df.loc[df.index[i], "Final_UB"] = df["Final_UB"].iloc[i - 1]

    if (
        df["Basic_LB"].iloc[i] > df["Final_LB"].iloc[i - 1]
        or df["Close"].iloc[i - 1] < df["Final_LB"].iloc[i - 1]
    ):
      df.loc[df.index[i], "Final_LB"] = df["Basic_LB"].iloc[i]
    else:
      df.loc[df.index[i], "Final_LB"] = df["Final_LB"].iloc[i - 1]

  df["Supertrend"] = True
  for i in range(1, len(df)):
    if df["Close"].iloc[i] > df["Final_UB"].iloc[i - 1]:
      df.loc[df.index[i], "Supertrend"] = True
    elif df["Close"].iloc[i] < df["Final_LB"].iloc[i - 1]:
      df.loc[df.index[i], "Supertrend"] = False
    else:
      df.loc[df.index[i], "Supertrend"] = df["Supertrend"].iloc[i - 1]

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


# ----------------- १. NIFTY 50 TRADING ENGINE -----------------
def run_nifty():
  time.sleep(3)
  send_telegram("🚀 [5-MIN SCALPING BOT ONLINE] Nifty, Crude & NatGas Active!")

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
            df[["Open", "High", "Low", "Close"]] = df[
                ["Open", "High", "Low", "Close"]
            ].astype(float)
            df = calculate_indicators(df)

            curr = df.iloc[-1]
            prev = df.iloc[-2]
            current_candle_time = curr["Date"]
            current_price = curr["Close"]

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

              ce_cond = (
                  curr["EMA9"] > curr["EMA21"]
                  and prev["EMA9"] <= prev["EMA21"]
                  and curr["Supertrend"] == True
                  and curr["RSI"] > 50
                  and oi_valid
              )

              pe_cond = (
                  curr["EMA9"] < curr["EMA21"]
                  and prev["EMA9"] >= prev["EMA21"]
                  and curr["Supertrend"] == False
                  and curr["RSI"] < 45
                  and oi_valid
              )

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
                    f"🎯 [BUY NIFTY {atm_strike} CE]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}\nTrades: [{daily_trades}/3]"
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
                    f"🎯 [BUY NIFTY {atm_strike} PE]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}\nTrades: [{daily_trades}/3]"
                )

    except Exception as e:
      print(f"Nifty Error: {e}")

    time.sleep(30)


# ----------------- २. CRUDE OIL TRADING ENGINE -----------------
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
            df[["Open", "High", "Low", "Close"]] = df[
                ["Open", "High", "Low", "Close"]
            ].astype(float)
            df = calculate_indicators(df)

            curr = df.iloc[-1]
            prev = df.iloc[-2]
            current_candle_time = curr["Date"]
            current_price = curr["Close"]

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
              if (
                  curr["EMA9"] > curr["EMA21"]
                  and prev["EMA9"] <= prev["EMA21"]
                  and curr["Supertrend"] == True
                  and curr["RSI"] > 50
              ):
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
                    f"🛢️ [BUY CRUDE OIL CE]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}"
                )
              elif (
                  curr["EMA9"] < curr["EMA21"]
                  and prev["EMA9"] >= prev["EMA21"]
                  and curr["Supertrend"] == False
                  and curr["RSI"] < 45
              ):
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
                    f"🛢️ [BUY CRUDE OIL PE]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}"
                )

    except Exception as e:
      print(f"Crude Error: {e}")

    time.sleep(30)


# ----------------- ३. NATURAL GAS TRADING ENGINE -----------------
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
            df[["Open", "High", "Low", "Close"]] = df[
                ["Open", "High", "Low", "Close"]
            ].astype(float)
            df = calculate_indicators(df)

            curr = df.iloc[-1]
            prev = df.iloc[-2]
            current_candle_time = curr["Date"]
            current_price = curr["Close"]

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
              if (
                  curr["EMA9"] > curr["EMA21"]
                  and prev["EMA9"] <= prev["EMA21"]
                  and curr["Supertrend"] == True
                  and curr["RSI"] > 50
              ):
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
                    f"🔥 [BUY NATURAL GAS CE]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}"
                )
              elif (
                  curr["EMA9"] < curr["EMA21"]
                  and prev["EMA9"] >= prev["EMA21"]
                  and curr["Supertrend"] == False
                  and curr["RSI"] < 45
              ):
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
                    f"🔥 [BUY NATURAL GAS PE]\nPrice: ₹{current_price}\nSL:"
                    f" {sl} | Target: {target}"
                )

    except Exception as e:
      print(f"NatGas Error: {e}")

    time.sleep(30)


# ----------------- MAIN START -----------------
if __name__ == "__main__":
  threading.Thread(target=run_nifty, daemon=True).start()
  threading.Thread(target=run_crude, daemon=True).start()
  threading.Thread(target=run_natgas, daemon=True).start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
  
