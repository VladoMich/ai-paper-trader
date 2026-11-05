import os
import sqlite3
import json
from datetime import datetime
import yfinance as yf
from openai import OpenAI

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

if __name__ == "__main__":
    try:
        init_db()
        if os.path.exists(DB_NAME):
            print(f"Fyzický súbor databázy úspešne potvrdený na disku: {DB_NAME}")
        else:
            print("CHYBA: Súbor databázy sa nenašiel!")
    except Exception as e:
        print(f"KRITICKÁ CHYBA: {e}")
        raise e
