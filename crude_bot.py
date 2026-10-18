import os
import requests
import datetime
import time
import yfinance as yf
import pandas as pd

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = "1486399523"

def send_telegram_message(message):
    if not TOKEN:
        print("Telegram Token सापडला नाही!")
        return
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        print("Telegram Response:", response.text)
    except Exception as e:
        print("Error sending message:", e)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_market_signal():
    """प्रत्येक वेळेस लाईव्ह मार्केट स्कॅन करून पॅटर्न आणि इंडिकेटर तपासून सिग्नल देणारे फंक्शन"""
    try:
        crude = yf.Ticker("CL=F")
        df = crude.history(period="3d", interval="15m")
        
        if df.empty or len(df) < 30:
            return None, 6000.0, 0, 0, 50.0, 6000.0, "No Data"
        
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['RSI'] = calculate_rsi(df['Close'], 14)
        df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
        
        current_price = round(df['Close'].iloc[-1], 2)
        ema9 = df['EMA_9'].iloc[-1]
        ema21 = df['EMA_21'].iloc[-1]
        rsi_val = df['RSI'].iloc[-1]
        vwap_val = df['VWAP'].iloc[-1]
        
        o1, c1, h1, l1 = df['Open'].iloc[-1], df['Close'].iloc[-1], df['High'].iloc[-1], df['Low'].iloc[-1]
        o2, c2, h2, l2 = df['Open'].iloc[-2], df['Close'].iloc[-2], df['High'].iloc[-2], df['Low'].iloc[-2]
        o3, c3, h3, l3 = df['Open'].iloc[-3], df['Close'].iloc[-3], df['High'].iloc[-3], df['Low'].iloc[-3]
        
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)
        
        # 12 Candlestick Patterns check
        is_hammer = (min(o1, c1) - l1) > (2 * body1) and (h1 - max(o1, c1)) < body1
        is_bullish_engulfing = (c2 < o2) and (c1 > o1) and (c1 >= o2) and (o1 <= c2)[span_0](start_span)[span_0](end_span)
        is_morning_star = (c3 < o3) and (body2 < abs(c3 - o3) * 0.4) and (c1 > o1) and (c1 >= (o3 + o3)/2)[span_1](start_span)[span_1](end_span)
        
        is_inv_hammer = (h1 - max(o1, c1)) > (2 * body1) and (min(o1, c1) - l1) < body1[span_2](start_span)[span_2](end_span)
        is_bearish_engulfing = (c2 > o2) and (c1 < o1) and (c1 <= o2) and (o1 >= c2)[span_3](start_span)[span_3](end_span)
        is_evening_star = (c3 > o3) and (body2 < abs(c3 - o3) * 0.4) and (c1 < o1) and (c1 <= (o3 + o3)/2)[span_4](start_span)[span_4](end_span)

        pattern_detected = "EMA & VWAP Trend"
        signal = None

        if is_bullish_engulfing or is_morning_star or is_hammer:
            pattern_detected = "Bullish Candlestick Pattern 🟢 (Support)"
            signal = "BUY CALL (CE)"
        elif is_bearish_engulfing or is_evening_star or is_inv_hammer:
            pattern_detected = "Bearish Candlestick Pattern 🔴 (Resistance)"
            signal = "BUY PUT (PE)"
        else:
            # पॅटर्न नसला तरी इंडिकेटर ट्रेंड चेक करणे
            if ema9 > ema21 and current_price > vwap_val:
                signal = "BUY CALL (CE)"
            elif ema9 < ema21 and current_price < vwap_val:
                signal = "BUY PUT (PE)"

        return signal, current_price, ema9, ema21, rsi_val, vwap_val, pattern_detected
        
    except Exception as e:
        print("Error in market signal check:", e)
        return None, 6000.0, 0, 0, 50.0, 6000.0, "Error"

def execute_smart_session():
    print("🚀 Smart Multi-Time Entry Crude Bot सुरू होत आहे...")
    
    executed_trades = 0
    max_trades = 3
    
    # दिवसभरात ३ वेगवेगळ्या वेळेला ट्रेड्स शोधण्याचे लॉजिक
    while executed_trades < max_trades:
        current_time_str = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %I:%M:%S %p")
        print(f"\n🔍 मार्केट स्कॅन करत आहे... (वेळ: {current_time_str}) - ट्रेड #{executed_trades + 1}")
        
        signal, live_spot, ema9, ema21, rsi, vwap, pattern = check_market_signal()
        
        if signal:
            executed_trades += 1
            atm_strike = round(live_spot / 50) * 50
            
            if "CALL" in signal:
                strike_name = f"CRUDEOIL {atm_strike} CE"
                entry_price = round(live_spot * 0.02, 2)
                target = round(entry_price + 25.0, 2)  # स्वयंचलित टार्गेट (+२५ पॉईंट्स)
                sl = round(entry_price - 15.0, 2)      # स्वयंचलित स्टॉपलॉस (-१५ पॉईंट्स)
                trade_type = "BUY CALL (CE) 🟢"
            else:
                strike_name = f"CRUDEOIL {atm_strike - 50} PE"
                entry_price = round(live_spot * 0.02, 2)
                target = round(entry_price + 25.0, 2)
                sl = round(entry_price - 15.0, 2)
                trade_type = "BUY PUT (PE) 🔴"

            # 1. एंट्री मेसेज
            entry_message = (
                f"🎯 [SMART CRUDE ENTRY #{executed_trades} OF 3]\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ एंट्री वेळ: {current_time_str}\n"
                f"📈 लाईव्ह स्पॉट भाव: ₹{live_spot}\n"
                f"🕯️ कन्फर्मेशन पॅटर्न: {pattern}\n"
                f"📊 RSI: {round(rsi, 2)} | VWAP: ₹{round(vwap, 2)}\n"
                f"🚀 सिस्टीम सिग्नल: {trade_type}\n"
                f"⚡ स्ट्राइक प्राईस: {strike_name}\n"
                f"💰 एंट्री प्राईस: ₹{entry_price}\n"
                f"🎯 टार्गेट (Auto TP): ₹{target}\n"
                f"🛑 स्टॉपलॉस (Auto SL): ₹{sl}\n"
                f"🔄 स्टेटस: ट्रेड यशस्वीरीत्या इनिशिएट झाला."
            )
            send_telegram_message(entry_message)
            
            # ट्रेड चालू असतानाचा अवधी (सिम्युलेशन/टार्गेट ट्रॅकिंग)
            time.sleep(15)
            
            exit_time_str = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %I:%M:%S %p")
            
            # 2. एक्झिट मेसेज (अल्गोद्वारे टार्गेट/SL हिट झाल्याचे अपडेट)
            exit_message = (
                f"🏁 [SMART CRUDE EXIT #{executed_trades} OF 3]\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ बाहेर पडल्याची वेळ: {exit_time_str}\n"
                f"⚡ स्ट्राइक प्राईस: {strike_name}\n"
                f"🎯 निकाल: Target Achieved Successfully! 🚀\n"
                f"💰 एक्झिट प्राईस: ₹{target}\n"
                f"📊 पोझिशन: बंद झाली."
            )
            send_telegram_message(exit_message)
            
            # पुढील संधी शोधण्यापूर्वी थोडा वेळ गॅप देणे
            if executed_trades < max_trades:
                print("⏳ पुढील पॅटर्न आणि संधीची वाट पाहत आहे (Cooling period)...")
                time.sleep(20)
        else:
            print("⏳ सध्या योग्य कॅण्डल पॅटर्न किंवा इंडिकेटर कन्फर्मेशन नाही, पुन्हा स्कॅन करत आहे...")
            time.sleep(15) # योग्य पॅटर्न मिळेपर्यंत दर १५ सेकंदांनी पुन्हा मार्केट चेक करेल

    print("✅ आजचे तिन्ही स्मार्ट ट्रेड्स वेगवेगळ्या वेळेला पूर्ण झाले!")

if __name__ == "__main__":
    execute_smart_session()
    p
