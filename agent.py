import os
import sqlite3
import json
import time
from datetime import datetime
import yfinance as yf
from google import genai
from google.genai import types

DB_NAME = "paper_trading.db"
# Zoznam tickerov, ktoré bude agent každý deň prechádzať
TICKERS = ["NVDA", "AAPL", "MSFT", "TSLA", "GOOGL"]

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
    
    if hist.empty:
        raise ValueError(f"Nepodarilo sa stiahnuť dáta pre {ticker}")
        
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
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Si konzervatívny kvantitatívny analytik. Vyhodnot trhové dáta pre akciu {market_data['ticker']}:
    - Aktuálna cena: {market_data['current_price']} EUR
    - SMA 20 (kĺzavý priemer): {market_data['sma_20']} EUR
    - Zmena za 5 dní: {market_data['change_5d']}%
    - Celková dostupná hotovosť na účte: {current_cash} EUR.
    
    Pravidlá tradingu:
    - Ak vidíš silný rastový trend (napr. cena nad SMA 20), môžeš zvoliť "BUY".
    - Vypočítaj presný počet akcií (`shares`), ktoré chceš kúpiť, pričom celková suma nesmie presiahnuť 20% dostupnej hotovosti.
    - Ak si nie si istý alebo trh klesá, zvoľ "HOLD" (vtedy zadaj shares: 0).
    
    Vráť odpoveď EXKLUZÍVNE vo formáte JSON s týmito kľúčmi:
    action (string: "BUY" alebo "HOLD"),
    shares (float),
    reasoning (string: stručné zdôvodnenie).
    """
    
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Pokus {attempt} zlyhal: {e}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                raise RuntimeError("Gemini API zlyhalo po viacerých pokusoch.")

def execute_virtual_trade(decision, market_data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT cash FROM account WHERE id = 1")
    cash = cursor.fetchone()[0]
    
    ticker = market_data['ticker']
    price = market_data['current_price']
    action = decision.get('action', 'HOLD')
    shares = float(decision.get('shares', 0))
    reasoning = decision.get('reasoning', 'Bez dôvodu')
    
    print(f"AI rozhodnutie pre {ticker}: {action} ({shares} ks) - {reasoning}")
    
    if action == "BUY":
        cost = shares * price
        if cost <= cash and shares > 0:
            new_cash = cash - cost
            cursor.execute("UPDATE account SET cash = ? WHERE id = 1", (new_cash,))
            cursor.execute(
                "INSERT INTO trades (timestamp, ticker, action, shares, price, reasoning) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), ticker, action, shares, price, reasoning)
            )
            print(f"✅ NÁKUP: {shares}x {ticker} za {cost:.2f}€")
        else:
            print("❌ Nedostatok hotovosti pre tento nákup, mením na HOLD.")
            cursor.execute(
                "INSERT INTO trades (timestamp, ticker, action, shares, price, reasoning) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), ticker, "HOLD", 0, price, "Nedostatok hotovosti na nákup: " + reasoning)
            )
    else:
        cursor.execute(
            "INSERT INTO trades (timestamp, ticker, action, shares, price, reasoning) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), ticker, action, 0, price, reasoning)
        )
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    for ticker in TICKERS:
        try:
            market_data = fetch_market_data(ticker)
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT cash FROM account WHERE id = 1")
            current_cash = cursor.fetchone()[0]
            conn.close()
            
            decision = get_ai_trade_recommendation(market_data, current_cash)
            execute_virtual_trade(decision, market_data)
            
            # Krátka pauza medzi tickermi, aby sme nepreťažili API
            time.sleep(2)
        except Exception as e:
            print(f"Chyba pri spracovaní tickera {ticker}: {e}")
            
    print("Agent úspešne prešiel všetky tickery.")
