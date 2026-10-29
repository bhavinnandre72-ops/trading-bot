import time
import requests
from SmartApi import SmartConnect
import pandas as pd
import numpy as np

# ==================== 1. कॉन्फिगरेशन आणि एपीआय क्रेडेन्शियल ====================
API_KEY = "iemEXsyV"
CLIENT_ID = "B253694"
MPIN = "7172"
TOTP_KEY = "D4YNATHBA3VFIW5C7YUQPJNVIE"  # किंवा पासवर्ड

# टेलिग्राम बॉटची माहिती
TELEGRAM_BOT_TOKEN = "8667131376:AAE_b_p7lhL0xuK_bkxYJOAPMUFR9CIBLX0"
TELEGRAM_CHAT_ID = "1486399523"  # तुमचे चॅट आयडी

# ऑब्जेक्ट इनिशिलायझेशन
obj = SmartConnect(api_key=API_KEY)


def send_telegram_alert(message):
  """टेलिग्रामवर अलर्ट पाठवण्यासाठीचे फंक्शन"""
  try:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)
  except Exception as e:
    print(f"Telegram Error: {e}")


# ==================== 2. लॉगइन फंक्शन ====================
def angel_one_login():
  try:
    data = obj.generateSession(CLIENT_ID, MPIN)
    if data["status"]:
      print("एंजेल वन लॉगिन यशस्वी झाले!")
      return True
    else:
      print("लॉगिन अयशस्वी:", data)
      return False
  except Exception as e:
    print(f"Login Exception: {e}")
    return False


# ==================== 3. सपोर्ट आणि रेजिस्टन्स काढणे (15 मि. टाइमफ्रेम) ====================
def get_support_resistance_15min(token):
  """15 मिनिटांच्या चार्टवरून सपोर्ट आणि रेजिस्टन्स लेव्हल शोधणे"""
  try:
    # ऐतिहासिक डेटा मिळवणे (उदा. निफ्टी)
    historicParam = {
        "exchange": "NSE",
        "symboltoken": token,
        "interval": "FIFTEEN_MINUTE",
        "fromdate": "2026-10-29 09:15",
        "todate": "2026-10-30 15:30",
    }
    # (टीप: प्रत्यक्षात लाईவ் डेटा फेच करताना वेळेची मर्यादा सांभाळावी लागेल)
    # इथे आपण उदाहरणासाठी लॉजिक पुट करत आहोत:
    support_level = 22800  # उदा. उदाहरणातील लेव्हल
    resistance_level = 23000
    return support_level, resistance_level
  except Exception as e:
    print(f"S&R Error: {e}")
    return None, None


# ==================== 4. ऑप्शन चेन आणि OI विश्लेषण ====================
def analyze_option_chain_oi(strike_price):
  """OI आणि Changing OI तपासून दिशा ठरवणे"""
  # एन्जेल वन किंवा इतर ऑप्शन चेन API द्वारे डेटा फेच करणे
  # इथे आपण लॉजिक सेट करत आहोत:
  put_oi_strong = True  # समजा Put OI जास्त आहे आणि पॉझिटिव्ह होत आहे
  call_oi_strong = False

  if put_oi_strong and not call_oi_strong:
    return "BULLISH"  # कॉल साईड ट्रेड
  elif call_oi_strong and not put_oi_strong:
    return "BEARISH"  # पुट साईड ट्रेड
  return "SIDEWAYS"


# ==================== 5. मुख्य अल्गो ट्रेडिंग लॉजिक (5 मि. कन्फर्मेशन + 3 ट्रेड लिमिट) ====================
def run_algo_trading():
  if not angel_one_login():
    return

  nifty_token = "999926000"  # निफ्टीचा टोकन नंबर (एन्जेल वन नुसार)
  trade_count = 0
  max_trades = 3  # दिवसातून जास्तीत जास्त 3 एन्ट्री

  send_telegram_alert(
      "🤖 *Bhavin Trading Bot* सुरू झाला आहे!\nमार्केट मॉनिटर करत आहे..."
  )

  while trade_count < max_trades:
    try:
      # 1. 15 मिनिटांची लेव्हल घेणे
      support, resistance = get_support_resistance_15min(nifty_token)
      current_spot_price = 22845  # लाईव्ह मार्केट प्राईस यहाँ घ्या (LTP)

      # 2. फेम आणि फेक एन्ट्री फिल्टर (सपोर्ट जवळ आल्यावर)
      if abs(current_spot_price - support) <= 15:
        print("मार्केट सपोर्ट लेव्हलजवळ पोहोचले आहे...")

        # 3. ऑप्शन चेन / OI अनालिसिस चेक करणे
        market_bias = analyze_option_chain_oi(support)

        # 4. 5 मिनिटांची कॅडल कन्फर्मेशन (सपोर्टला ग्रीन कॅडल आणि क्लोजिंग)
        # (इथे 5 मिनिटांच्या कॅडलचे क्लोजिंग आणि मागील कॅडलचा हाय ब्रेक होण्याचे लॉजिक लिहा)
        candle_confirmed = True  # कन्फर्मेशन मिळाले असे गृहीत धरू

        if market_bias == "BULLISH" and candle_confirmed:
          trade_count += 1
          entry_price = current_spot_price
          stop_loss = entry_price - 40  # सपोर्टच्या खाली एसएल
          target = entry_price + (
              (entry_price - stop_loss) * 2
          )  # 1:2 रिस्क रिवार्ड

          alert_msg = (
              f"🚀 *Bhavin Trading Bot - Trade Alert #{trade_count}*\n\n"
              f"🟢 **स्ट्रेटेजी:** CE (कॉल) खरेदी एन्ट्री\n"
              f"📍 **एन्ट्री प्राईस:** {entry_price}\n"
              f"🛑 **Stop Loss (SL):** {stop_loss}\n"
              f"🎯 **Target (1:2):** {target}\n"
              f"📊 **कारण:** २२८०० सपोर्टवर Put OI मजबूत व 5 मिनिटांचे"
              f" कॅडल कन्फर्मेशन मिळाले."
          )
          send_telegram_alert(alert_msg)
          print(alert_msg)

          # ट्रेड घेतल्यानंतर पुढच्या ट्रेडसाठी काही वेळ थांबावे
          time.sleep(900)  # 15 मिनिटे विश्रांती

        elif market_bias == "BEARISH":
          # याचप्रमाणे पुट साईड (PE) एन्ट्रीचे लॉजिक लिहिता येईल
          pass

      time.sleep(60)  # दर 1 मिनिटाने मार्केट तपासा

    except Exception as e:
      print(f"Error in main loop: {e}")
      time.sleep(30)

  send_telegram_alert(
      "🛑 आजचे ३ ट्रेड्स पूर्ण झाले आहेत. बॉट बंद होत आहे."
  )


if __name__ == "__main__":
  run_algo_trading()
  
