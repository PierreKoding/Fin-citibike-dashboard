"""Halaman Hasil prediksi: tiga pendekatan dibandingkan dengan jumlah aktual (Juli 2019)."""
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import common
import data
import style as s

TEST_START, TEST_END = date(2019, 7, 1), date(2019, 7, 31)
TOP_STATIONS = 15


def metrics(frame: pd.DataFrame) -> pd.DataFrame:
    """MAE dan RMSE tiap pendekatan untuk sekumpulan baris stasiun-jam."""
    rows = []
    for variant in s.VARIANTS:
        error = frame[variant] - frame["actual"]
        rows.append({"variant": variant, "mae": error.abs().mean(), "rmse": np.sqrt((error ** 2).mean())})
    return pd.DataFrame(rows).set_index("variant")


def render():
    pred = data.predictions()

    st.title("Hasil prediksi")
    st.caption("Prediksi satu jam ke depan dibandingkan jumlah aktual · data uji Juli 2019 · 52 stasiun")

    # ------------------------------------------- filter (berlaku untuk semua grafik)
    c1, c2, c3 = st.columns(3)
    target = c1.segmented_control("Jenis aktivitas", s.TARGETS, format_func=s.TARGET_LABEL.get,
                                  default="departures", required=True, key="model_target")
    with c2:
        station = data.station_picker("model_station")
    picked = c3.date_input("Rentang tanggal", value=(TEST_START, TEST_END), min_value=TEST_START,
                           max_value=TEST_END, format="DD/MM/YYYY", key="model_dates")
    start, end = (picked[0], picked[-1]) if isinstance(picked, (tuple, list)) and picked else (TEST_START, TEST_END)

    common.insight_box("model")

    in_range = pred[(pred["target"] == target)
                    & (pred["date"] >= pd.Timestamp(start)) & (pred["date"] <= pd.Timestamp(end))]
    part = in_range[in_range["station_id"] == station] if station else in_range
    scope = data.station_name(station) if station else "52 stasiun"
    label = s.TARGET_LABEL[target].lower()
    result = metrics(part)
    base = result.loc["baseline_minggu_lalu"]

    # ---------------------------------------------------------- angka utama
    st.markdown(f"**Rata-rata selisih prediksi {label} (MAE)** · perjalanan per stasiun per jam · "
                "lebih kecil lebih baik")
    tiles = st.columns(4)
    for tile, variant in zip(tiles, s.VARIANTS):
        value = result.loc[variant, "mae"]
        extra = {}
        if variant != "baseline_minggu_lalu" and base["mae"] > 0:
            change = (value / base["mae"] - 1) * 100
            extra = dict(delta=f"{change:.1f}%".replace(".", ","), delta_color="inverse",
                         delta_description="dibanding baseline")
        tile.metric(s.VARIANT_LABEL[variant], s.num(value, 2), border=True, height="stretch", **extra)
    tiles[3].metric("Jam tanpa perjalanan", s.pct((part["actual"] == 0).mean() * 100), border=True, height="stretch",
                    help=f"Bagian dari {s.num(len(part))} pengamatan stasiun-jam yang jumlah aktualnya nol. "
                         "Banyaknya jam sepi ikut menurunkan rata-rata selisih.")

    # ------------------------------------------- MAE dan RMSE tiga pendekatan
    with s.card(f"Selisih prediksi menurut pendekatan · {label} · {scope}",
                "MAE = rata-rata selisih. RMSE memberi bobot lebih besar pada selisih yang besar. "
                "Satuan: perjalanan per stasiun per jam."):
        fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.06,
                            subplot_titles=["MAE", "RMSE"])
        names = [s.VARIANT_LABEL[v] for v in s.VARIANTS]
        for col, metric in enumerate(["mae", "rmse"], start=1):
            values = [result.loc[v, metric] for v in s.VARIANTS]
            fig.add_trace(go.Bar(
                y=names, x=values, orientation="h", marker_color=[s.VARIANT_COLOR[v] for v in s.VARIANTS],
                text=[s.pad(s.num(v, 2)) for v in values], textposition="outside", cliponaxis=False,
                textfont=dict(color=s.INK, size=13),
                hovertemplate="%{y}: <b>%{x:,.4f}</b><extra>" + metric.upper() + "</extra>"), row=1, col=col)
            fig.update_xaxes(range=[0, max(max(values), 0.01) * 1.18], row=1, col=col)
        s.style(fig, height=210, legend=False, hovermode="closest")
        fig.update_layout(margin_t=36, bargap=0.55)
        fig.update_annotations(font=dict(size=13, color=s.INK_2), xanchor="left", xref="x domain", x=0)
        fig.update_annotations(selector=dict(text="RMSE"), xref="x2 domain")
        fig.update_xaxes(showgrid=True, gridcolor=s.GRID, showline=False, ticks="")
        fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=s.INK_2, size=13))
        s.show(fig, key="model_metrics")
        table = result.reset_index()
        table["Pendekatan"] = table["variant"].map(s.VARIANT_LABEL)
        table = table.rename(columns={"mae": "MAE", "rmse": "RMSE"})
        s.table_view(table[["Pendekatan", "MAE", "RMSE"]], {"MAE": "{:,.4f}", "RMSE": "{:,.4f}"})

    # ------------------------------------------------ aktual vs prediksi per jam
    note = ("Jumlah seluruh 52 stasiun pada tiap jam. Pada jumlah gabungan, selisih antarstasiun dapat saling "
            "menutupi; pilih satu stasiun untuk melihat prediksi di tingkat stasiun."
            if not station else "Tiap garis adalah jumlah perjalanan per jam di stasiun ini.")
    note += " Tampilan awal memperlihatkan paling banyak tujuh hari; geser bilah di bawah grafik untuk tanggal lain."
    with s.card(f"Aktual dan prediksi {label} per jam · {scope}", note):
        series = part.groupby("hour_local")[["actual"] + s.VARIANTS].sum()
        fig = go.Figure()
        for rank, variant in enumerate(s.VARIANTS):
            fig.add_trace(go.Scatter(
                x=series.index, y=series[variant], mode="lines", name=s.VARIANT_LABEL[variant],
                line=dict(color=s.VARIANT_COLOR[variant], width=1.5), legendrank=rank + 2,
                hovertemplate="%{y:,.1f}<extra>" + s.VARIANT_LABEL[variant] + "</extra>"))
        fig.add_trace(go.Scatter(
            x=series.index, y=series["actual"], mode="lines", name="Aktual", legendrank=1,
            line=dict(color=s.INK, width=2), hovertemplate="%{y:,.0f}<extra>Aktual</extra>"))
        s.style(fig, height=400)
        fig.update_xaxes(
            hoverformat="%d/%m/%Y %H.%M",
            tickformatstops=[dict(dtickrange=[None, 86_399_999], value="%H.%M<br>%d/%m"),
                             dict(dtickrange=[86_400_000, None], value="%d/%m")],
            rangeslider=dict(visible=True, thickness=0.07, bgcolor=s.NEUTRAL))
        fig.update_yaxes(title_text="Perjalanan per jam", rangemode="tozero")
        first, last = series.index.min(), series.index.max()
        if last - first > pd.Timedelta(days=7):      # tampilan awal: tujuh hari pertama
            fig.update_xaxes(range=[first, first + pd.Timedelta(days=7)])
        s.show(fig, key="model_series")
        table = series.reset_index().rename(columns={"hour_local": "Jam mulai", "actual": "Aktual",
                                                     **s.VARIANT_LABEL})
        table["Jam mulai"] = table["Jam mulai"].dt.strftime("%d/%m/%Y %H.%M")
        s.table_view(table, {name: "{:,.1f}" for name in ["Aktual"] + list(s.VARIANT_LABEL.values())})

    # ------------------------------------------------ selisih menurut jam
    with s.card(f"Selisih prediksi {label} menurut jam dalam sehari · {scope}",
                "Atas: rata-rata selisih prediksi (MAE) tiap pendekatan. "
                "Bawah: rata-rata jumlah aktual per stasiun pada jam yang sama."):
        by_hour = pd.DataFrame({v: (part[v] - part["actual"]).abs().groupby(part["hour"]).mean() for v in s.VARIANTS})
        by_hour["actual"] = part.groupby("hour")["actual"].mean()
        by_hour = by_hour.reindex(range(24))
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.66, 0.34])
        for variant in s.VARIANTS:
            fig.add_trace(go.Scatter(
                x=s.HOURS, y=by_hour[variant], mode="lines", name=s.VARIANT_LABEL[variant],
                line=dict(color=s.VARIANT_COLOR[variant], width=2),
                hovertemplate="%{y:,.2f}<extra>" + s.VARIANT_LABEL[variant] + "</extra>"), row=1, col=1)
        fig.add_trace(go.Bar(
            x=s.HOURS, y=by_hour["actual"], name="Rata-rata aktual", marker_color=s.MUTED, showlegend=False,
            hovertemplate="%{y:,.2f}<extra>Rata-rata aktual</extra>"), row=2, col=1)
        s.style(fig, height=430)
        fig.update_traces(xaxis="x2")      # satu sumbu jam untuk kedua panel -> satu tooltip
        fig.update_layout(hoversubplots="axis", bargap=0.55)
        fig.update_xaxes(type="category", tickvals=s.HOURS[::3], showline=False, ticks="")
        fig.update_xaxes(title_text="Jam mulai", showline=True, ticks="outside", row=2, col=1)
        fig.update_yaxes(title_text="MAE", rangemode="tozero", row=1, col=1)
        fig.update_yaxes(title_text="Aktual", rangemode="tozero", row=2, col=1)
        s.show(fig, key="model_by_hour")
        table = by_hour.reset_index().rename(columns={"hour": "Jam", "actual": "Rata-rata aktual", **s.VARIANT_LABEL})
        table["Jam"] = table["Jam"].map(s.hour_label)
        s.table_view(table[["Jam", "Rata-rata aktual"] + list(s.VARIANT_LABEL.values())],
                     {name: "{:,.2f}" for name in ["Rata-rata aktual"] + list(s.VARIANT_LABEL.values())})

    # ------------------------------------------------ selisih per stasiun
    with s.card(f"Selisih prediksi {label} per stasiun · {TOP_STATIONS} stasiun tersibuk",
                "Tiap baris satu stasiun, diurutkan dari yang paling ramai. Titik menunjukkan MAE tiap pendekatan; "
                "makin ke kiri makin kecil selisihnya. Grafik ini selalu menampilkan semua stasiun tersibuk; "
                "stasiun yang dipilih ditebalkan."):
        errors = {v: (in_range[v] - in_range["actual"]).abs() for v in s.VARIANTS}
        per_station = pd.DataFrame(errors).groupby(in_range["station_id"]).mean()
        per_station["actual_mean"] = in_range.groupby("station_id")["actual"].mean()
        per_station = per_station.join(data.stations().set_index("station_id")["station_name"])
        per_station = per_station.sort_values("actual_mean", ascending=False)
        shown = per_station.head(TOP_STATIONS)
        if station and station not in shown.index:
            shown = pd.concat([shown, per_station.loc[[station]]])
        labels = [f"<b>{name}</b>" if sid == station else name
                  for sid, name in zip(shown.index, shown["station_name"])]
        fig = go.Figure()
        span_x, span_y = [], []
        for label_text, low, high in zip(labels, shown[s.VARIANTS].min(axis=1), shown[s.VARIANTS].max(axis=1)):
            span_x += [low, high, None]
            span_y += [label_text, label_text, None]
        fig.add_trace(go.Scatter(x=span_x, y=span_y, mode="lines", line=dict(color=s.AXIS, width=2),
                                 hoverinfo="skip", showlegend=False))
        for variant in s.VARIANTS:
            fig.add_trace(go.Scatter(
                x=shown[variant], y=labels, mode="markers", name=s.VARIANT_LABEL[variant],
                marker=dict(color=s.VARIANT_COLOR[variant], size=11, line=dict(color=s.SURFACE, width=2)),
                hovertemplate="%{x:,.2f}<extra>" + s.VARIANT_LABEL[variant] + "</extra>"))
        s.style(fig, height=64 + 26 * len(shown), hovermode="y unified")
        fig.update_xaxes(title_text="MAE (perjalanan per jam)", rangemode="tozero", showgrid=True,
                         gridcolor=s.GRID, showline=False, ticks="")
        fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=s.INK_2, size=13))
        s.show(fig, key="model_by_station")
        table = per_station.reset_index().rename(columns={"station_name": "Stasiun", "station_id": "ID",
                                                          "actual_mean": "Rata-rata aktual per jam",
                                                          **s.VARIANT_LABEL})
        s.table_view(table[["Stasiun", "ID", "Rata-rata aktual per jam"] + list(s.VARIANT_LABEL.values())],
                     {name: "{:,.2f}" for name in ["Rata-rata aktual per jam"] + list(s.VARIANT_LABEL.values())},
                     label="Lihat semua 52 stasiun sebagai tabel")

    st.caption(
        "Baseline minggu lalu = jumlah pada stasiun dan jam yang sama seminggu sebelumnya. Kedua model adalah "
        "Gradient-Boosted Trees (Spark MLlib) dengan fitur stasiun, kalender, dan riwayat aktivitas; model dengan "
        "cuaca menambah suhu, kelembapan, angin, dan hujan ERA5 pada jam target, yaitu nilai yang sudah diketahui "
        "dalam data historis dan belum tentu tersedia saat prediksi langsung. Yang diprediksi adalah jumlah "
        "perjalanan, bukan stok sepeda. Hasil berlaku untuk Juli 2019 dengan satu pembagian waktu."
    )
