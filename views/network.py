"""Halaman Jaringan stasiun: hasil graph analytics (node = stasiun, edge = asal -> tujuan)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common
import data
import style as s

TOP_BARS = 15


def undirected_routes(edges: pd.DataFrame) -> pd.DataFrame:
    """Gabungkan dua arah (A->B dan B->A) menjadi satu rute untuk digambar di peta."""
    routes = edges[edges["src"] != edges["dst"]].copy()
    forward = routes["src"] < routes["dst"]
    routes["a"] = np.where(forward, routes["src"], routes["dst"])
    routes["b"] = np.where(forward, routes["dst"], routes["src"])
    routes["a_to_b"] = np.where(forward, routes["weight"], 0)
    routes["b_to_a"] = np.where(forward, 0, routes["weight"])
    out = routes.groupby(["a", "b"], as_index=False)[["a_to_b", "b_to_a"]].sum()
    out["total"] = out["a_to_b"] + out["b_to_a"]
    return out


def station_map(nodes, routes, selected, basemap):
    """Peta: lingkaran = stasiun, garis = rute tersibuk."""
    place = nodes.set_index("station_id")
    fig = go.Figure()

    # Garis rute. Plotly memakai satu ketebalan per trace, jadi rute dikelompokkan per ketebalan.
    if len(routes):
        routes = routes.assign(width=np.round(1 + 6 * np.sqrt(routes["total"] / routes["total"].max())))
        for width, group in routes.groupby("width"):
            lats, lons = [], []
            for row in group.itertuples():
                lats += [place.at[row.a, "lat"], place.at[row.b, "lat"], None]
                lons += [place.at[row.a, "lon"], place.at[row.b, "lon"], None]
            fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="lines", hoverinfo="skip", showlegend=False,
                                        line=dict(color="rgba(82,81,78,0.55)", width=float(width))))
        # Titik tak terlihat di tengah garis supaya rute punya tooltip.
        fig.add_trace(go.Scattermap(
            lat=[(place.at[r.a, "lat"] + place.at[r.b, "lat"]) / 2 for r in routes.itertuples()],
            lon=[(place.at[r.a, "lon"] + place.at[r.b, "lon"]) / 2 for r in routes.itertuples()],
            mode="markers", marker=dict(size=14, color=s.INK_2, opacity=0), showlegend=False,
            text=[f"<b>{place.at[r.a, 'station_name']} ↔ {place.at[r.b, 'station_name']}</b><br>"
                  f"{s.num(r.total)} perjalanan<br>"
                  f"{place.at[r.a, 'station_name']} → {place.at[r.b, 'station_name']}: {s.num(r.a_to_b)}<br>"
                  f"{place.at[r.b, 'station_name']} → {place.at[r.a, 'station_name']}: {s.num(r.b_to_a)}"
                  for r in routes.itertuples()],
            hovertemplate="%{text}<extra></extra>"))

    # Lingkaran stasiun: diameter mengikuti akar total aktivitas (luas sebanding dengan aktivitas).
    size = 8 + 34 * np.sqrt(nodes["total_activity"] / nodes["total_activity"].max())
    is_selected = nodes["station_id"] == selected
    # Skala warna dibatasi supaya stasiun selain yang paling ekstrem tetap terbedakan;
    # nilai di luar batas memakai warna paling pekat.
    limit = float(np.ceil(nodes["net_flow"].abs().nlargest(2).iloc[-1] / 100) * 100)
    fig.add_trace(go.Scattermap(           # cincin gelap di belakang supaya lingkaran pucat tetap terlihat
        lat=nodes["lat"], lon=nodes["lon"], mode="markers", hoverinfo="skip", showlegend=False,
        marker=dict(size=size + np.where(is_selected, 9, 3), color=np.where(is_selected, s.INK, s.INK_2), opacity=1)))
    fig.add_trace(go.Scattermap(
        lat=nodes["lat"], lon=nodes["lon"], mode="markers", showlegend=False,
        marker=dict(size=size, color=nodes["net_flow"].clip(-limit, limit), colorscale=s.DIVERGING,
                    cmin=-limit, cmax=limit, opacity=1,
                    colorbar=dict(title=dict(text="Masuk − keluar", font=dict(size=12, color=s.INK_2)),
                                  tickvals=[-limit, 0, limit],
                                  ticktext=[f"≤ −{s.num(limit)}", "0", f"≥ +{s.num(limit)}"],
                                  thickness=10, len=0.5, outlinewidth=0,
                                  tickfont=dict(color=s.INK_2, size=12))),
        text=[f"<b>{r.label}</b><br>Keluar {s.num(r.out_strength)} · Masuk {s.num(r.in_strength)}<br>"
              f"Masuk − keluar {s.signed(r.net_flow)}<br>Total aktivitas {s.num(r.total_activity)}"
              for r in nodes.itertuples()],
        hovertemplate="%{text}<extra></extra>"))

    s.style(fig, height=560, legend=False, hovermode="closest")
    # Tanpa center/zoom, Plotly menyesuaikan tampilan peta dengan sebaran titik stasiun.
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0),
                      map=dict(style="carto-positron" if basemap else "white-bg"))
    return fig


def ranked_bars(names, values, color, height=None):
    """Batang mendatar berurutan dengan nilai di ujung batang."""
    if not values:
        return None
    fig = go.Figure(go.Bar(
        y=names, x=values, orientation="h", marker_color=color,
        text=[s.pad(s.num(v)) for v in values], textposition="outside", cliponaxis=False,
        textfont=dict(color=s.INK, size=12), hovertemplate="%{y}: <b>%{x:,.0f}</b> perjalanan<extra></extra>"))
    s.style(fig, height=height or 56 + 26 * len(names), legend=False, hovermode="closest")
    fig.update_xaxes(range=[0, max(values) * 1.15], tickformat=",", showgrid=True, gridcolor=s.GRID, showline=False,
                     ticks="")
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=s.INK_2, size=12))
    return fig


def render():
    nodes, edges = data.graph()
    info = data.summary()

    st.title("Jaringan stasiun")
    st.caption(f"Hubungan perjalanan antarstasiun · {len(nodes)} stasiun · {s.num(info['graph_trips'])} perjalanan · "
               "1 Mei – 31 Juli 2019")

    # ------------------------------------------- filter (berlaku untuk semua grafik)
    left, middle, right = st.columns([2, 2, 1], vertical_alignment="bottom")
    with left:
        station = data.station_picker("network_station")
    n_routes = middle.slider("Jumlah rute pada peta", 10, 60, 25, step=5, key="network_routes")
    # Peta jalan diambil dari server peta (CARTO) oleh browser; matikan jika peta tidak muncul.
    basemap = right.toggle("Peta jalan", value=True, key="network_basemap")

    common.insight_box("network")

    routes = undirected_routes(edges)
    directed = edges[edges["src"] != edges["dst"]]

    # ---------------------------------------------------------- angka utama
    tiles = st.columns(4)
    if station:
        node = nodes.set_index("station_id").loc[station]
        loops = int(edges.loc[(edges["src"] == station) & (edges["dst"] == station), "weight"].sum())
        tiles[0].metric("Perjalanan keluar", s.num(node["out_strength"]), border=True, height="stretch",
                        help=f"Termasuk {s.num(loops)} perjalanan yang kembali ke stasiun ini.")
        tiles[1].metric("Perjalanan masuk", s.num(node["in_strength"]), border=True, height="stretch",
                        help=f"Termasuk {s.num(loops)} perjalanan yang kembali ke stasiun ini.")
        tiles[2].metric("Masuk − keluar", s.signed(node["net_flow"]), border=True, height="stretch",
                        help="Selisih arus perjalanan selama tiga bulan, bukan jumlah stok sepeda.")
        tiles[3].metric("Stasiun tujuan / asal", f"{node['out_degree']} / {node['in_degree']}", border=True,
                        height="stretch",
                        help=f"Jumlah stasiun lain yang menjadi tujuan dan asal perjalanan stasiun ini, "
                             f"dari {len(nodes) - 1} stasiun lain dalam jaringan.")
        routes = routes[(routes["a"] == station) | (routes["b"] == station)]
    else:
        tiles[0].metric("Stasiun", s.num(len(nodes)), border=True, height="stretch")
        tiles[1].metric("Perjalanan dalam jaringan", s.num(info["graph_trips"]), border=True, height="stretch",
                        help="Perjalanan yang berangkat dan berakhir di 52 stasiun ini.")
        tiles[2].metric("Rute berarah", s.num(info["graph_edges"]), border=True, height="stretch",
                        help="Pasangan asal → tujuan yang punya minimal satu perjalanan.")
        tiles[3].metric("Kembali ke stasiun asal", s.num(info["graph_self_loop_trips"]), border=True, height="stretch",
                        help="Perjalanan yang berangkat dan berakhir di stasiun yang sama.")
    top_routes = routes.nlargest(n_routes, "total")

    # ------------------------------------------------------ peta dan rute
    map_col, bar_col = st.columns([3, 2])
    with map_col:
        with s.card("Peta stasiun dan rute tersibuk",
                    f"Lingkaran: ukuran = total aktivitas, warna = selisih masuk − keluar. Garis: {len(top_routes)} rute "
                    "tersibuk (dua arah digabung), makin tebal makin banyak perjalanan."):
            s.show(station_map(nodes, top_routes, station, basemap), key="network_map", scroll_zoom=True)
    with bar_col:
        if station:
            name = data.station_name(station)
            out_edges = directed[directed["src"] == station].nlargest(8, "weight")
            in_edges = directed[directed["dst"] == station].nlargest(8, "weight")
            for title, rows, column, color, key in [
                (f"Tujuan terbanyak dari {name}", out_edges, "dst_name", s.GREEN, "network_out"),
                (f"Asal terbanyak menuju {name}", in_edges, "src_name", s.VIOLET, "network_in"),
            ]:
                with s.card(title):
                    fig = ranked_bars(rows[column].tolist(), rows["weight"].tolist(), color, 250)
                    if fig is None:
                        st.caption("Tidak ada perjalanan ke atau dari stasiun lain.")
                    else:
                        s.show(fig, key=key)
        else:
            busiest = directed.nlargest(TOP_BARS, "weight")
            with s.card(f"{TOP_BARS} rute tersibuk (asal → tujuan)",
                        "Tiap arah dihitung terpisah."):
                names = (busiest["src_name"] + " → " + busiest["dst_name"]).tolist()
                s.show(ranked_bars(names, busiest["weight"].tolist(), s.ACCENT, 500), key="network_routes_bar")

    # ------------------------------------- aktivitas dan selisih per stasiun
    left, right = st.columns(2)
    with left:
        with s.card(f"Total aktivitas per stasiun · {TOP_BARS} teratas",
                    "Panjang batang = perjalanan keluar + masuk selama tiga bulan."):
            top = nodes.nlargest(TOP_BARS, "total_activity")
            fig = go.Figure()
            for column, name, color in [("out_strength", "Keluar", s.GREEN), ("in_strength", "Masuk", s.VIOLET)]:
                fig.add_trace(go.Bar(y=top["station_name"], x=top[column], orientation="h", name=name,
                                     marker=dict(color=color, line=dict(color=s.SURFACE, width=2)),
                                     hovertemplate="%{x:,.0f}<extra>" + name + "</extra>"))
            fig.add_trace(go.Scatter(y=top["station_name"], x=top["total_activity"], mode="text",
                                     text=[s.pad(s.num(v)) for v in top["total_activity"]], textposition="middle right",
                                     textfont=dict(color=s.INK, size=12), hoverinfo="skip", showlegend=False,
                                     cliponaxis=False))
            s.style(fig, height=92 + 26 * len(top), hovermode="y unified")
            fig.update_layout(barmode="stack", barcornerradius=0, legend_traceorder="normal")
            fig.update_xaxes(range=[0, top["total_activity"].max() * 1.15], tickformat=",", showgrid=True,
                             gridcolor=s.GRID, showline=False, ticks="")
            fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=s.INK_2, size=12))
            s.show(fig, key="network_activity")
    with right:
        with s.card(f"Selisih masuk − keluar per stasiun · {TOP_BARS} selisih terbesar",
                    "Kanan (ungu) = lebih banyak perjalanan masuk; kiri (hijau) = lebih banyak perjalanan keluar. "
                    "Ini selisih arus perjalanan, bukan jumlah stok sepeda."):
            order = nodes["net_flow"].abs().nlargest(TOP_BARS).index
            net = nodes.loc[order].sort_values("net_flow", ascending=False)
            fig = go.Figure(go.Bar(
                y=net["station_name"], x=net["net_flow"], orientation="h",
                marker_color=np.where(net["net_flow"] >= 0, s.VIOLET, s.GREEN),
                text=[s.pad(s.signed(v)) + "\u00a0" for v in net["net_flow"]], textposition="outside", cliponaxis=False,
                textfont=dict(color=s.INK, size=12),
                hovertemplate="%{y}: <b>%{x:+,.0f}</b><extra></extra>"))
            s.style(fig, height=92 + 26 * len(net), legend=False, hovermode="closest")
            span = net["net_flow"].abs().max() * 1.2
            fig.update_xaxes(range=[-span * 0.45, span], tickformat=",", showgrid=True, gridcolor=s.GRID, showline=False,
                             ticks="",
                             zeroline=True, zerolinecolor=s.AXIS, zerolinewidth=1)
            fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=s.INK_2, size=12))
            s.show(fig, key="network_net")

    table = nodes.sort_values("total_activity", ascending=False).rename(columns={
        "station_name": "Stasiun", "station_id": "ID", "out_strength": "Keluar", "in_strength": "Masuk",
        "total_activity": "Total aktivitas", "net_flow": "Masuk − keluar",
        "out_degree": "Jumlah stasiun tujuan", "in_degree": "Jumlah stasiun asal"})
    s.table_view(table[["Stasiun", "ID", "Keluar", "Masuk", "Total aktivitas", "Masuk − keluar",
                        "Jumlah stasiun tujuan", "Jumlah stasiun asal"]],
                 {"Keluar": "{:,.0f}", "Masuk": "{:,.0f}", "Total aktivitas": "{:,.0f}", "Masuk − keluar": "{:+,.0f}"},
                 label="Lihat semua 52 stasiun sebagai tabel")

    st.caption("Graph memuat perjalanan yang berangkat dan berakhir di 52 stasiun dalam cakupan analisis dan selesai "
               "sebelum 1 Agustus 2019. Selisih masuk − keluar belum menunjukkan jumlah sepeda yang tersedia atau "
               "yang perlu dipindahkan; itu memerlukan data stok awal, kapasitas stasiun, dan pemindahan oleh operator.")
