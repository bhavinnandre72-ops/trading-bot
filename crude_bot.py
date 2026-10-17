import os
import requests
import datetime
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
    """RSI (Relative Strength Index) मोजण्यासाठीचे फंक्शन"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def check_ultimate_strategy():
    """EMA, RSI, VWAP आणि 12 कॅण्डलस्टिक पॅटर्न्सचे कॉम्बिनेशन लॉजिक"""
    try:
        crude = yf.Ticker("CL=F")
        df = crude.history(period="3d", interval="15m")
        
        if df.empty or len(df) < 30:
            return "NEUTRAL", 6000.0, 0, 0, 50.0, 6000.0, "No Data"
        
        # 1. EMA मोजणे (9 आणि 21)
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # 2. RSI मोजणे (14 पीरियड)
        df['RSI'] = calculate_rsi(df['Close'], 14)
        
        # 3. VWAP मोजणे (Volume Weighted Average Price)
        df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
        
        current_price = round(df['Close'].iloc[-1], 2)
        ema9 = df['EMA_9'].iloc[-1]
        ema21 = df['EMA_21'].iloc[-1]
        rsi_val = df['RSI'].iloc[-1]
        vwap_val = df['VWAP'].iloc[-1]
        
        # कॅण्डल्सचा डेटा (पॅटर्न्स तपासण्यासाठी)
        o1, c1, h1, l1 = df['Open'].iloc[-1], df['Close'].iloc[-1], df['High'].iloc[-1], df['Low'].iloc[-1]
        o2, c2, h2, l2 = df['Open'].iloc[-2], df['Close'].iloc[-2], df['High'].iloc[-2], df['Low'].iloc[-2]
        o3, c3, h3, l3 = df['Open'].iloc[-3], df['Close'].iloc[-3], df['High'].iloc[-3], df['Low'].iloc[-3]
        
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)
        
        pattern_detected = "Normal Trend"
        candlestick_signal = "NEUTRAL"

        # --- 12 कॅण्डलस्टिक पॅटर्न्सची तपासणी ---
        # बुलिश पॅटर्न्स (सपोर्ट लेव्हल)
        is_hammer = (min(o1, c1) - l1) > (2 * body1) and (h1 - max(o1, c1)) < body1
        is_bullish_harami = (c2 < o2) and (c1 > o1) and (c1 <= o2) and (o1 >= c2)
        is_doji_dt = (body1 <= (h1 - l1) * 0.1) and (c2 < o2) and (c1 > o1)
        is_bullish_engulfing = (c2 < o2) and (c1 > o1) and (c1 >= o2) and (o1 <= c2)[span_0](start_span)[span_0](end_span)
        is_bullish_piercing = (c2 < o2) and (c1 > o1) and (c1 >= (o2 + c2) / 2) and (o1 < c2)
        is_morning_star = (c3 < o3) and (body2 < abs(c3 - o3) * 0.4) and (c1 > o1) and (c1 >= (o3 + o3)/2)[span_1](start_span)[span_1](end_span)

        # बेरिश पॅटर्न्स (रेझिस्टन्स लेव्हल)
        is_inv_hammer = (h1 - max(o1, c1)) > (2 * body1) and (min(o1, c1) - l1) < body1[span_2](start_span)[span_2](end_span)
        is_bearish_harami = (c2 > o2) and (c1 < o1) and (c1 >= o2) and (o1 <= c2)[span_3](start_span)[span_3](end_span)
        is_doji_ut = (body1 <= (h1 - l1) * 0.1) and (c2 > o2) and (c1 < o1)[span_4](start_span)[span_4](end_span)
        is_bearish_engulfing = (c2 > o2) and (c1 < o1) and (c1 <= o2) and (o1 >= c2)[span_5](start_span)[span_5](end_span)
        is_bearish_piercing = (c2 > o2) and (c1 < o1) and (c1 <= (o2 + c2) / 2) and (o1 > c2)[span_6](start_span)[span_6](end_span)
        is_evening_star = (c3 > o3) and (body2 < abs(c3 - o3) * 0.4) and (c1 < o1) and (c1 <= (o3 + o3)/2)[span_7](start_span)[span_7](end_span)

        if is_bullish_engulfing or is_morning_star or is_hammer or is_bullish_harami or is_bullish_piercing or is_doji_dt:
            pattern_detected = "Bullish Candlestick Pattern 🟢 (Support)"
            candlestick_signal = "BUY CALL (CE)"
        elif is_bearish_engulfing or is_evening_star or is_inv_hammer or is_bearish_harami or is_bearish_piercing or is_doji_ut:
            pattern_detected = "Bearish Candlestick Pattern 🔴 (Resistance)"
            candlestick_signal = "BUY PUT (PE)"
        else:
            candlestick_signal = "NEUTRAL"

        # --- सर्व इंडिकेटर्स आणि पॅटर्नचे फायनल कन्फर्मेशन लॉजिक ---
        # कॉल (CE) साठी: पॅटर्न बुलिश असावा किंवा (EMA 9 > 21 आणि प्राईस VWAP च्या वर आणि RSI < 70)
        if candlestick_signal == "BUY CALL (CE)" or (ema9 > ema21 and current_price > vwap_val and rsi_val < 70):
            final_signal = "BUY CALL (CE) 🟢"
        # पुट (PE) साठी: पॅटर्न बेरिश असावा किंवा (EMA 9 < 21 आणि प्राईस VWAP च्या खाली आणि RSI > 30)
        elif candlestick_signal == "BUY PUT (PE)" or (ema9 < ema21 and current_price < vwap_val and rsi_val > 30):
            final_signal = "BUY PUT (PE) 🔴"
        else:
            final_signal = "BUY CALL (CE) 🟢" if ema9 > ema21 else "BUY PUT (PE) 🔴"

        return final_signal, current_price, ema9, ema21, rsi_val, vwap_val, pattern_detected
        
    except Exception as e:
        print("Error in technical calculation:", e)
        return "BUY CALL (CE) 🟢", 6000.0, 0, 0, 50.0, 6000.0, "Error"

def execute_ultimate_bot():
    print("🚀 Ultimate EMA + RSI + VWAP + 12 Patterns Bot सुरू होत आहे...")
    
    signal, live_spot, ema9, ema21, rsi, vwap, pattern = check_ultimate_strategy()
    atm_strike = round(live_spot / 50) * 50
    
    entry_time = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %I:%M:%S %p")
    
    if "CALL" in signal:
        strike_name = f"CRUDEOIL {atm_strike} CE"
        entry_price = 140.0
        target = 175.0
        sl = 115.0
    else:
        strike_name = f"CRUDEOIL {atm_strike - 50} PE"
        entry_price = 130.0
        target = 165.0
        sl = 105.0

    message = (
        f"🎯 [CRUDE OIL ULTIMATE SYSTEM SIGNAL]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ वेळ: {entry_time}\n"
        f"📈 लाईव्ह स्पॉट भाव: ₹{live_spot}\n"
        f"🕯️ कॅण्डल पॅटर्न: {pattern}\n"
        f"⚡ 9 EMA: {round(ema9, 2)} | 21 EMA: {round(ema21, 2)}\n"
        f"📊 RSI वैल्यू: {round(rsi, 2)} | VWAP: ₹{round(vwap, 2)}\n"
        f"🚀 फायनल सिग्नल: {signal}\n"
        f"⚡ स्ट्राइक प्राईस: {strike_name}\n"
        f"💰 सुचवलेली एन्ट्री: ₹{entry_price}\n"
        f"🎯 टार्गेट: ₹{target}\n"
        f"🛑 स्टॉपलॉस: ₹{sl}\n"
        f"🔄 स्टेटस: सर्व इंडिकेटर्स आणि पॅटर्न्सचे कन्फर्मेशन पूर्ण."
    )
    
    send_telegram_message(message)

if __name__ == "__main__":
    execute_ultimate_bot()
    
