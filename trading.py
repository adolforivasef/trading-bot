import yfinance as yf
import smtplib
from email.mime.text import MIMEText
import requests
import time

# -------- CONFIG --------

tickers = ["QQQ","SPY","NVDA","MSFT","AMZN","META"]

# 📩 EMAIL (opcional)
EMAIL = "TU_EMAIL@gmail.com"
PASSWORD = "TU_PASSWORD_APP"

# 🤖 TELEGRAM
TOKEN = "8655596407:AAENe10VPDPEe6wC_-KZdaqpvT8o7O2-blY"
CHAT_ID = "881645405"

# -------- EMAIL --------
def send_email(msg):
    try:
        m = MIMEText(msg)
        m["Subject"] = "ALERTA TRADING"
        m["From"] = EMAIL
        m["To"] = EMAIL

        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(EMAIL, PASSWORD)
        s.send_message(m)
        s.quit()
    except:
        pass

# -------- TELEGRAM --------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": msg
    }
    requests.post(url, data=data)

# -------- UTILS --------
def get_data(t):
    try:
        df = yf.download(t, period="1y", interval="1d", progress=False)
        if df is None or df.empty:
            return None
        return df
    except:
        return None

def clean(series):
    return [float(x) for x in series.squeeze().tolist() if str(x) != "nan"]

def rsi(close, period=14):
    gains, losses = [], []
    for i in range(-period, 0):
        diff = close[i] - close[i-1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains)/period if gains else 0
    avg_loss = sum(losses)/period if losses else 1

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# -------- MERCADO --------
def market_ok():
    df = get_data("SPY")
    if df is None:
        return False, "Error datos mercado"

    close = clean(df["Close"])
    if len(close) < 200:
        return False, "Datos insuficientes"

    price = close[-1]
    ma50 = sum(close[-50:]) / 50
    ma200 = sum(close[-200:]) / 200

    if price > ma50 and ma50 > ma200:
        return True, "🟢 Mercado FUERTE"
    elif price > ma200:
        return False, "🟡 Mercado NEUTRO"
    else:
        return False, "🔴 Mercado DÉBIL"

# -------- BASE --------
def valid_base(high):
    recent_high = max(high[-20:])
    recent_low = min(high[-20:])
    return (recent_high - recent_low) / recent_low < 0.08

# -------- ANALISIS --------
def analyze(t):
    df = get_data(t)
    if df is None:
        return None

    close = clean(df["Close"])
    high = clean(df["High"])
    low = clean(df["Low"])

    if len(close) < 200:
        return None

    price = close[-1]
    ma50 = sum(close[-50:]) / 50
    ma200 = sum(close[-200:]) / 200
    r = rsi(close)

    breakout = max(high[-20:-1])
    atr = sum(abs(h - l) for h, l in zip(high[-14:], low[-14:])) / 14

    tendencia = price > ma50 and ma50 > ma200
    base = valid_base(high)
    ruptura = price > breakout
    confirmacion = price < breakout * 1.05
    rsi_ok = r < 70

    if all([tendencia, base, ruptura, confirmacion, rsi_ok]):
        return f"""
{t} → COMPRAR
Precio: {round(price,2)}
Entrada: {round(breakout,2)}
Stop: {round(breakout - 1.5*atr,2)}
Objetivo: {round(breakout + 2*(1.5*atr),2)}
"""

    return None

# -------- RUN --------
def run():
    
    ok, estado = market_ok()
    print("\n" + estado)

    if not ok:
        print("NO OPERAR\n")
        return

    print("Buscando oportunidades...\n")

    mensajes = []

    for t in tickers:
        res = analyze(t)
        if res:
            print(res)
            mensajes.append(res)

    if mensajes:
        final = "🚨 SETUPS A+ 🚨\n\n" + "\n".join(mensajes)
        send_telegram(final)
        send_email(final)
    else:
        print("Sin oportunidades claras\n")

# -------- LOOP --------
while True:
    run()
    time.sleep(900)