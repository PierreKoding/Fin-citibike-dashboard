"""Dashboard Citi Bike Jersey City (Final Project Big Data Analytics).

Jalankan:  streamlit run app.py
Data dibaca dari folder data/ yang dibuat oleh prepare_data.py.
"""
import streamlit as st

st.set_page_config(page_title="Dashboard Citi Bike Jersey City", page_icon=":material/pedal_bike:", layout="wide")

import common  # noqa: E402  (set_page_config harus dipanggil lebih dulu)
from views import demand, model, network, overview  # noqa: E402

page_overview = st.Page(overview.render, title="Ringkasan", icon=":material/dashboard:", default=True)
page_demand = st.Page(demand.render, title="Pola aktivitas", icon=":material/schedule:", url_path="pola")
page_model = st.Page(model.render, title="Hasil prediksi", icon=":material/monitoring:", url_path="prediksi")
page_network = st.Page(network.render, title="Jaringan stasiun", icon=":material/hub:", url_path="jaringan")

common.PAGES.update({"demand": page_demand, "model": page_model, "network": page_network})

current = st.navigation([page_overview, page_demand, page_model, page_network], position="top")
current.run()
common.footer()
