import json
import os
import sqlite3
from datetime import datetime
import yfinance as yf
from openai import OpenAI

# 1. ROZŠÍRENÝ ZBER TRHOVÝCH DÁT A SPRÁV
def fetch_market_data_with_news(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1mo")
    
    current_price = hist['Close'].iloc[-1]
    sma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
    change_5d = ((current_price - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100
    
    # Sťahovanie posledných správ cez yfinance
    raw_news = stock.news
    headlines = []
    if raw_news:
        # Vyberieme napr. posledných 5 titulkov správ
        for item in raw_news[:5]:
            # yfinance štruktúra môže obsahovať 'title' alebo 'content' -> 'title'
            title = item.get('title') or item.get('content', {}).get('title')
            if title:
                headlines.append(title)
                
    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "sma_20": round(sma_20, 2),
        "change_5d": round(change_5d, 2),
        "recent_headlines": headlines
    }

# 2. AI ROZHODOVANIE S VYUŽITÍM SPRÁV A SENTIMENTU
def get_ai_trade_recommendation(market_data, current_cash):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    prompt = f"""
    Si konzervatívny kvantitatívny analytik. Vyhodnot nasledujúce trhové dáta a mediálny sentiment:
    
    Ticker: {market_data['ticker']}
    Aktuálna cena: {market_data['current_price']} EUR
    SMA 20 (priemer): {market_data['sma_20']} EUR
    Zmena za 5 dní: {market_data['change_5d']}%
    
    Posledné titulky správ z trhu (vyhodnot ich sentiment - pozitívny/negatívny/neutrálny):
    {json.dumps(market_data['recent_headlines'], indent=2)}
    
    K dispozícii je celková hotovosť: {current_cash} EUR.
    Risk pravidlo: Maximálne 10% kapitálu na jeden obchod. Ak sú správy extrémne negatívne alebo je trh v neistote, zvoľ "HOLD".
    
    Vráť odpoveď EXKLUZÍVNE vo formáte JSON:
    {{
        "action": "BUY" | "SELL" | "HOLD",
        "shares": float,
        "sentiment_score": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
        "confidence": float (0-1),
        "reasoning": "Stručné zdôvodnenie vrátane vplyvu správ na 2-3 vety."
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)