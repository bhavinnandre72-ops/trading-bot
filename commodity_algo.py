from datetime import datetime, timedelta
import time
import numpy as np
import pandas as pd
import requests

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

  def login_and_fetch_data(self, symbol_token, exchange='MCX', interval='FIVE_MINUTE'):
    try:
      data = self.smart_api.generateSession(self.client_id, self.pwd)
      if data['status']:
        print('Angel One API लॉगिन यशस्वी झाले!')
        
        # मागील काही दिवसांचा डेटा फेच करणे
        to_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        from_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M')
        
        historic_param = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date
        }
        
        response = self.smart_api.getCandleData(historic_param)
        if response['status'] and response['data']:
          # डेटाला Pandas DataFrame मध्ये कन्वर्ट करणे
          df = pd.DataFrame(response['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
          df['Close'] = df['Close'].astype(float)
          df['High'] = df['High'].astype(float)
          df['Low'] = df['Low'].astype(float)
          return df
        else:
          print('डेटा फेच करण्यात अपयश:', response.get('message'))
          return None
      else:
        print('लॉगिन फेल झाले:', data['message'])
        return None
    except Exception as e:
      print('लॉगिन किंवा डेटा फेच करताना एरर आली:', e)
      return None

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

  def run_strategy(self, symbol_name, symbol_token):
    print(f'{symbol_name} साठी डेटा तपासत आहे...')
    df = self.login_and_fetch_data(symbol_token)
    
    if df is not None and len(df) > 60:
      df = self.calculate_indicators(df)
      i = len(df) - 1

      current_close = df['Close'].iloc[i]
      prev_close = df['Close'].iloc[i - 1]
      curr_ma = df['MA_60'].iloc[i]
      prev_ma = df['MA_60'].iloc[i - 1]
      stoch_k = df['Stoch_RSI_%K'].iloc[i]

      # --- BUY / CE ENTRY ---
      if current_close > curr_ma and prev_close <= prev_ma and (stoch_k > 35 or stoch_k > 75):
        sl_price = df['Low'].iloc[i - 1]
        risk = current_close - sl_price
        target_price = current_close + (2 * risk)
        self.quantity = max(1, int(self.capital / current_close))

        msg = (
            f'🟢 *COMMODITY BUY / CE SIGNAL* 🟢\n\n'
            f'📦 *Symbol:* {symbol_name}\n'
            f'💰 *Entry Price:* {current_close}\n'
            f'🛑 *Stop Loss:* {sl_price}\n'
            f'🎯 *Target:* {target_price}\n'
            f'📊 *Quantity:* {self.quantity}\n'
            f'💼 *Capital:* ₹{self.capital}'
        )
        self.send_telegram_alert(msg)
        print(msg)

      # --- SELL / PE ENTRY ---
      elif current_close < curr_ma and prev_close >= prev_ma and (stoch_k < 75 or stoch_k < 35):
        sl_price = df['High'].iloc[i - 1]
        risk = sl_price - current_close
        target_price = current_close - (2 * risk)
        self.quantity = max(1, int(self.capital / current_close))

        msg = (
            f'🔴 *COMMODITY SELL / PE SIGNAL* 🔴\n\n'
            f'📦 *Symbol:* {symbol_name}\n'
            f'💰 *Entry Price:* {current_close}\n'
            f'🛑 *Stop Loss:* {sl_price}\n'
            f'🎯 *Target:* {target_price}\n'
            f'📊 *Quantity:* {self.quantity}\n'
            f'💼 *Capital:* ₹{self.capital}'
        )
        self.send_telegram_alert(msg)
        print(msg)
      else:
        print(f'{symbol_name} साठी सध्या कोणतीही एंट्री नाही.')
    else:
      print('डेटा अपुरा आहे किंवा फेच झाला नाही.')


if __name__ == '__main__':
  API_KEY = 'iemEXsyV'
  CLIENT_ID = 'B253694'
  PWD = '7172'

  TELEGRAM_TOKEN = '9248058546:AAGWN9FI9MjTgbw5xlAI3QiPUL4Ia2dUvLI'
  CHAT_ID = '9248058546'

  trader = CommodityTelegramTrader(
      API_KEY, CLIENT_ID, PWD, TELEGRAM_TOKEN, CHAT_ID, initial_capital=15000
  )

  # बॉट सुरू झाल्याचा टेस्ट मेसेज
  trader.send_telegram_alert('🚀 *कमोडिटी अल्गो ट्रेडिंग बॉट यशस्वीरित्या सुरू झाला आहे!*')

  # क्रूड ऑइल मिनीचे उदाहरण (टोकन नंबर टाका, उदा. क्रूड ऑइलचा टोकन)
  trader.run_strategy('CRUDEOIL', '260937')

