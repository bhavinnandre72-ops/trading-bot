from datetime import datetime
import time
import numpy as np
import pandas as pd
import requests

# आवश्यक लायब्ररी इन्स्टॉल करण्यासाठी कमांड:
# pip install smartapi-python pandas numpy requests ta

from SmartApi import SmartConnect


class CommodityTelegramTrader:

  def __init__(
      self,
      api_key,
      client_id,
      pwd,
      telegram_token,
      chat_id,
      initial_capital=15000,
  ):
    self.api_key = api_key
    self.client_id = client_id
    self.pwd = pwd
    self.telegram_token = telegram_token
    self.chat_id = chat_id
    self.capital = initial_capital
    self.position = None
    self.entry_price = 0.0
    self.sl = 0.0
    self.target = 0.0
    self.quantity = 0

    self.smart_api = SmartConnect(api_key=self.api_key)

  def send_telegram_alert(self, message):
    """टेलिग्रामवर मेसेज पाठवणारे फंक्शन"""
    try:
      url = f'https://api.telegram.org/bot{self.telegram_token}/sendMessage'
      payload = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'Markdown'}
      response = requests.post(url, json=payload)
      if response.status_code != 200:
        print('टेलीग्राम अलर्ट पाठवण्यात एरर आली:', response.text)
    except Exception as e:
      print('Telegram Error:', e)

  def login(self):
    try:
      data = self.smart_api.generateSession(self.client_id, self.pwd)
      if data['status']:
        print('Angel One API लॉगिन यशस्वी झाले!')
        self.send_telegram_alert(
            '🤖 *Commodity Algo Bot Started!*\nAngel One Login Successful.'
        )
      else:
        print('लॉगिन फेल झाले:', data['message'])
    except Exception as e:
      print('लॉगिन करताना एरर आली:', e)

  def calculate_indicators(self, df):
    # 1. Moving Average 60 (SMA 60)
    df['MA_60'] = df['Close'].rolling(window=60).mean()

    # 2. Stoch RSI (Upper: 75, Lower: 35)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    rsi_low = df['RSI'].rolling(window=14).min()
    rsi_high = df['RSI'].rolling(window=14).max()
    df['Stoch_RSI_%K'] = ((df['RSI'] - rsi_low) / (rsi_high - rsi_low)) * 100
    df['Stoch_RSI_%D'] = df['Stoch_RSI_%K'].rolling(window=3).mean()

    return df

  def execute_paper_trade(self, df, symbol):
    df = self.calculate_indicators(df)
    i = len(df) - 1

    current_close = df['Close'].iloc[i]
    prev_close = df['Close'].iloc[i - 1]
    curr_ma = df['MA_60'].iloc[i]
    prev_ma = df['MA_60'].iloc[i - 1]
    stoch_k = df['Stoch_RSI_%K'].iloc[i]

    # पोझिशन नसताना नवीन एंट्री शोधणे
    if self.position is None:
      # --- BUY / CE ENTRY ---
      if (
          current_close > curr_ma
          and prev_close <= prev_ma
          and (stoch_k > 35 or stoch_k > 75)
      ):
        sl_price = df['Low'].iloc[i - 1]
        risk = current_close - sl_price
        target_price = current_close + (2 * risk)  # 1:2 टार्गेट

        self.quantity = max(1, int(self.capital / current_close))
        self.position = 'BUY'
        self.entry_price = current_close
        self.sl = sl_price
        self.target = target_price

        # टेलिग्राम अलर्ट मेसेज
        msg = (
            f'🟢 *COMMODITY BUY / CE SIGNAL* 🟢\n\n'
            f'📦 *Symbol:* {symbol}\n'
            f'💰 *Entry Price:* {current_close}\n'
            f'🛑 *Stop Loss:* {sl_price}\n'
            f'🎯 *Target:* {target_price}\n'
            f'📊 *Quantity:* {self.quantity}\n'
            f'💼 *Capital:* ₹{self.capital}'
        )
        self.send_telegram_alert(msg)
        print(msg)

      # --- SELL / PE ENTRY ---
      elif (
          current_close < curr_ma
          and prev_close >= prev_ma
          and (stoch_k < 75 or stoch_k < 35)
      ):
        sl_price = df['High'].iloc[i - 1]
        risk = sl_price - current_close
        target_price = current_close - (2 * risk)

        self.quantity = max(1, int(self.capital / current_close))
        self.position = 'SELL'
        self.entry_price = current_close
        self.sl = sl_price
        self.target = target_price

        # टेलिग्राम अलर्ट मेसेज
        msg = (
            f'🔴 *COMMODITY SELL / PE SIGNAL* 🔴\n\n'
            f'📦 *Symbol:* {symbol}\n'
            f'💰 *Entry Price:* {current_close}\n'
            f'🛑 *Stop Loss:* {sl_price}\n'
            f'🎯 *Target:* {target_price}\n'
            f'📊 *Quantity:* {self.quantity}\n'
            f'💼 *Capital:* ₹{self.capital}'
        )
        self.send_telegram_alert(msg)
        print(msg)

    # चालू ट्रेडसाठी SL किंवा Target हिट होणे तपासणे
    elif self.position == 'BUY':
      if current_close <= self.sl:
        pnl = (self.sl - self.entry_price) * self.quantity
        self.capital += pnl
        msg = (
            f'❌ *BUY TRADE SL HIT* ❌\nSymbol: {symbol}\nLoss: ₹{pnl}\nUpdated'
            f' Capital: ₹{self.capital}'
        )
        self.send_telegram_alert(msg)
        self.position = None
      elif current_close >= self.target:
        pnl = (self.target - self.entry_price) * self.quantity
        self.capital += pnl
        msg = (
            f'✅ *BUY TRADE TARGET HIT* ✅\nSymbol: {symbol}\nProfit:'
            f' ₹{pnl}\nUpdated Capital: ₹{self.capital}'
        )
        self.send_telegram_alert(msg)
        self.position = None

    elif self.position == 'SELL':
      if current_close >= self.sl:
        pnl = (self.entry_price - self.sl) * self.quantity
        self.capital += pnl
        msg = (
            f'❌ *SELL TRADE SL HIT* ❌\nSymbol: {symbol}\nLoss: ₹{pnl}\nUpdated'
            f' Capital: ₹{self.capital}'
        )
        self.send_telegram_alert(msg)
        self.position = None
      elif current_close <= self.target:
        pnl = (self.entry_price - self.target) * self.quantity
        self.capital += pnl
        msg = (
            f'✅ *SELL TRADE TARGET HIT* ✅\nSymbol: {symbol}\nProfit:'
            f' ₹{pnl}\nUpdated Capital: ₹{self.capital}'
        )
        self.send_telegram_alert(msg)
        self.position = None


# --- मुख्य प्रोग्राम (तुमची माहिती इथे भरलेली आहे) ---
if __name__ == '__main__':
  API_KEY = 'iemEXsyV'
  CLIENT_ID = 'B253694'
  PWD = '7172'  # तुमचा पिन

  TELEGRAM_TOKEN = '9248058546:AAGWN9FI9MjTgbw5xlAI3QiPUL4Ia2dUvLI'
  CHAT_ID = '9248058546'

  trader = CommodityTelegramTrader(
      API_KEY,
      CLIENT_ID,
      PWD,
      TELEGRAM_TOKEN,
      CHAT_ID,
      initial_capital=15000,
  )

  # बॉट सुरू झाल्याची टेस्ट करण्यासाठी खालील ओळ अनकमेंट करून रन करा:
  trader.send_telegram_alert(
      '🚀 *कमोडिटी अल्गो ट्रेडिंग बॉट यशस्वीरित्या सुरू झाला आहे!*'
  )

  print(
      'Telegram Alert सह कमोडिटी अल्गो ट्रेडिंग सिस्टीम तयार आहे! (Capital:'
      ' ₹15,000)'
  )
