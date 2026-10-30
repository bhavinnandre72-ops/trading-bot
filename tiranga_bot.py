import requests
import pandas as pd
import yfinance as yf
from stocks_200 import stocks_list

# टेलिग्राम बॉटची माहिती
TOKEN = "8731401312:AAEQwWyzIDfGXUQeT3f0ZrKkkabi98xOvrQ"
CHAT_ID = "1486399523"  # तुमचा खरा चॅट आयडी इथे टाकला आहे

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
    print("Daily Tiranga Strategy स्कॅनिंग सुरू आहे...")
    
    # 🔴 टेस्टिंगसाठी आधीच एक मेसेज पाठवत आहे (बॉट ॲक्टिव्ह आहे का हे तपासण्यासाठी)
    send_telegram_alert("🤖 *Tiranga Bot Test:* बॉट यशस्वीरित्या कनेक्ट झाला आहे आणि काम करत आहे!")
    
    alert_count = 0

    for stock in stocks_list:
        try:
            # Yahoo Finance वरून डेली (1D) डेटा घेणे (NSE साठी .NS जोडले आहे)
            ticker = stock + ".NS"
            df = yf.download(ticker, period="60d", interval="1d", progress=False)

            if df.empty or len(df) < 30:
                continue

            # मल्टिइंडेक्स कॉलम काढणे
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # EMA कॅल्क्युलेशन (Daily Close नुसार)
            # EMA 5 (सफेद), EMA 13 (पांढरा), EMA 26 (हिरवा)
            df['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
            df['EMA_13'] = df['Close'].ewm(span=13, adjust=False).mean()
            df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()

            # मागील आणि आजची कॅंडल तपासणे
            prev = df.iloc[-2]
            curr = df.iloc[-1]

            # तिरंगा पॅटर्न क्रॉसओव्हर कन्डिशन:
            # जेव्हा EMA 5 हा EMA 13 ला वरच्या बाजूने क्रॉस करतो आणि EMA 13 हा EMA 26 च्या वर असतो
            is_crossover = (prev['EMA_5'] <= prev['EMA_13']) and (curr['EMA_5'] > curr['EMA_13'])
            is_uptrend_aligned = curr['EMA_13'] > curr['EMA_26']

            if is_crossover and is_uptrend_aligned:
                candle_low = curr['Low']  # स्टॉप लॉससाठी डेली कॅंडलचा लो
                close_price = curr['Close']

                                msg = (
                    f"🟢 *Daily Tiranga Strategy Alert* 🚀\n\n"
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

    print(f"स्कॅनिंग पूर्ण झाले. एकूण अलर्ट पाठवले: {alert_count}")

if __name__ == "__main__":
    scan_tiranga_strategy()
    
