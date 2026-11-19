import time
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
from stocks_200 import stocks_list

TOKEN = "8731401312:AAEQwWyzIDfGXUQeT3f0ZrKkkabi98xOvrQ"
CHAT_ID = "1486399523"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Telegram Error: {e}")

def scan_tiranga_strategy():
    print("३:०० वाजताचे तिरंगा स्कॅनिंग सुरू झाले...")
    alert_count = 0

    for stock in stocks_list:
        try:
            ticker = stock + ".NS"
            df = yf.download(ticker, period="60d", interval="1d", progress=False)

            if df.empty or len(df) < 30:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
            df['EMA_13'] = df['Close'].ewm(span=13, adjust=False).mean()
            df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()

            prev = df.iloc[-2]
            curr = df.iloc[-1]

            is_crossover = (prev['EMA_5'] <= prev['EMA_13']) and (curr['EMA_5'] > curr['EMA_13'])
            is_uptrend_aligned = curr['EMA_13'] > curr['EMA_26']

            if is_crossover and is_uptrend_aligned:
                candle_low = curr['Low']
                close_price = curr['Close']

                msg = (
                    f"🟢 *Live Tiranga Strategy Alert* 🚀\n\n"
                    f"📈 *Stock:* `{stock}`\n"
                    f"⏰ *Timeframe:* Daily (1D)\n"
                    f"🧡🤍💚 *Pattern:* Bullish Crossover\n"
                    f"*(EMA 5 🧡 > EMA 13 🤍 > EMA 26 💚)*\n"
                    f"💰 *Close Price:* `{close_price:.2f}`\n"
                    f"🛑 *Stop Loss (Low):* `{candle_low:.2f}`"
                )
                send_telegram_alert(msg)
                alert_count += 1

        except Exception as e:
            print(f"Error processing {stock}: {e}")

    if alert_count == 0:
        send_telegram_alert("ℹ️ *Market Scan Update:* आज दुपारी ३ वाजताच्या स्कॅनिंगमध्ये कोणत्याही स्टॉकवर तिरंगा पॅटर्न मॅच झालेला नाही.")

    print(f"स्कॅनिंग पूर्ण झाले. एकूण अलर्ट्स: {alert_count}")

def run_bot_loop():
    ist = pytz.timezone('Asia/Kolkata')
    morning_sent_date = None
    afternoon_sent_date = None

    send_telegram_alert("🤖 *Tiranga Bot Started:* बॉट मॉनिटरिंगसाठी सुरू झाला आहे.")

    while True:
        now = datetime.now(ist)
        today_str = now.strftime("%Y-%m-%d")
        weekday = now.weekday()  # 0 = Monday ... 4 = Friday

        # फक्त सोमवार ते शुक्रवार
        if weekday < 5:
            # सकाळी 9:30 AM ला ॲक्टिव्ह मेसेज
            if now.hour == 9 and now.minute == 30 and morning_sent_date != today_str:
                send_telegram_alert("🚀 *Tiranga Live Scanner:* मार्केट सुरू झाले आहे, बॉट ॲक्टिव्ह आहे!")
                morning_sent_date = today_str

            # दुपारी 3:00 PM ला तिरंगा स्कॅनिंग आणि अलर्ट
            if now.hour == 15 and now.minute == 0 and afternoon_sent_date != today_str:
                scan_tiranga_strategy()
                afternoon_sent_date = today_str

        time.sleep(20)  # दर २० सेकंदांनी वेळ तपासेल

if __name__ == "__main__":
    run_bot_loop()
    
