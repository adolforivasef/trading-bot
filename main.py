import yfinance as yf
import pandas as pd
import requests
import time
import os

# ===== CONFIG =====

TOKEN = os.getenv("TOKEN") or "8655596407:AAENe10VPDPEe6wC_-KZdaqpvT8o7O2-blY"
CHAT_ID = os.getenv("CHAT_ID") or "881645405"

RIESGO_EUR = 30

ACTIVOS = {
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DAX": "^GDAXI",
    "ORO": "GC=F",
    "BRENT": "BZ=F",
}

ULTIMA_SENAL = {}

# ===== TELEGRAM =====

def enviar_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print("Error Telegram:", e)

# ===== DATA =====

def get_data(ticker):
    try:
        df = yf.download(ticker, interval="15m", period="3d", progress=False)

        if df is None or df.empty:
            return None

        # 🔥 FIX CLAVE
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df["EMA20"] = df["Close"].ewm(span=20).mean()
        df["EMA50"] = df["Close"].ewm(span=50).mean()
        df["EMA200"] = df["Close"].ewm(span=200).mean()
        df["VOL_MED"] = df["Volume"].rolling(20).mean()

        return df.dropna()

    except Exception as e:
        print(f"Error datos {ticker}:", e)
        return None

# ===== SEÑAL =====

def generar_senal(df):

    if df is None or len(df) < 210:
        return None

    ultima = df.iloc[-1]
    prev = df.iloc[-2]

    # volumen
    if float(ultima["Volume"]) < float(ultima["VOL_MED"]):
        return None

    # tendencia
    alcista = float(ultima["EMA50"]) > float(ultima["EMA200"])
    bajista = float(ultima["EMA50"]) < float(ultima["EMA200"])

    # pullback EMA20 (más realista intradía)
    pullback_long = float(prev["Low"]) <= float(prev["EMA20"])
    pullback_short = float(prev["High"]) >= float(prev["EMA20"])

    # confirmación vela
    ruptura_alcista = float(ultima["Close"]) > float(prev["High"])
    ruptura_bajista = float(ultima["Close"]) < float(prev["Low"])

    if alcista and pullback_long and ruptura_alcista:
        return "COMPRA"

    if bajista and pullback_short and ruptura_bajista:
        return "VENTA"

    return None

# ===== TRADE =====

def calcular_trade(df, tipo):

    precio = float(df.iloc[-1]["Close"])

    if tipo == "COMPRA":
        sl = float(df["Low"].iloc[-5:].min())
        riesgo = precio - sl
        tp = precio + (riesgo * 1.5)

    else:
        sl = float(df["High"].iloc[-5:].max())
        riesgo = sl - precio
        tp = precio - (riesgo * 1.5)

    if riesgo <= 0:
        return None

    tamaño = RIESGO_EUR / riesgo

    return {
        "entrada": precio,
        "sl": sl,
        "tp": tp,
        "riesgo": riesgo,
        "tamaño": tamaño
    }

# ===== RUN =====

def run():
    print("\n--- Analizando mercado ---\n")

    for nombre, ticker in ACTIVOS.items():

        try:
            df = get_data(ticker)

            if df is None:
                print(f"{nombre}: sin datos")
                continue

            señal = generar_senal(df)

            if señal is None:
                print(f"{nombre}: sin señal")
                continue

            if ULTIMA_SENAL.get(nombre) == señal:
                continue

            trade = calcular_trade(df, señal)

            if trade is None:
                continue

            mensaje = f"""
{señal} {nombre}

Entrada: {trade['entrada']:.2f}
SL: {trade['sl']:.2f}
TP: {trade['tp']:.2f}

Riesgo: {trade['riesgo']:.2f}
Tamaño: {trade['tamaño']:.2f}
"""

            print(mensaje)
            enviar_telegram(mensaje)

            ULTIMA_SENAL[nombre] = señal

        except Exception as e:
            print(f"{nombre} ERROR:", e)

# ===== LOOP =====

if __name__ == "__main__":

    print("🚀 BOT INICIADO")

    while True:
        try:
            run()
        except Exception as e:
            print("Error general:", e)

        print("⏳ Esperando 5 minutos...\n")
        time.sleep(300)