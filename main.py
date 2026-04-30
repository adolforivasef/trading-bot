import yfinance as yf
import pandas as pd
import requests
import time
import os

# ===== CONFIG =====
TOKEN = os.getenv("8655596407:AAENe10VPDPEe6wC_-KZdaqpvT8o7O2-blY")
CHAT_ID = os.getenv("881645405")

RIESGO_EUR = 30
SL_PUNTOS = 7   # 🔥 TU REGLA FIJA
RR = 2          # riesgo beneficio

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
    if not TOKEN or not CHAT_ID:
        print("⚠️ Telegram no configurado")
        return

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

    # volumen fuerte
    if float(ultima["Volume"]) < float(ultima["VOL_MED"]):
        return None

    # tendencia clara
    alcista = float(ultima["EMA50"]) > float(ultima["EMA200"])
    bajista = float(ultima["EMA50"]) < float(ultima["EMA200"])

    # pullback real (clave)
    pullback_long = float(prev["Close"]) < float(prev["EMA20"])
    pullback_short = float(prev["Close"]) > float(prev["EMA20"])

    # confirmación vela
    vela_verde = float(ultima["Close"]) > float(ultima["Open"])
    vela_roja = float(ultima["Close"]) < float(ultima["Open"])

    if alcista and pullback_long and vela_verde:
        return "COMPRA"

    if bajista and pullback_short and vela_roja:
        return "VENTA"

    return None

# ===== TRADE =====
def calcular_trade(df, tipo):

    precio = float(df.iloc[-1]["Close"])

    # 🔥 SL FIJO
    if tipo == "COMPRA":
        sl = precio - SL_PUNTOS
        tp = precio + (SL_PUNTOS * RR)

    else:
        sl = precio + SL_PUNTOS
        tp = precio - (SL_PUNTOS * RR)

    riesgo = SL_PUNTOS

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

            # evitar repetir
            if ULTIMA_SENAL.get(nombre) == señal:
                continue

            trade = calcular_trade(df, señal)

            mensaje = f"""
{señal} {nombre}

Entrada: {trade['entrada']:.2f}
SL: {trade['sl']:.2f}
TP: {trade['tp']:.2f}

Riesgo fijo: {SL_PUNTOS} puntos
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
        run()
        print("⏳ Esperando 5 minutos...\n")
        time.sleep(300)