import json
import os
import sqlite3
from datetime import datetime
import yfinance as yf
from openai import OpenAI

print("Šartujem skript agenta...")

def init_db():
    print("Pripájam sa do SQLite databázy...")
    conn = sqlite3.connect("paper_trading.db")
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
    print("Databáza je pripravená.")

def fetch_market_data_with_news(ticker):
    print(f"Sťahujem dáta pre {ticker} z Yahoo Finance...")
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1mo")
    
    current_price = float(hist['Close'].iloc[-1])
    sma_20 = float(hist['Close'].rolling(window=20).mean().iloc[-1])
    change_5d = float(((current_price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100)
    
    headlines = []
    try:
        raw_news = getattr(stock, 'news', [])
        if raw_news:
            for item in raw_news[:5]:
                title = item.get('title') or item.get('content', {}).get('title')
                if title:
                    headlines.append(title)
    except Exception as e:
        print(f"Varovanie: Nepodarilo sa stiahnuť správy: {e}")
                
    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "sma_20": round(sma_20, 2),
        "change_5d": round(change_5d, 2),
        "recent_headlines": headlines
    }

def get_ai_trade_recommendation(market_data, current_cash):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Chýba OPENAI_API_KEY v premenných prostredia!")
        
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
    Si konzervatívny kvantitatívny analytik. Vyhodnot nasledujúce trhové dáta:
    Ticker: {market_data['ticker']}
    Aktuálna cena: {market_data['current_price']} EUR
    SMA 20: {market_data['sma_20']} EUR
    Zmena za 5 dní: {market_data['change_5d']}%
    Dostupná hotovosť: {current_cash} EUR.
    
    Vráť odpoveď EXKLUZÍVNE vo formáte JSON:
    {{
        "action": "BUY" | "SELL" | "HOLD",
        "shares": float,
        "sentiment_score": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
        "confidence": float (0-1),
        "reasoning": "Stručné zdôvodnenie."
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def execute_virtual_trade(decision, market_data):
    conn = sqlite3.connect("paper_trading.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT cash FROM account WHERE id = 1")
    row = cursor.fetchone()
    cash = row[0] if row else 1000.0
    
    ticker = market_data['ticker']
    price = market_data['current_price']
    action = decision.get('action', 'HOLD')
    shares = decision.get('shares', 0)
    reasoning = decision.get('reasoning', 'Bez dôvodu')
    
    print(f"AI rozhodnutie pre {ticker}: {action} ({shares} ks) - {reasoning}")
    
    if action == "BUY":
        cost = shares * price
        if cost <= cash:
            new_cash = cash - cost
            cursor.execute("UPDATE account SET cash = ? WHERE id = 1", (new_cash,))
            cursor.execute(
                "INSERT INTO trades (timestamp, ticker, action, shares, price, reasoning) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), ticker, action, shares, price, reasoning)
            )
            print(f"✅ ÚSPEŠNÝ NÁKUP: {shares}x {ticker} po {price}€.")
        else:
            print("❌ Nedostatok hotovosti na nákup.")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    try:
        init_db()
        data = fetch_market_data_with_news("NVDA")
        
        conn = sqlite3.connect("paper_trading.db")
        c = conn.cursor()
        c.execute("SELECT cash FROM account WHERE id = 1")
        current_cash = c.fetchone()[0]
        conn.close()
        
        decision = get_ai_trade_recommendation(data, current_cash)
        execute_virtual_trade(decision, data)
        print("Skript úspešne dokončený, databáza paper_trading.db vytvorená.")
    except Exception as e:
        print(f"CHYBA V SKRIPTE: {str(e)}")
        raise e
