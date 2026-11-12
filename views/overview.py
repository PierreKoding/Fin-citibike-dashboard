"""Halaman Ringkasan: angka utama, rangkuman insight, dan tren harian bersama cuaca."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import common
import data
import style as s


def render():
    info = data.summary()
    daily = data.daily()
    pred = data.predictions()

    st.title("Aktivitas Citi Bike Jersey City")
    st.caption("1 Mei – 31 Juli 2019 · perjalanan per stasiun per jam, prediksi untuk Juli 2019, "
               "dan hubungan perjalanan antarstasiun")

    # ---------------------------------------------------------- angka utama
    tiles = st.columns([1, 1, 1, 1.35, 1.35])
    tiles[0].metric("Perjalanan tercatat", s.num(info["trips_total"]), border=True, height="stretch",
                    help="Seluruh perjalanan yang berangkat pada 1 Mei–31 Juli 2019.")
    tiles[1].metric("Rata-rata per hari", s.num(info["trips_total"] / info["days"]), border=True, height="stretch",
                    help=f"Total perjalanan dibagi {info['days']} hari.")
    tiles[2].metric("Stasiun dianalisis", s.num(info["stations_in_scope"]), border=True, height="stretch",
                    help="Stasiun yang sudah menjadi asal perjalanan sebelum 16 Juni 2019. "
                         "Stasiun yang baru muncul setelahnya tidak masuk grafik per stasiun.")
    for tile, target in zip(tiles[3:], s.TARGETS):
        part = pred[pred["target"] == target]
        mae_model = (part["tanpa_cuaca"] - part["actual"]).abs().mean()
        mae_base = (part["baseline_minggu_lalu"] - part["actual"]).abs().mean()
        change = (mae_model / mae_base - 1) * 100
        tile.metric(
            f"Selisih prediksi {s.TARGET_LABEL[target].lower()}",
            s.num(mae_model, 2),
            delta=f"{change:.1f}%".replace(".", ","),
            delta_color="inverse",
            delta_description="dibanding baseline",
            border=True, height="stretch",
            help="Rata-rata selisih antara prediksi model tanpa cuaca dan jumlah aktual, dalam perjalanan "
                 "per stasiun per jam, pada Juli 2019 (MAE). Lebih kecil lebih baik. Baseline = jumlah pada "
                 "jam yang sama seminggu sebelumnya.",
        )

    # ------------------------------------------------------ rangkuman insight
    common.insight_summary()

    # ------------------------------------------------ tren harian dan cuaca
    with s.card("Perjalanan per hari, curah hujan, dan suhu",
                "Tiga panel dengan sumbu waktu yang sama. Arahkan kursor untuk membaca nilai pada satu tanggal."):
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                            row_heights=[0.5, 0.25, 0.25])
        days = [s.DAY_NAMES[d] for d in daily["date"].dt.dayofweek]
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["trips"], name="Perjalanan", mode="lines",
            line=dict(color=s.ACCENT, width=2), fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
            customdata=days, hovertemplate="%{y:,.0f} (%{customdata})<extra>Perjalanan</extra>"), row=1, col=1)
        fig.add_trace(go.Bar(
            x=daily["date"], y=daily["precip_mm"], name="Curah hujan", marker_color=s.MUTED,
            hovertemplate="%{y:,.1f} mm<extra>Curah hujan</extra>"), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["temp_mean_c"], name="Suhu rata-rata", mode="lines",
            line=dict(color=s.MUTED, width=2),
            hovertemplate="%{y:,.1f} °C<extra>Suhu rata-rata</extra>"), row=3, col=1)
        s.style(fig, height=520, legend=False)
        # Ketiga panel memakai sumbu waktu yang sama supaya satu tooltip memuat ketiga nilainya.
        fig.update_traces(xaxis="x3")
        fig.update_layout(hoversubplots="axis", bargap=0.3, barcornerradius=2)
        ticks = pd.to_datetime(["2019-05-01", "2019-05-15", "2019-06-01", "2019-06-15",
                                "2019-07-01", "2019-07-15", "2019-07-31"])
        fig.update_xaxes(tickvals=ticks, ticktext=[f"{t.day} {s.MONTH_SHORT[t.month]}" for t in ticks],
                         hoverformat="%d/%m/%Y", showline=False, ticks="")
        fig.update_xaxes(showline=True, ticks="outside", row=3, col=1)
        fig.update_yaxes(title_text="Perjalanan", rangemode="tozero", tickformat=",", row=1, col=1)
        fig.update_yaxes(title_text="Hujan (mm)", rangemode="tozero", row=2, col=1)
        fig.update_yaxes(title_text="Suhu (°C)", row=3, col=1)
        s.show(fig, key="overview_daily")
        table = daily.rename(columns={"date": "Tanggal", "trips": "Perjalanan", "precip_mm": "Curah hujan (mm)",
                                      "temp_mean_c": "Suhu rata-rata (°C)", "temp_max_c": "Suhu tertinggi (°C)",
                                      "wind_mean_ms": "Angin rata-rata (m/s)"})
        table["Tanggal"] = table["Tanggal"].map(s.date_label)
        s.table_view(table, {"Perjalanan": "{:,.0f}", "Curah hujan (mm)": "{:,.1f}", "Suhu rata-rata (°C)": "{:,.1f}",
                             "Suhu tertinggi (°C)": "{:,.1f}", "Angin rata-rata (m/s)": "{:,.1f}"})

    # ---------------------------------------------------------- catatan data
    with st.expander("Tentang data dan batasannya"):
        months = ", ".join(f"{name} {s.num(count)}" for name, count in info["trips_by_month"].items())
        st.markdown(
            f"- **Perjalanan.** {s.num(info['trips_total'])} perjalanan Citi Bike di Jersey City ({months}). "
            "Waktu ditampilkan dalam waktu lokal New York.\n"
            f"- **Cakupan stasiun.** Grafik per stasiun memakai {info['stations_in_scope']} stasiun yang sama "
            "dengan cakupan model.\n"
            "- **Prediksi.** Yang diprediksi adalah jumlah peminjaman dan pengembalian per stasiun per jam, "
            "diuji pada Juli 2019. Angka ini adalah perjalanan yang tercatat, bukan stok sepeda dan bukan "
            "permintaan yang gagal dilayani.\n"
            "- **Cuaca.** Data ERA5 adalah rekonstruksi historis dengan satu titik untuk seluruh wilayah, "
            "bukan prakiraan yang tersedia sebelum jam prediksi.\n"
            f"- **Jaringan.** Graph memuat {s.num(info['graph_trips'])} perjalanan yang berangkat dan berakhir "
            f"di {info['stations_in_scope']} stasiun tersebut."
        )
