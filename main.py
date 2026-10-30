import time
import requests
from SmartApi import SmartConnect
import pandas as pd
import numpy as np
import pyotp

# ==================== 1. कॉन्फिगरेशन आणि तुमचे अचूक क्रेडेंशियल्स ====================
API_KEY = "ianEntxyV"
CLIENT_ID = "B253694"  # अपडेटेड Client ID
MPIN = "7172"
TOTP_KEY = "D4YNATHBAJVFIVOCYVUOPJNVIE"

# टेलिग्राम बॉटची माहिती (नवीन टोकनसह)
TELEGRAM_BOT_TOKEN = "8667131376:AAE_b_p7lhL0xuK_bkxYJOAPMUFR9CIBLX0"
TELEGRAM_CHAT_ID = "1486399523"

# ऑब्जेक्ट इनिशिलायझेशन
obj = SmartConnect(api_key=API_KEY)

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def angel_one_login():
    try:
        # लाईव्ह TOTP जनरेट करणे
        current_totp = pyotp.TOTP(TOTP_KEY).now()
        data = obj.generateSession(CLIENT_ID, MPIN, current_totp)
        if data and data.get("status"):
            print("एंजेल वन लॉगिन यशस्वी झाले!")
            return True
        else:
            error_msg = f"⚠️ *[LOGIN FAILED]* कारण: {data}"
            send_telegram_alert(error_msg)
            print("लॉगिन अयशस्वी:", data)
            return False
    except Exception as e:
        error_msg = f"⚠️ *[LOGIN EXCEPTION]* एरर: {e}"
        send_telegram_alert(error_msg)
        print(f"Login Exception: {e}")
        return False

def get_live_market_data(exchange, symbol_token):
    try:
        ltp_data = obj.ltpData(exchange, symbol_token, symbol_token)
        if ltp_data and ltp_data.get("status"):
            return ltp_data["data"]["ltp"]
    except Exception as e:
        print(f"LTP Fetch Error: {e}")
    return None

# ==================== 2. पेपर ट्रेडिंग ऑटोमॅटिक लॉजिक ====================
def run_paper_trading_bot():
    send_telegram_alert("🧪 *[TEST]* बॉट चालू होत आहे...")
    
    if not angel_one_login():
        send_telegram_alert("⚠️ *[SYSTEM ERROR]* एंजेल वन लॉगिन फेल झाले आहे!")
        return
    
    virtual_capital = 15000.0  # ₹१५,००० पेपर ट्रेडिंग कॅपिटल
    send_telegram_alert(f"🚀 *[PAPER TRADING ONLINE]* Bhavin Bot सक्रिय!\n💰 व्हर्च्युअल कॅपिटल: ₹{virtual_capital}")

    indices = {
        "NIFTY": {"exchange": "NSE", "token": "999926000", "support": 22800}
    }

    trade_count = 0
    max_trades = 3  # दिवसातून जास्तीत जास्त ३ ट्रेड

    while trade_count < max_trades:
        try:
            for index_name, data in indices.items():
                current_spot_price = get_live_market_data(data["exchange"], data["token"])
                if not current_spot_price:
                    continue

                support_level = data["support"]
                print(f"Monitoring {index_name} | LTP: {current_spot_price} | Support: {support_level}")

                # सपोर्ट लेव्हलजवळ आल्यावर ट्रेड घेणे
                if abs(current_spot_price - support_level) <= 20:
                    trade_count += 1
                    entry_time = time.strftime('%Y-%m-%d %H:%M:%S')
                    entry_price = current_spot_price
                    stop_loss = entry_price - 30
                    
                    # रिस्क-रिवार्ड रेशो (1:2 आणि 1:3 टार्गेट सेट करणे)
                    risk = entry_price - stop_loss
                    target_1_2 = entry_price + (risk * 2)  # 1:2 टार्गेट
                    target_1_3 = entry_price + (risk * 3)  # 1:3 टार्गेट
                    
                    target = target_1_2  # मुख्य टार्गेट 1:2 नुसार

                    # एन्ट्री मेसेज (वेळेसह)
                    entry_msg = (
                        f"🟢 *[PAPER TRADE ENTRY #{trade_count}]*\n"
                        f"──────────────────\n"
                        f"⏳ एन्ट्री वेळ: {entry_time}\n"
                        f"📊 इंडेक्स: {index_name}\n"
                        f"📍 एन्ट्री प्राईस: ₹{entry_price}\n"
                        f"🛑 स्टॉपलॉस: ₹{stop_loss}\n"
                        f"🎯 टार्गेट (1:2): ₹{target} | (1:3 साठी: ₹{target_1_3})\n"
                        f"💰 उपलब्ध कॅपिटल: ₹{virtual_capital}"
                    )
                    send_telegram_alert(entry_msg)

                    # ट्रेड लाईव्ह मॉनिटर करणे आणि एक्झिट वेळेची नोंद ठेवणे
                    position_active = True
                    while position_active:
                        time.sleep(10)
                        live_price = get_live_market_data(data["exchange"], data["token"])
                        if not live_price:
                            continue

                        exit_time = time.strftime('%Y-%m-%d %H:%M:%S')

                        # टार्गेट हिट झाल्यास
                        if live_price >= target:
                            profit = (target - entry_price) * 15  # १ लॉट (१५ क्वांटिटी)
                            virtual_capital += profit
                            exit_msg = (
                                f"🎯 *[TARGET HIT #{trade_count}]*\n"
                                f"──────────────────\n"
                                f"⏳ एक्झिट वेळ: {exit_time}\n"
                                f"✅ नफा: +₹{profit}\n"
                                f"💰 एकूण कॅपिटल: ₹{virtual_capital}\n"
                                f"🏁 पोझिशन यशस्वीरित्या क्लोज झाली."
                            )
                            send_telegram_alert(exit_msg)
                            position_active = False

                        # स्टॉपलॉस हिट झाल्यास
                        elif live_price <= stop_loss:
                            loss = (entry_price - stop_loss) * 15
                            virtual_capital -= loss
                            exit_msg = (
                                f"🛑 *[STOPLOSS HIT #{trade_count}]*\n"
                                f"──────────────────\n"
                                f"⏳ एक्झिट वेळ: {exit_time}\n"
                                f"❌ नुकसान: -₹{loss}\n"
                                f"💰 एकूण कॅपिटल: ₹{virtual_capital}\n"
                                f"🏁 पोझिशन क्लोज झाली."
                            )
                            send_telegram_alert(exit_msg)
                            position_active = False

                    time.sleep(300) # ट्रेडनंतर ५ मिनिटे विश्रांती

            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(30)

    send_telegram_alert(f"🛑 *[TRADING FINISHED]* आजचे ३ ट्रेड्स पूर्ण झाले. अंतिम कॅपिटल: ₹{virtual_capital}")

if __name__ == "__main__":
    run_paper_trading_bot()
    
