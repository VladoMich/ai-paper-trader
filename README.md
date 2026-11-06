# 🤖 AI Paper Trading Agent

Automatizovaný papierový (virtuálny) obchodník poháňaný umelou inteligenciou (**Google Gemini**), ktorý denne analyzuje vybrané akciové trhy, vykonáva simulované obchody a ukladá dáta do SQLite databázy. Výsledky a stav portfólia sú vizualizované v reálnom čase pomocou **Streamlit** dashboardu.

---

## 🏗️ Architektúra a ako to funguje
1. **GitHub Actions (Cron):** 
   - Spúšťa sa automaticky raz denne (prípadne manuálne cez *Workflow dispatch*).
   - Skript `agent.py` sťahuje aktuálne trhové dáta pre sledované tickery cez knižnicu `yfinance`.
   - Vypočítava základné technické indikátory (kĺzavý priemer SMA 20, 5-dňovú percentuálnu zmenu).
2. **AI Analytik (Gemini API):**
   - Dáta spolu s aktuálnym stavom hotovosti sa odošlú modelu `gemini-3.8-flash`.
   - Model na základe prednastavených pravidiel vyhodnotí situáciu a vráti štruktúrovanú JSON odpoveď s akciou (`BUY`, `HOLD`), počtom kusov a zdôvodnením.
3. **Persistencia (SQLite):**
   - Všetky obchody a stav účtu sa ukladajú do lokálnej databázy `paper_trading.db`.
   - GitHub Action automaticky urobí `git commit & push` zmenenej databázy späť do repozitára.
4. **Dashboard (Streamlit Community Cloud):**
   - Aplikácia (`app.py`) číta dáta priamo z repozitára, vizualizuje celkovú hodnotu portfólia, voľnú hotovosť a detailnú históriu obchodov vrátane komentárov AI.

---

## 🚀 Sledované aktíva (Tickers)
- **NVDA** (NVIDIA)
- **AAPL** (Apple)
- **MSFT** (Microsoft)
- **TSLA** (Tesla)
- **GOOGL** (Alphabet)

---

## 🔮 Plány do budúcna
- [ ] Pridať pokročilé technické indikátory (RSI, MACD, volatilita).
- [ ] Rozšíriť rozhodovaciu logiku AI o predikčné modely a širšiu trhovú analýzu.
- [ ] Pridať graf vývoja hodnoty portfólia v čase priamo do Streamlit dashboardu.
