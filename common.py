"""Bagian yang dipakai bersama oleh semua halaman: kotak insight dan catatan kaki."""
import streamlit as st

import data
from insights import INSIGHTS

PAGE_TITLE = {"demand": "Pola aktivitas", "model": "Hasil prediksi", "network": "Jaringan stasiun"}
PAGES = {}  # diisi oleh app.py: nama halaman -> objek st.Page (untuk tautan antarhalaman)

REMINDER = "Insight untuk bagian ini belum ditulis. Isi teksnya di `insights.py`."


def insight_box(page: str):
    """Kotak insight di bagian atas halaman (teks berasal dari insights.py)."""
    for item in INSIGHTS:
        if item["page"] != page:
            continue
        if not item["body"].strip():
            st.warning(REMINDER, icon=":material/edit_note:")
            continue
        heading = f"**{item['title'].strip()}**\n\n" if item["title"].strip() else ""
        st.info(heading + item["body"].strip(), icon=":material/lightbulb:")


def insight_summary():
    """Judul semua insight di halaman Ringkasan, dengan tautan ke halaman yang memuat penjelasan dan grafiknya."""
    if not INSIGHTS:
        return
    st.subheader("Insight utama")
    columns = st.columns(len(INSIGHTS))
    for number, (column, item) in enumerate(zip(columns, INSIGHTS), start=1):
        with column.container(border=True, height="stretch"):
            st.caption(f"Insight {number} · {PAGE_TITLE[item['page']]}")
            if item["body"].strip():
                # Ringkasan cukup memuat judulnya; isi lengkap ada di halaman terkait.
                st.markdown(f"**{item['title'].strip() or item['body'].strip()}**")
            else:
                st.warning(REMINDER, icon=":material/edit_note:")
            if item["page"] in PAGES:
                st.page_link(PAGES[item["page"]], label="Lihat penjelasan dan grafiknya", icon=":material/arrow_forward:")


def footer():
    info = data.summary()
    st.divider()
    st.caption(
        "Sumber data: [Citi Bike System Data](https://citibikenyc.com/system-data) (perjalanan Jersey City, "
        "Mei–Juli 2019) dan [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) "
        "(ERA5), lisensi [CC BY 4.0](https://open-meteo.com/en/licence); data cuaca diratakan menjadi tabel dan "
        "dirangkum per hari. Diolah dengan PySpark (run "
        f"{info['run_id']}). Proyek akademik, tidak berafiliasi dengan dan tidak didukung oleh operator Citi Bike."
    )
