import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime, UTC

# -------- CONFIG --------
tickers = ["SPY","QQQ","NVDA","MSFT","AMZN","META"]

TOKEN = "8655596407:AAENe10VPDPEe6wC_-KZdaqpvT8o7O2-blY"
CHAT_ID = "881645405"

last_message = None

# -------- TELEGRAM --------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }
    requests.post(url, data=data)

# -------- DATA --------
def get_data(ticker):
    df = yf.download(ticker, period="6mo", interval="1d", progress=False)
    if df is None or df.empty:
        return None
    return df

# -------- SEÑALES --------
def get_signal(df):
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # COMPRA
    if last["EMA50"] > last["EMA200"]:
        if abs(last["Close"] - last["EMA50"]) / last["Close"] < 0.01:
            if last["Close"] > prev["Close"]:

                entry = float(last["Close"])
                stop = float(df["Low"].iloc[-5:].min())
                tp = entry + (entry - stop) * 2

                return f"🟢 COMPRA\nEntrada: {entry:.2f}\nStop: {stop:.2f}\nTP: {tp:.2f}"

    # VENTA
    if last["EMA50"] < last["EMA200"]:
        if abs(last["Close"] - last["EMA50"]) / last["Close"] < 0.01:
            if last["Close"] < prev["Close"]:

                entry = float(last["Close"])
                stop = float(df["High"].iloc[-5:].max())
                tp = entry - (stop - entry) * 2

                return f"🔴 VENTA\nEntrada: {entry:.2f}\nStop: {stop:.2f}\nTP: {tp:.2f}"

    return None

# -------- MERCADO --------
def market_ok():
    df = get_data("SPY")
    if df is None or len(df) < 200:
        return False

    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    last = df.iloc[-1]

    return bool(last["EMA50"] > last["EMA200"])

# -------- RUN --------
def run():
    global last_message

    print("\nAnalizando mercado...\n")

    # 🔹 FILTRO HORARIO (USA)
    hour = datetime.now(UTC).hour
    if hour < 12 or hour > 19:
        print("⏰ Fuera de horario de mercado")
        return

    # 🔹 MERCADO
    if not market_ok():
        msg = "❌ Mercado débil, no operar"
        print(msg)
        if msg != last_message:
            send_telegram(msg)
            last_message = msg
        return

    print("✅ Mercado favorable\n")

    mensajes = []

    for t in tickers:
        df = get_data(t)
        if df is None or len(df) < 200:
            continue

        signal = get_signal(df)

        if signal:
            texto = f"{t}\n{signal}"
            print(texto)
            mensajes.append(texto)

    # 🔹 ENVÍO CONTROLADO
    if mensajes:
        final = "🚨 SEÑALES 🚨\n\n" + "\n\n".join(mensajes)
        if final != last_message:
            send_telegram(final)
            last_message = final
    else:
        msg = "⚠️ Sin oportunidades"
        print(msg)
        if msg != last_message:
            send_telegram(msg)
            last_message = msg

# -------- LOOP --------
while True:
    run()
    time.sleep(900)