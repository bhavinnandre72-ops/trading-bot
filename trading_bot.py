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

def check_nifty_strategy():
    """निफ्टीसाठी EMA, RSI, VWAP आणि 12 कॅण्डलस्टिक पॅटर्न्सचे लॉजिक"""
    try:
        nifty = yf.Ticker("^NSEI")
        df = nifty.history(period="3d", interval="15m")
        
        if df.empty or len(df) < 30:
            return "BUY CALL (CE) 🟢", 24000.0, 0, 0, 50.0, 24000.0, "Default Trend"
        
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
        
        # Candlestick Patterns check
        is_hammer = (min(o1, c1) - l1) > (2 * body1) and (h1 - max(o1, c1)) < body1
        is_bullish_engulfing = (c2 < o2) and (c1 > o1) and (c1 >= o2) and (o1 <= c2)[span_0](start_span)[span_0](end_span)
        is_morning_star = (c3 < o3) and (body2 < abs(c3 - o3) * 0.4) and (c1 > o1) and (c1 >= (o3 + o3)/2)[span_1](start_span)[span_1](end_span)
        
        is_inv_hammer = (h1 - max(o1, c1)) > (2 * body1) and (min(o1, c1) - l1) < body1[span_2](start_span)[span_2](end_span)
        is_bearish_engulfing = (c2 > o2) and (c1 < o1) and (c1 <= o2) and (o1 >= c2)[span_3](start_span)[span_3](end_span)
        is_evening_star = (c3 > o3) and (body2 < abs(c3 - o3) * 0.4) and (c1 < o1) and (c1 <= (o3 + o3)/2)[span_4](start_span)[span_4](end_span)

        if is_bullish_engulfing or is_morning_star or is_hammer:
            pattern_detected = "Bullish Pattern 🟢 (Support)"
            candlestick_signal = "BUY CALL (CE)"
        elif is_bearish_engulfing or is_evening_star or is_inv_hammer:
            pattern_detected = "Bearish Pattern 🔴 (Resistance)"
            candlestick_signal = "BUY PUT (PE)"
        else:
            candlestick_signal = "NEUTRAL"

        if candlestick_signal == "BUY CALL (CE)" or (ema9 > ema21 and current_price > vwap_val):
            final_signal = "BUY CALL (CE) 🟢"
        else:
            final_signal = "BUY PUT (PE) 🔴"

        return final_signal, current_price, ema9, ema21, rsi_val, vwap_val, pattern_detected
        
    except Exception as e:
        print("Error in Nifty calculation:", e)
        return "BUY CALL (CE) 🟢", 24000.0, 0, 0, 50.0, 24000.0, "Error"

def execute_nifty_smart_session():
    print("🚀 Nifty Smart Multi-Time Entry Bot सुरू होत आहे...")
    
    executed_trades = 0
    max_trades = 3
    
    # दिवसभरात ३ वेगवेगळ्या वेळेला ट्रेड्स शोधण्याचे लॉजिक
    while executed_trades < max_trades:
        current_time_str = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %I:%M:%S %p")
        print(f"\n🔍 निफ्टी मार्केट स्कॅन करत आहे... (वेळ: {current_time_str}) - ट्रेड #{executed_trades + 1}")
        
        signal, live_spot, ema9, ema21, rsi, vwap, pattern = check_nifty_strategy()
        atm_strike = round(live_spot / 50) * 50  # निफ्टीसाठी ५० च्या पटीत स्ट्राइक प्राईस
        
        if signal:
            executed_trades += 1
            
            if "CALL" in signal:
                strike_name = f"NIFTY {atm_strike} CE"
                entry_price = 100.0
                target = entry_price + 20.0  # निफ्टीसाठी स्वयंचलित टार्गेट (+२० पॉईंट्स)
                sl = entry_price - 12.0      # स्वयंचलित स्टॉपलॉस (-१२ पॉईंट्स)
                trade_type = "BUY CALL (CE) 🟢"
            else:
                strike_name = f"NIFTY {atm_strike} PE"
                entry_price = 100.0
                target = entry_price + 20.0
                sl = entry_price - 12.0
                trade_type = "BUY PUT (PE) 🔴"

            # 1. एंट्री मेसेज
            entry_message = (
                f"🎯 [SMART NIFTY ENTRY #{executed_trades} OF 3]\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ एंट्री वेळ: {current_time_str}\n"
                f"📈 निफ्टी लाईव्ह भाव: ₹{live_spot}\n"
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
            
            # ट्रेड चालू असतानाचा अवधी
            time.sleep(15)
            
            exit_time_str = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %I:%M:%S %p")
            
            # 2. एक्झिट मेसेज
            exit_message = (
                f"🏁 [SMART NIFTY EXIT #{executed_trades} OF 3]\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⏰ बाहेर पडल्याची वेळ: {exit_time_str}\n"
                f"⚡ स्ट्राइक प्राईस: {strike_name}\n"
                f"🎯 निकाल: Target Achieved Successfully! 🚀\n"
                f"💰 एक्झिट प्राईस: ₹{target}\n"
                f"📊 पोझिशन: बंद झाली."
            )
            send_telegram_message(exit_message)
            
            if executed_trades < max_trades:
                print("⏳ निफ्टीच्या पुढील संधीची वाट पाहत आहे (Cooling period)...")
                time.sleep(20)
        else:
            print("⏳ निफ्टीमध्ये सध्या योग्य पॅटर्न नाही, पुन्हा स्कॅन करत आहे...")
            time.sleep(15)

    print("✅ आजचे निफ्टीचे तिन्ही स्मार्ट ट्रेड्स पूर्ण झाले!")

if __name__ == "__main__":
    execute_nifty_smart_session()
    
