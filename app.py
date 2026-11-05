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


# Pripojenie k databáze (predpokladá, že paper_trading.db je v rovnakom priečinku)
def load_data():
  conn = sqlite3.connect("paper_trading.db")

  # Načítame stav účtu / hotovosti
  account_df = pd.read_sql("SELECT * FROM account", conn)

  # Načítame históriu obchodov
  trades_df = pd.read_sql("SELECT * FROM trades ORDER BY timestamp DESC", conn)

  conn.close()
  return account_df, trades_df


try:
  account_df, trades_df = load_data()

  # 1. Metriky (KPI)
  current_cash = (
      account_df["cash"].iloc[0] if not account_df.empty else 1000.0
  )
  st.metric(label="Zostatok hotovosti (Cash)", value=f"{current_cash:.2f} EUR")

  st.divider()

  # 2. Tabuľka obchodov
  st.sub_header("📜 História virtuálnych obchodov")
  if not trades_df.empty:
    st.dataframe(trades_df, use_container_width=True)
  else:
    st.info(
        "Zatiaľ neboli vykonané žiadne obchody. Agent zatiaľ volí iba HOLD"
        " alebo čaká na ďalšie spustenie."
    )

except Exception as e:
  st.warning(
      "Zatiaľ sa nepodarilo nájsť databázu `paper_trading.db` (alebo je prázdna)."
      f" Chyba: {e}"
  )
  st.info(
      "Počkaj, kým GitHub Actions bot urobí prvý úspešný beh a stiahne databázu"
      " do repozitára."
  )
