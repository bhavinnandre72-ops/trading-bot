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
  return "Advanced Scalping Bot Status: ONLINE (5-Min TF Active)"


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


# ----------------- तांत्रिक इंडिकेटर कॅल्क्युलेशन्स -----------------
def calculate_indicators(df):
  # EMA (9 & 21)
  df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
  df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()

  # RSI (14)
  delta = df["Close"].diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
  rs = gain / loss
  df["RSI"] = 100 - (100 / (1 + rs))

  # Supertrend (10, 3)
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
      fetched = search_data["data"]["fetched"][0]
      oi = fetched.get("opnInterest", 0)
      return True if oi > 0 else True
  except Exception as e:
    print(f"OI Fetch Error: {e}")
  return True


# ----------------- १. NIFTY 50 TRADING ENGINE -----------------
def run_nifty():
  time.sleep(3)
  send_telegram(
      "🚀 [5-MIN SCALPING BOT ONLINE]\nNifty, Crude & NatGas Active!\nStrategy:"
      " 9/21 EMA + Supertrend + RSI + OI Filter"
  )

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
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

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

            # SL / Target / Square-off Check
            if active_position:
              if (
                  active_position["type"] == "CE"
                  and current_price <= active_position["sl"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price >= active_position["sl"]
              ):
                msg = (
                    f"🔴 [NIFTY SL HIT - EXIT]\nType: {active_position['type']}\nExit"
                    f" Price: ₹{current_price}"
                )
                send_telegram(msg)
                active_position = None

              elif (
                  active_position["type"] == "CE"
                  and current_price >= active_position["target"]
              ) or (
                  active_position["type"] == "PE"
                  and current_price <= active_position["target"]
              ):
                msg = (
                    f"🟢 [NIFTY TARGET HIT - EXIT]\nType:"
                    f" {active_position['type']}\nExit Price:"
                    f" ₹{current_price} 🎉"
                )
                send_telegram(msg)
                active_position = None

              elif current_time >= "15:20":
                msg = (
                    "⏰ [AUTO SQUARE-OFF 15:20]\nExiting Nifty Position at"
                    f" ₹{current_price}"
                )
                send_telegram(msg)
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

                msg = (
                    f"🎯 [BUY NIFTY {atm_strike} CE]\n"
                    f"📈 एन्ट्री भाव: ₹{current_price}\n"
                    f"🛑 StopLoss: ₹{sl}\n"
                    f"🎯 Target: ₹{target}\n"
                    f"⏱ कॅण्डल: {current_candle_time}\n"
                    f"📊 Trade Count: [{daily_trades}/{max_trades}]"
                )
                send_telegram(msg)

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

                msg = (
                    f"🎯 [BUY NIFTY {atm_strike} PE]\n"
                    f"📉 एन्ट्री भाव: ₹{current_price}\n"
                    f"🛑 StopLoss: ₹{sl}\n"
                    f"🎯 Target: ₹{target}\n"
                    f"⏱ कॅण्डल: {current_candle_time}\n"
                    f"📊 Trade Count: [{daily_trades}/{max_trades}]"
                )
                send_telegram(msg)

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
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

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
                    f"🟢 [CRUDE OIL TARGET HIT] Exited at ₹{current_price} 🎉"
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
                    f" {sl} | Target: {target}\nTrades Today:"
                    f" [{daily_trades}/{max_trades}]"
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
                    f" {sl} | Target: {target}\nTrades Today:"
                    f" [{daily_trades}/{max_trades}]"
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
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smartApi.generateSession(CLIENT_ID, PWD, totp)

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
                    f"🟢 [NATURAL GAS TARGET HIT] Exited at ₹{current_price} 🎉"
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
                    f" {sl} | Target: {target}\nTrades Today:"
                    f" [{daily_trades}/{max_trades}]"
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
                    f" {sl} | Target: {target}\nTrades Today:"
                    f" [{daily_trades}/{max_trades}]"
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
