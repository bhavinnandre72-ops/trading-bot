import requests
import pandas as pd
import yfinance as yf
from stocks_200 import stocks_list

# टेलिग्राम बॉटची माहिती
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

def scan_tiranga_strategy():
    print("लाईव्ह मार्केट स्कَनिंग सुरू आहे...")
    
    # बॉट चालू असल्याचा लाईव्ह टेस्ट मेसेज
    send_telegram_alert("🚀 *Tiranga Live Scanner:* बॉट लाईव्ह मार्केट स्कॅनिंगसाठी सुरू झाला आहे!")
    
    alert_count = 0
    matched_stocks = []

    for stock in stocks_list:
        try:
            ticker = stock + ".NS"
            df = yf.download(ticker, period="60d", interval="1d", progress=False)

            if df.empty or len(df) < 30:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # EMA कॅल्क्युलेशन (तिरंगा रंगसंगतीसह)
            df['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
            df['EMA_13'] = df['Close'].ewm(span=13, adjust=False).mean()
            df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()

            prev = df.iloc[-2]
            curr = df.iloc[-1]

            # तिरंगा पॅटर्न कन्डिशन (EMA 5 > EMA 13 > EMA 26)
            is_crossover = (prev['EMA_5'] <= prev['EMA_13']) and (curr['EMA_5'] > curr['EMA_13'])
            is_uptrend_aligned = curr['EMA_13'] > curr['EMA_26']

            if is_crossover and is_uptrend_aligned:
                candle_low = curr['Low']
                close_price = curr['Close']
                matched_stocks.append(stock)

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

    # समजा लाईव्ह स्कॅनिंगमध्ये पॅटर्न मॅच झाला नाही, तर त्याचीही माहिती देणारा मेसेज
    if alert_count == 0:
        send_telegram_alert("ℹ️ *Live Scan Update:* आजच्या स्कॅनिंगमध्ये कोणत्याही नवीन स्टॉकवर तिरंगा पॅटर्न मॅच झालेला नाही.")
    
    print(f"स्कॅनिंग पूर्ण झाले. एकूण अलर्ट पाठवले: {alert_count}")

if __name__ == "__main__":
    scan_tiranga_strategy()
    
