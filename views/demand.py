"""Halaman Pola aktivitas: kapan sepeda dipinjam dan dikembalikan."""
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import common
import data
import style as s

MONTHS = {0: "Mei–Juli", 5: "Mei", 6: "Juni", 7: "Juli"}


def render():
    hourly = data.hourly()

    st.title("Pola aktivitas")
    st.caption("Kapan sepeda dipinjam dan dikembalikan · 52 stasiun · Mei–Juli 2019 · waktu lokal New York")

    # ------------------------------------------- filter (berlaku untuk semua grafik)
    left, right = st.columns([2, 3])
    with left:
        station = data.station_picker("demand_station")
    with right:
        month = st.segmented_control("Bulan", list(MONTHS), format_func=MONTHS.get, default=0,
                                     required=True, key="demand_month")
    months = [5, 6, 7] if month == 0 else [month]

    common.insight_box("demand")

    part = hourly[hourly["month"].isin(months)]
    if station:
        part = part[part["station_id"] == station]
    scope = data.station_name(station) if station else "52 stasiun"

    # Satu baris per jam kalender: jumlah seluruh stasiun yang dipilih.
    by_hour = part.groupby(["hour_local", "date", "hour", "dow"], as_index=False)[s.TARGETS].sum()
    if by_hour.empty:
        st.info("Stasiun ini belum punya data pada bulan terpilih.")
        return
    n_days = by_hour["date"].nunique()
    total_dep, total_arr = int(by_hour["departures"].sum()), int(by_hour["arrivals"].sum())

    # ---------------------------------------------------------- angka utama
    tiles = st.columns(4)
    tiles[0].metric("Peminjaman", s.num(total_dep), border=True, height="stretch",
                    help="Perjalanan yang berangkat dari stasiun terpilih.")
    tiles[1].metric("Pengembalian", s.num(total_arr), border=True, height="stretch",
                    help="Perjalanan yang berakhir di stasiun terpilih.")
    tiles[2].metric("Pengembalian − peminjaman", s.signed(total_arr - total_dep), border=True, height="stretch",
                    help="Positif berarti lebih banyak sepeda yang datang daripada yang pergi. "
                         "Ini selisih arus perjalanan, bukan jumlah stok sepeda.")
    tiles[3].metric("Rata-rata peminjaman per hari", s.num(total_dep / n_days, 1), border=True, height="stretch",
                    help=f"Dihitung dari {n_days} hari pada bulan terpilih.")

    # ------------------------------------- profil 24 jam: hari kerja vs akhir pekan
    with s.card(f"Rata-rata perjalanan per jam dalam sehari · {scope}",
                "Rata-rata jumlah perjalanan yang dimulai (peminjaman) atau berakhir (pengembalian) pada tiap jam."):
        profile = (by_hour.assign(weekend=by_hour["dow"] >= 5)
                   .groupby(["weekend", "hour"], as_index=False)[s.TARGETS].mean())
        fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
                            subplot_titles=["Hari kerja (Senin–Jumat)", "Akhir pekan (Sabtu–Minggu)"])
        for col, weekend in enumerate([False, True], start=1):
            rows = profile[profile["weekend"] == weekend]
            for target in s.TARGETS:
                fig.add_trace(go.Scatter(
                    x=[s.HOURS[h] for h in rows["hour"]], y=rows[target], mode="lines",
                    name=s.TARGET_LABEL[target], legendgroup=target, showlegend=(col == 1),
                    line=dict(color=s.TARGET_COLOR[target], width=2),
                    hovertemplate="%{y:,.1f}<extra>" + s.TARGET_LABEL[target] + "</extra>"), row=1, col=col)
        s.style(fig, height=340)
        fig.update_layout(margin_t=64, legend_y=1.16)
        fig.update_annotations(font=dict(size=13, color=s.INK_2), xanchor="left", xref="x domain", x=0)
        fig.update_annotations(selector=dict(text="Akhir pekan (Sabtu–Minggu)"), xref="x2 domain")
        fig.update_xaxes(type="category", tickvals=s.HOURS[::3], title_text="Jam mulai")
        fig.update_yaxes(rangemode="tozero")
        fig.update_yaxes(title_text="Perjalanan per jam", col=1)
        s.show(fig, key="demand_profile")
        table = profile.assign(Hari=profile["weekend"].map({False: "Hari kerja", True: "Akhir pekan"}),
                               Jam=profile["hour"].map(s.hour_label))
        table = table.rename(columns={"departures": "Peminjaman", "arrivals": "Pengembalian"})
        s.table_view(table[["Hari", "Jam", "Peminjaman", "Pengembalian"]],
                     {"Peminjaman": "{:,.1f}", "Pengembalian": "{:,.1f}"})

    # -------------------------------------------- heatmap hari x jam, dua arah
    with s.card(f"Rata-rata perjalanan per jam menurut hari dan jam · {scope}",
                "Makin gelap makin ramai. Kedua panel memakai skala warna yang sama."):
        grid = by_hour.groupby(["dow", "hour"])[s.TARGETS].mean()
        zmax = float(grid.max().max())
        fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.03,
                            subplot_titles=[s.TARGET_LABEL[t] for t in s.TARGETS])
        for col, target in enumerate(s.TARGETS, start=1):
            matrix = grid[target].unstack("hour").reindex(index=range(7), columns=range(24))
            fig.add_trace(go.Heatmap(
                z=matrix.values, x=s.HOURS, y=s.DAY_NAMES, zmin=0, zmax=zmax, colorscale=s.SEQUENTIAL,
                xgap=2, ygap=2, showscale=(col == 2),
                colorbar=dict(title=dict(text="per jam", font=dict(size=12, color=s.INK_2)), thickness=10,
                              len=0.9, outlinewidth=0, tickfont=dict(color=s.MUTED, size=12)),
                hovertemplate="%{y}, mulai %{x}<br><b>%{z:,.1f}</b> perjalanan per jam<extra>"
                              + s.TARGET_LABEL[target] + "</extra>"), row=1, col=col)
        s.style(fig, height=330, legend=False, hovermode="closest")
        fig.update_layout(margin_t=40)
        fig.update_annotations(font=dict(size=13, color=s.INK_2), xanchor="left", xref="x domain", x=0)
        fig.update_annotations(selector=dict(text=s.TARGET_LABEL["arrivals"]), xref="x2 domain")
        fig.update_xaxes(type="category", tickvals=s.HOURS[::3], showline=False, ticks="", title_text="Jam mulai")
        fig.update_yaxes(autorange="reversed", showgrid=False)
        s.show(fig, key="demand_heatmap")
        table = grid.reset_index()
        table["Hari"] = table["dow"].map(lambda d: s.DAY_NAMES[d])
        table["Jam"] = table["hour"].map(s.hour_label)
        table = table.rename(columns={"departures": "Peminjaman", "arrivals": "Pengembalian"})
        s.table_view(table[["Hari", "Jam", "Peminjaman", "Pengembalian"]],
                     {"Peminjaman": "{:,.1f}", "Pengembalian": "{:,.1f}"})

    st.caption("Jam tanpa perjalanan tercatat dihitung nol. Angka di halaman ini adalah perjalanan yang tercatat, "
               "bukan stok sepeda dan bukan permintaan yang gagal dilayani.")
