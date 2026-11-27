import time
from datetime import datetime, timedelta
import requests
import pandas as pd
import pyotp
from SmartApi import SmartConnect

# --- Angel One API आणि Telegram बॉटची माहिती ---
API_KEY = "iemEXsyV"
CLIENT_ID = "B253694"
MPIN = "7172"
TOTP_KEY = "D4YNATHBA3VFIW5C7YUQPJNVIE"

# टेलिग्राम बॉटची माहिती
TELEGRAM_BOT_TOKEN = "9128543562:AAG9vfmFC9K2eqZtJ51XCeMaGi6A68GmWpk"
TELEGRAM_CHAT_ID = "1486399523"

# मॉनिटर करायचे सिम्बॉल्स (इथे तुम्हाला हवे असलेले Stocks/Index चे Symbol Token जोडा; ETF टाळा)
WATCHLIST = [
    {"name": "NIFTY 50", "exchange": "NSE", "symboltoken": "99926000"},
    # {"name": "RELIANCE", "exchange": "NSE", "symboltoken": "2885"},
]


def send_telegram_alert(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        print("[OK] Telegram अलर्ट पाठवला गेला.")
    except Exception as e:
        print(f"[ERROR] Telegram मेसेज पाठवताना अडचण: {e}")


def connect_angel_one() -> SmartConnect:
    smart_api = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_KEY).now()
    data = smart_api.generateSession(CLIENT_ID, MPIN, totp)
    if not data.get("status"):
        raise RuntimeError(f"Angel One Login अयशस्वी: {data}")
    print("[OK] Angel One शी यशस्वी कनेक्ट झाले.")
    return smart_api


def fetch_5m_candles(smart_api: SmartConnect, exchange: str, token: str, days_back: int = 3) -> pd.DataFrame:
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days_back)

    params = {
        "exchange": exchange,
        "symboltoken": token,
        "interval": "FIVE_MINUTE",
        "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
        "todate": to_date.strftime("%Y-%m-%d %H:%M"),
    }
    res = smart_api.getCandleData(params)
    candles = res.get("data") or []
    if not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["ema10"] = df["close"].ewm(span=10, adjust=False).mean()
    return df.dropna().reset_index(drop=True)


def is_green_non_doji(row: pd.Series) -> bool:
    body = row["close"] - row["open"]
    rng = max(row["high"] - row["low"], 1e-9)
    return body > 0 and (body / rng) >= 0.15


def is_red_non_doji(row: pd.Series) -> bool:
    body = row["open"] - row["close"]
    rng = max(row["high"] - row["low"], 1e-9)
    return body > 0 and (body / rng) >= 0.15


def detect_setups_for_date(df: pd.DataFrame, target_date: datetime.date) -> list[dict]:
    signals = []
    if len(df) < 15:
        return signals

    for i in range(4, len(df)):
        row_curr = df.iloc[i]
        if row_curr["timestamp"].date() != target_date:
            continue

        # --- BUY SETUP: 3 White Soldiers + 1 Red Candle (Close > 10 EMA) + High Break ---
        s1, s2, s3 = df.iloc[i - 4], df.iloc[i - 3], df.iloc[i - 2]
        pb_red = df.iloc[i - 1]

        three_white_soldiers = (
            is_green_non_doji(s1)
            and is_green_non_doji(s2)
            and is_green_non_doji(s3)
            and (s2["close"] > s1["close"])
            and (s3["close"] > s2["close"])
        )
        red_pullback_above_ema = (
            is_red_non_doji(pb_red)
            and (pb_red["close"] > pb_red["ema10"])
        )
        buy_breakout = row_curr["high"] >= pb_red["high"]

        if three_white_soldiers and red_pullback_above_ema and buy_breakout:
            entry_price = round(float(pb_red["high"]), 2)
            sl_price = round(float(row_curr["ema10"]), 2)
            risk = max(entry_price - sl_price, 0.05)
            signals.append({
                "time": row_curr["timestamp"].strftime("%Y-%m-%d %H:%M"),
                "side": "BUY",
                "trigger_high_low": entry_price,
                "sl": sl_price,
                "t_1_1": round(entry_price + risk, 2),
                "t_1_2": round(entry_price + 2 * risk, 2),
                "t_1_3": round(entry_price + 3 * risk, 2),
            })

        # --- SELL SETUP: 3 Black Soldiers + 1 Green Candle (Close < 10 EMA) + Low Break ---
        b1, b2, b3 = df.iloc[i - 4], df.iloc[i - 3], df.iloc[i - 2]
        pb_green = df.iloc[i - 1]

        three_black_soldiers = (
            is_red_non_doji(b1)
            and is_red_non_doji(b2)
            and is_red_non_doji(b3)
            and (b2["close"] < b1["close"])
            and (b3["close"] < b2["close"])
        )
        green_pullback_below_ema = (
            is_green_non_doji(pb_green)
            and (pb_green["ema10"] > pb_green["close"])
        )
        sell_breakout = row_curr["low"] <= pb_green["low"]

        if three_black_soldiers and green_pullback_below_ema and sell_breakout:
            entry_price = round(float(pb_green["low"]), 2)
            sl_price = round(float(row_curr["ema10"]), 2)
            risk = max(sl_price - entry_price, 0.05)
            signals.append({
                "time": row_curr["timestamp"].strftime("%Y-%m-%d %H:%M"),
                "side": "SELL",
                "trigger_high_low": entry_price,
                "sl": sl_price,
                "t_1_1": round(entry_price - risk, 2),
                "t_1_2": round(entry_price - 2 * risk, 2),
                "t_1_3": round(entry_price - 3 * risk, 2),
            })

    return signals[:3]


def run_scanner(live_loop: bool = False) -> None:
    smart_api = connect_angel_one()
    today = datetime.now().date()
    sent_keys = set()

    while True:
        for item in WATCHLIST:
            df = fetch_5m_candles(smart_api, item["exchange"], item["symboltoken"], days_back=3)
            if df.empty:
                print(f"[INFO] {item['name']} साठी कॅण्डल डेटा मिळाला नाही.")
                continue

            day_signals = detect_setups_for_date(df, today)
            if not day_signals and not live_loop:
                print(f"[INFO] {item['name']} साठी आज ({today}) कोणतीही एन्ट्री तयार झालेली नाही.")

            for idx, sig in enumerate(day_signals, start=1):
                unique_key = f"{item['name']}_{sig['time']}_{sig['side']}"
                if unique_key in sent_keys:
                    continue
                sent_keys.add(unique_key)

                msg = (
                    f"<b>10 EMA Breakout Alert (#{idx}/3)</b>\n"
                    f"Symbol: <b>{item['name']}</b> ({item['exchange']})\n"
                    f"Side: <b>{sig['side']}</b> | Time: {sig['time']}\n"
                    f"Breakout Level: <code>{sig['trigger_high_low']}</code>\n"
                    f"SL (10 EMA): <code>{sig['sl']}</code>\n"
                    f"Targets: 1:1 <code>{sig['t_1_1']}</code> | "
                    f"1:2 <code>{sig['t_1_2']}</code> | "
                    f"1:3 <code>{sig['t_1_3']}</code>"
                )
                send_telegram_alert(msg)

        if not live_loop:
            break
        time.sleep(60)


if __name__ == "__main__":
    # आजच्या कॅण्डल्स तपासून अलर्ट पाठवण्यासाठी:
    run_scanner(live_loop=False)
