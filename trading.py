import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime, timezone

# -------- CONFIG --------
tickers = ["SPY","QQQ","NVDA","MSFT","AMZN","META"]

TOKEN = "8655596407:AAENe10VPDPEe6wC_-KZdaqpvT8o7O2-blY"
CHAT_ID = "881645405"

RISK_EUR = 30
last_message = None

# -------- TELEGRAM --------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

# -------- DATA --------
def get_data(ticker):
    df = yf.download(ticker, period="5d", interval="15m", progress=False)

    if df is None or df.empty:
        return None

    # 🔥 SOLUCIÓN CLAVE → quitar multi-index
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.dropna()

    return df

# -------- MERCADO --------
def market_direction():
    df = get_data("SPY")
    if df is None or len(df) < 200:
        return "neutral"

    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    ema50 = df["EMA50"].iloc[-1]
    ema200 = df["EMA200"].iloc[-1]

    if ema50 > ema200:
        return "bull"
    elif ema50 < ema200:
        return "bear"
    else:
        return "neutral"

# -------- FILTRO LATERAL --------
def is_trending(df):
    if len(df) < 20:
        return False

    high = df["High"].iloc[-20:].max()
    low = df["Low"].iloc[-20:].min()

    return (high - low) / low > 0.01

# -------- SEÑALES --------
def get_signal(df, ticker):
    if df is None or len(df) < 50:
        return None

    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["EMA200"] = df["Close"].ewm(span=200).mean()

    ema50 = df["EMA50"].iloc[-1]
    ema200 = df["EMA200"].iloc[-1]
    close = df["Close"].iloc[-1]

    breakout = df["High"].iloc[-10:-1].max()
    breakdown = df["Low"].iloc[-10:-1].min()

    # -------- COMPRA --------
    if ema50 > ema200 and is_trending(df):
        if close > breakout:

            entry = close
            stop = df["Low"].iloc[-5:].min()
            tp = entry + (entry - stop) * 2

            risk = entry - stop
            if risk <= 0:
                return None

            size = RISK_EUR / risk

            return f"""🟢 COMPRA {ticker}
Entrada: {entry:.2f}
Stop: {stop:.2f}
TP: {tp:.2f}

Riesgo: {risk:.2f}
Tamaño: {size:.2f} €/punto"""

    # -------- VENTA --------
    if ema50 < ema200 and is_trending(df):
        if close < breakdown:

            entry = close
            stop = df["High"].iloc[-5:].max()
            tp = entry - (stop - entry) * 2

            risk = stop - entry
            if risk <= 0:
                return None

            size = RISK_EUR / risk

            return f"""🔴 VENTA {ticker}
Entrada: {entry:.2f}
Stop: {stop:.2f}
TP: {tp:.2f}

Riesgo: {risk:.2f}
Tamaño: {size:.2f} €/punto"""

    return None

# -------- RUN --------
def run():
    global last_message

    print("\nAnalizando mercado...\n")

    hour = datetime.now(timezone.utc).hour
    if hour < 13 or hour > 20:
        print("⏰ Fuera horario USA")
        return

    direction = market_direction()

    mensajes = []

    for t in tickers:
        df = get_data(t)
        if df is None:
            continue

        signal = get_signal(df, t)

        if signal:
            if "COMPRA" in signal and direction != "bull":
                continue
            if "VENTA" in signal and direction != "bear":
                continue

            print(signal)
            mensajes.append(signal)

    if mensajes:
        final = "🚨 SEÑALES PRO 🚨\n\n" + "\n\n".join(mensajes)
        if final != last_message:
            send_telegram(final)
            last_message = final
    else:
        print("Sin oportunidades")

# -------- LOOP --------
while True:
    run()
    time.sleep(900)