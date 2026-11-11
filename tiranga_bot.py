import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
from stocks_200 import stocks_list

# Telegram Bot Credentials
TOKEN = "8731401312:AAEQwWyzIDfGXUQeT3f0ZrKkkabi98xOvrQ"
CHAT_ID = "1486399523"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

def main():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    current_hour = now_ist.hour
    current_minute = now_ist.minute

    print(f"Current IST Time: {now_ist.strftime('%H:%M:%S')}")

    # १. सकाळी 9 ते 10 च्या दरम्यान असल्यास फक्त ॲक्टिव्ह मेसेज पाठवणे
    if current_hour == 9 or (current_hour == 10 and current_minute < 30):
        send_telegram_alert("🚀 *Tiranga Live Scanner:* मार्केट सुरू झाले आहे, बॉट मॉर्निंग मॉनिटरिंगसाठी ॲक्टिव्ह झाला आहे!")
        print("Morning active message sent.")
        return

    # २. दुपारी 3 वाजता (किंवा 3:00 ते 4:00 दरम्यान) असल्यास थेट २०० स्टॉक्सचे लाईव्ह स्कॅनिंग करणे
    print("दुपारचे लाईव्ह तिरंगा स्कॅनिंग सुरू होत आहे...")
    
    alert_count = 0
    for stock in stocks_list:
        try:
            ticker = stock + ".NS"
            df = yf.download(ticker, period="60d", interval="1d", progress=False)

            if df.empty or len(df) < 30:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # EMA Calculation
            df['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
            df['EMA_13'] = df['Close'].ewm(span=13, adjust=False).mean()
            df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()

            prev = df.iloc[-2]
            curr = df.iloc[-1]

            # Tiranga Pattern Crossover (EMA 5 > EMA 13 > EMA 26)
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
    
    print(f"स्कॅनिंग पूर्ण झाले. एकूण ॲलर्ट्स: {alert_count}")

if __name__ == "__main__":
    main()
                
