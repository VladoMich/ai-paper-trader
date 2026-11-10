import sqlite3
import pandas as pd
import streamlit as st
import yfinance as yf
from agent import run_trading_bot  # Importujeme funkciu na spustenie agenta

st.set_page_config(
    page_title="AI Paper Trading Dashboard", page_icon="📈", layout="wide"
)

st.title("🤖 AI Paper Trading Agent – Dashboard")
st.markdown(
    "Sleduje aktuálne trhové výkony, stav hotovosti a rozhodnutia AI tradera."
)

# --- SIDEBAR: Ovládanie a manuálne spustenie ---
with st.sidebar:
  st.header("⚙️ Ovládanie agenta")
  st.markdown(
      "Tu môžeš spustiť okamžitú analýzu trhu a obchodovanie bez čakania na"
      " GitHub Actions."
  )

  if st.button("🚀 Spustiť AI Analýzu hneď", type="primary"):
    with st.spinner("Prebieha sťahovanie dát a analýza cez Gemini..."):
      try:
        run_trading_bot()
        st.success("Analýza úspešne dokončená!")
        st.rerun()  # Obnoví aplikáciu a načíta nové dáta
      except Exception as e:
        st.error(f"Chyba pri behu agenta: {e}")


def load_data():
  conn = sqlite3.connect("paper_trading.db")
  account_df = pd.read_sql("SELECT * FROM account", conn)
  trades_df = pd.read_sql("SELECT * FROM trades ORDER BY timestamp DESC", conn)

  try:
    history_df = pd.read_sql(
        "SELECT * FROM portfolio_history ORDER BY timestamp ASC", conn
    )
  except Exception:
    history_df = pd.DataFrame()

  conn.close()
  return account_df, trades_df, history_df


try:
  account_df, trades_df, history_df = load_data()
  current_cash = (
      account_df["cash"].iloc[0] if not account_df.empty else 1000.0
  )

  # Výpočet reálnej hodnoty a P&L pre jednotlivé pozície
  current_holdings_value = 0.0
  holdings_summary = []

  if not trades_df.empty:
    # Zrátame čisté akcie a priemernú nákupnú cenu pre každú pozíciu
    # Prechádzame obchody v chronologickom poradí
    chronological_trades = trades_df.sort_values("timestamp", ascending=True)

    positions = {}
    for _, row in chronological_trades.iterrows():
      t = row["ticker"]
      action = row["action"]
      shares = row["shares"]
      price = row["price"]

      if t not in positions:
        positions[t] = {"shares": 0.0, "total_cost": 0.0}

      if action == "BUY":
        positions[t]["shares"] += shares
        positions[t]["total_cost"] += shares * price
      elif action == "SELL":
        if positions[t]["shares"] > 0:
          # Znížime náklady proporcionálne
          avg_p = positions[t]["total_cost"] / positions[t]["shares"]
          positions[t]["shares"] -= shares
          positions[t]["total_cost"] -= shares * avg_p

    for ticker, pos in positions.items():
      if pos["shares"] > 0.0001:
        avg_buy_price = pos["total_cost"] / pos["shares"]
        try:
          live_price = float(
              yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
          )
          market_val = pos["shares"] * live_price
          profit_loss = market_val - pos["total_cost"]
          profit_loss_pct = (
              (profit_loss / pos["total_cost"]) * 100
              if pos["total_cost"] > 0
              else 0
          )

          current_holdings_value += market_val
          holdings_summary.append({
              "Ticker": ticker,
              "Počet ks": round(pos["shares"], 4),
              "Priem. nákup (€)": round(avg_buy_price, 2),
              "Aktuálna cena (€)": round(live_price, 2),
              "Trhová hodnota (€)": round(market_val, 2),
              "Zisk / Strata (€)": round(profit_loss, 2),
              "Zisk / Strata (%)": round(profit_loss_pct, 2),
          })
        except Exception:
          pass

  total_portfolio_value = current_cash + current_holdings_value
  pnl = total_portfolio_value - 1000.0
  pnl_pct = (pnl / 1000.0) * 100

  # Metriky navrchu
  col1, col2, col3, col4 = st.columns(4)
  col1.metric(
      label="Celková hodnota",
      value=f"{total_portfolio_value:.2f} EUR",
      delta=f"{pnl:+.2f} EUR ({pnl_pct:+.2f}%)",
  )
  col2.metric(label="Voľná hotovosť", value=f"{current_cash:.2f} EUR")
  col3.metric(
      label="Aktuálna hodnota akcií", value=f"{current_holdings_value:.2f} EUR"
  )
  col4.metric(
      label="Otvorené pozície",
      value=len(holdings_summary) if holdings_summary else 0,
  )

  # Graf vývoja portfólia
  if not history_df.empty:
    st.markdown("### 📈 Vývoj hodnoty portfólia v čase")
    history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
    chart_data = history_df.set_index("timestamp")[
        ["total_value", "cash", "holdings_value"]
    ]
    chart_data.columns = [
        "Celková hodnota (€)",
        "Hotovosť (€)",
        "Hodnota akcií (€)",
    ]
    st.line_chart(chart_data)

  st.divider()

  # Zobrazenie otvorených pozícií s P&L
  if holdings_summary:
    st.subheader("📦 Aktuálne držané akcie a ich výkonnosť (P&L)")
    st.dataframe(
        pd.DataFrame(holdings_summary),
        use_container_width=True,
        hide_index=True,
    )
    st.divider()

  st.subheader("📜 História virtuálnych obchodov a rozhodnutí")
  if not trades_df.empty:
    st.dataframe(trades_df, use_container_width=True, hide_index=True)

    st.markdown("### 🔍 Detailné zdôvodnenia AI pre jednotlivé kroky")
    for index, row in trades_df.iterrows():
      badge = (
          "🟢"
          if row["action"] == "BUY"
          else ("🔴" if row["action"] == "SELL" else "⚪")
      )
      with st.expander(
          f"{badge} [{str(row['timestamp'])[:19]}] Ticker: **{row['ticker']}**"
          f" | Akcia: **{row['action']}** | Počet: {row['shares']} ks"
      ):
        st.markdown(f"**Cena:** {row['price']} EUR")
        st.markdown(f"**Zdôvodnenie od AI:** {row['reasoning']}")
  else:
    st.info("Zatiaľ neboli zaznamenané žiadne obchody.")

except Exception as e:
  st.warning(f"Databáza zatiaľ nie je dostupná alebo je prázdna. Chyba: {e}")
