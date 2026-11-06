import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="AI Paper Trading Dashboard", page_icon="📈", layout="wide"
)

st.title("🤖 AI Paper Trading Agent – Dashboard")
st.markdown("Sleduje reálne výkony, stav hotovosti a rozhodnutia AI tradera.")


def load_data():
  conn = sqlite3.connect("paper_trading.db")
  account_df = pd.read_sql("SELECT * FROM account", conn)
  trades_df = pd.read_sql("SELECT * FROM trades ORDER BY timestamp DESC", conn)
  conn.close()
  return account_df, trades_df


try:
  account_df, trades_df = load_data()

  current_cash = (
      account_df["cash"].iloc[0] if not account_df.empty else 1000.0
  )

  invested_value = 0.0
  if not trades_df.empty:
    buys = trades_df[trades_df["action"] == "BUY"]
    if not buys.empty:
      invested_value = (buys["shares"] * buys["price"]).sum()

  total_portfolio_value = current_cash + invested_value

  # Metriky navrchu
  col1, col2, col3 = st.columns(3)
  col1.metric(
      label="Celková hodnota portfólia", value=f"{total_portfolio_value:.2f} EUR"
  )
  col2.metric(label="Voľná hotovosť (Cash)", value=f"{current_cash:.2f} EUR")
  col3.metric(label="Celkom investované", value=f"{invested_value:.2f} EUR")

  st.divider()

  st.subheader("📜 História virtuálnych obchodov a rozhodnutí")

  if not trades_df.empty:
    # 1. Klasická tabuľka (rýchly prehľad)
    st.dataframe(trades_df, use_container_width=True, hide_index=True)

    st.markdown("### 🔍 Detailné zdôvodnenia AI pre jednotlivé kroky")
    # 2. Prehľadné karty pre každý záznam, kde sa text nikdy neodreže
    for index, row in trades_df.iterrows():
      badge = "🟢" if row["action"] == "BUY" else "⚪"
      with st.expander(
          f"{badge} [{row['timestamp'][:19]}] Ticker: **{row['ticker']}** |"
          f" Akcia: **{row['action']}** | Počet: {row['shares']} ks"
      ):
        st.markdown(f"**Cena:** {row['price']} EUR")
        st.markdown(f"**Zdôvodnenie od AI:** {row['reasoning']}")
  else:
    st.info("Zatiaľ neboli zaznamenané žiadne obchody.")

except Exception as e:
  st.warning(f"Databáza zatiaľ nie je dostupná alebo je prázdna. Chyba: {e}")
