import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="AI Paper Trading Dashboard", page_icon="📈", layout="wide"
)

st.title("🤖 AI Paper Trading Agent – Dashboard")
st.markdown(
    "Tento dashboard sleduje reálne výkony a rozhodnutia tvojho AI tradera na"
    " GitHube."
)


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
  st.metric(label="Zostatok hotovosti (Cash)", value=f"{current_cash:.2f} EUR")

  st.divider()

  # OPRAVA: st.subheader namiesto st.sub_header
  st.subheader("📜 História virtuálnych obchodov")

  if not trades_df.empty:
    st.dataframe(trades_df, use_container_width=True)
  else:
    st.info("Zatiaľ neboli vykonané žiadne záznamy v databáze.")

except Exception as e:
  st.warning(
      "Zatiaľ sa nepodarilo nájsť databázu `paper_trading.db` (alebo je prázdna)."
      f" Chyba: {e}"
  )
