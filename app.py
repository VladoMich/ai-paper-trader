import sqlite3
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="AI Paper Trading Dashboard", page_icon="📈", layout="wide"
)

st.title("🤖 AI Paper Trading Agent – Dashboard")
st.markdown(
    "Sleduje aktuálne trhové výkony, stav hotovosti a rozhodnutia AI tradera."
)


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

  # Výpočet REÁLNEJ trhovej hodnoty otvorených pozícií (Mark-to-Market)
  current_holdings_value = 0.0
  holdings_summary = []

  if not trades_df.empty:
    summary = (
        trades_df.groupby("ticker")
        .apply(
            lambda x: (x[x["action"] == "BUY"]["shares"].sum())
            - (x[x["action"] == "SELL"]["shares"].sum())
        )
        .reset_index(name="net_shares")
    )
    active_positions = summary[summary["net_shares"] > 0]

    for _, row in active_positions.iterrows():
      ticker = row["ticker"]
      shares = row["net_shares"]
      try:
        live_price = float(
            yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
        )
        value = shares * live_price
        current_holdings_value += value
        holdings_summary.append({
            "Ticker": ticker,
            "Počet ks": round(shares, 4),
            "Aktuálna cena": f"{live_price:.2f} €",
            "Trhová hodnota": f"{value:.2f} €",
        })
      except Exception:
        pass

  total_portfolio_value = current_cash + current_holdings_value
  pnl = total_portfolio_value - 1000.0  # Vstupný kapitál bol 1000 EUR
  pnl_pct = (pnl / 1000.0) * 100

  # Metriky navrchu (OPRAVENÉ volanie 4. metriky)
  col1, col2, col3, col4 = st.columns(4)
  col1.metric(
      label="Celková hodnota (Trhová)",
      value=f"{total_portfolio_value:.2f} EUR",
      delta=f"{pnl:+.2f} EUR ({pnl_pct:+.2f}%)",
  )
  col2.metric(label="Voľná hotovosť", value=f"{current_cash:.2f} EUR")
  col3.metric(
      label="Aktuálna hodnota akcií", value=f"{current_holdings_value:.2f} EUR"
  )
  col4.metric(
      label="Počet otvorených pozícií",
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

  # Zobrazenie otvorených pozícií ak existujú
  if holdings_summary:
    st.subheader("📦 Aktuálne držané akcie")
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
      badge = "🟢" if row["action"] == "BUY" else "⚪"
      with st.expander(
          f"{badge} [{str(row['timestamp'])[:19]}] Ticker: **{row['ticker']}**"
          f" | Akcia: **{row['action']}** | Počet: {row['shares']} ks"
      ):
        st.markdown(f"**Nákupná cena:** {row['price']} EUR")
        st.markdown(f"**Zdôvodnenie od AI:** {row['reasoning']}")
  else:
    st.info("Zatiaľ neboli zaznamenané žiadne obchody.")

except Exception as e:
  st.warning(f"Databáza zatiaľ nie je dostupná alebo je prázdna. Chyba: {e}")
