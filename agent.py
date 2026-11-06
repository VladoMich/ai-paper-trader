import os
import sqlite3
import json
from datetime import datetime
import yfinance as yf
from google import genai
from google.genai import types

DB_NAME = "paper_trading.db"

def init_db():
    print(f"Opening database at: {os.path.abspath(DB_NAME)}")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY,
            cash REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ticker TEXT,
            action TEXT,
            shares REAL,
            price REAL,
            reasoning TEXT
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM account")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO account (id, cash) VALUES (1, 1000.0)")
    conn.commit()
    conn.close()
    print("Databáza úspešne inicializovaná.")

def fetch_market_data(ticker):
    print(f"Sťahujem dáta pre {ticker} z Yahoo Finance...")
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1mo")
    
    current_price = float(hist['Close'].iloc[-1])
    sma_20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
    change_5d = float(((current_price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100)
    
    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "sma_20": round(sma_20, 2),
        "change_5d": round(change_5d, 2)
    }

def get_ai_trade_recommendation(market_data, current_cash):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Chýba GEMINI_API_KEY v premenných prostredia!")
        
    # Inicializácia nového Gemini klienta
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Si konzervatívny kvantitatívny analytik. Vyhodnot nasledujúce trhové dáta pre akciu {market_data['ticker']}:
    - Aktuálna cena: {market_data['current_price']} EUR
    - SMA 20 (kĺzavý priemer): {market_data['sma_20']} EUR
    - Zmena za 5 dní: {market_data['change_5d']}%
    - Dostupná hotovosť: {current_cash} EUR.
    
    Risk pravidlo: Maximálne 10% hotovosti na jeden obchod. Zvoľ "BUY", "SELL" alebo "HOLD".
    
    Vráť odpoveď EXKLUZÍVNE vo formáte JSON s týmito kľúčmi:
    action (string: BUY, SELL alebo HOLD),
    shares (float),
    reasoning (string: stručné zdôvodnenie).
    """
    
    # Použijeme rýchly a inteligentný gemini-2.5-flash model
    response = client.models.generate_content(
        model='gemini-3.8-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    
    return json.loads(response.text)

def execute_virtual_trade(decision, market_data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT cash FROM account WHERE id = 1")
    row = cursor.fetchone()
    cash = row[0] if row else 1000.0
    
    ticker = market_data['ticker']
    price = market_data['current_price']
    action = decision.get('action', 'HOLD')
    shares = float(decision.get('shares', 0))
    reasoning = decision.get('reasoning', 'Bez dôvodu')
    
    print(f"AI rozhodnutie (Gemini) pre {ticker}: {action} ({shares} ks) - {reasoning}")
    
    if action == "BUY":
        cost = shares * price
        if cost <= cash and shares > 0:
            new_cash = cash - cost
            cursor.execute("UPDATE account SET cash = ? WHERE id = 1", (new_cash,))
            cursor.execute(
                "INSERT INTO trades (timestamp, ticker, action, shares, price, reasoning) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), ticker, action, shares, price, reasoning)
            )
            print(f"✅ ÚSPEŠNÝ NÁKUP: {shares}x {ticker} po {price}€.")
        else:
            print("❌ Nedostatok hotovosti alebo neplatný počet akcii, mením na HOLD.")
            cursor.execute(
                "INSERT INTO trades (timestamp, ticker, action, shares, price, reasoning) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), ticker, "HOLD", 0, price, "Pokus o nákup zlyhal: " + reasoning)
            )
    else:
        cursor.execute(
            "INSERT INTO trades (timestamp, ticker, action, shares, price, reasoning) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), ticker, action, 0, price, reasoning)
        )
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    try:
        init_db()
        market_data = fetch_market_data("NVDA")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT cash FROM account WHERE id = 1")
        current_cash = cursor.fetchone()[0]
        conn.close()
        
        decision = get_ai_trade_recommendation(market_data, current_cash)
        execute_virtual_trade(decision, market_data)
        print("Agent úspešne dokončil analýzu s Gemini.")
    except Exception as e:
        print(f"KRITICKÁ CHYBA: {e}")
        raise e
