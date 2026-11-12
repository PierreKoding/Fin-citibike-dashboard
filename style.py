"""Warna, format angka, dan gaya grafik yang dipakai semua halaman.

Aturan warna (supaya konsisten di seluruh dashboard):
  - satu seri            -> biru (ACCENT)
  - tiga pendekatan      -> abu-abu / biru / oranye (sama dengan Gambar 5.2 laporan)
  - peminjaman vs pengembalian -> hijau / ungu
  - besaran (heatmap)    -> satu warna, makin gelap makin besar
  - selisih masuk-keluar -> ungu (lebih banyak masuk) dan hijau (lebih banyak keluar),
                            abu-abu netral di tengah; sama dengan warna
                            pengembalian (masuk) dan peminjaman (keluar)
"""
from contextlib import contextmanager

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------ warna
SURFACE = "#fcfcfb"
INK = "#0b0b0b"        # teks utama
INK_2 = "#52514e"      # teks sekunder
MUTED = "#898781"      # label sumbu
GRID = "#e1e0d9"       # garis bantu tipis
AXIS = "#c3c2b7"       # garis sumbu

BLUE = "#2a78d6"
ORANGE = "#eb6834"
GREEN = "#008300"
VIOLET = "#6250d6"
NEUTRAL = "#f0efec"
ACCENT = BLUE

VARIANTS = ["baseline_minggu_lalu", "tanpa_cuaca", "dengan_cuaca"]
VARIANT_LABEL = {
    "baseline_minggu_lalu": "Baseline minggu lalu",
    "tanpa_cuaca": "Model tanpa cuaca",
    "dengan_cuaca": "Model dengan cuaca",
}
VARIANT_COLOR = {"baseline_minggu_lalu": MUTED, "tanpa_cuaca": BLUE, "dengan_cuaca": ORANGE}

TARGETS = ["departures", "arrivals"]
TARGET_LABEL = {"departures": "Peminjaman", "arrivals": "Pengembalian"}
TARGET_COLOR = {"departures": GREEN, "arrivals": VIOLET}

# Satu warna dari terang ke gelap untuk besaran.
SEQUENTIAL = [
    [0.00, "#e9f1fc"], [0.15, "#cde2fb"], [0.30, "#9ec5f4"], [0.45, "#6da7ec"],
    [0.60, "#3987e5"], [0.75, "#256abf"], [0.90, "#184f95"], [1.00, "#0d366b"],
]
# Dua warna berlawanan dengan titik tengah netral: negatif = lebih banyak keluar
# (hijau, warna peminjaman), positif = lebih banyak masuk (ungu, warna pengembalian).
DIVERGING = [[0.0, GREEN], [0.5, NEUTRAL], [1.0, VIOLET]]

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
DAY_SHORT = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
MONTH_SHORT = {5: "Mei", 6: "Jun", 7: "Jul", 8: "Agu"}


# ---------------------------------------------------------- format angka
def num(value, decimals=0):
    """Format Indonesia: titik untuk ribuan, koma untuk desimal (119.311 / 0,82)."""
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def signed(value, decimals=0):
    """Angka dengan tanda plus/minus, misalnya +3.324 atau −466."""
    sign = "+" if value > 0 else ("−" if value < 0 else "")
    return f"{sign}{num(abs(value), decimals)}"


def pct(value, decimals=1):
    return f"{num(value, decimals)}%"


def date_label(ts):
    """Contoh: Sen, 1 Jul 2019"""
    ts = pd.Timestamp(ts)
    return f"{DAY_SHORT[ts.dayofweek]}, {ts.day} {MONTH_SHORT[ts.month]} {ts.year}"


HOURS = [f"{h:02d}.00" for h in range(24)]     # label sumbu jam: 00.00 ... 23.00


def pad(text):
    """Beri jarak kecil antara ujung batang dan angkanya."""
    return "\u00a0" + text


def hour_label(hour):
    """Contoh: 08.00–09.00"""
    return f"{int(hour):02d}.00–{(int(hour) + 1) % 24:02d}.00"


# ---------------------------------------------------------- gaya grafik
def style(fig, height=320, legend=True, hovermode="x unified"):
    """Gaya dasar: latar polos, garis bantu tipis, legenda di atas kiri."""
    fig.update_layout(
        template="none",
        height=height,
        margin=dict(l=8, r=16, t=36 if legend else 12, b=8),
        font=dict(family=FONT, size=13, color=INK_2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        separators=",.",
        hovermode=hovermode,
        hoverlabel=dict(bgcolor="#ffffff", bordercolor=GRID,
                        font=dict(family=FONT, size=13, color=INK)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    title_text="", font=dict(color=INK_2, size=13)),
        bargap=0.35,
        barcornerradius=4,
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor=AXIS, zeroline=False,
                     ticks="outside", ticklen=4, tickcolor=AXIS, automargin=True,
                     tickfont=dict(color=MUTED, size=12), title_font=dict(color=INK_2, size=12))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, gridwidth=1, showline=False, zeroline=False,
                     ticks="", ticklabelstandoff=6, automargin=True, tickfont=dict(color=MUTED, size=12),
                     title_font=dict(color=INK_2, size=12))
    return fig


def show(fig, key, scroll_zoom=False):
    """Tampilkan grafik Plotly dengan gaya di atas (tanpa tema bawaan Streamlit)."""
    st.plotly_chart(fig, theme=None, key=key,
                    config={"displayModeBar": False, "scrollZoom": scroll_zoom})


@contextmanager
def card(title, note=None):
    """Kartu berbingkai: judul, keterangan singkat, lalu isi grafik."""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        if note:
            st.caption(note)
        yield


def table_view(df, formats=None, label="Lihat sebagai tabel"):
    """Versi tabel dari grafik, supaya setiap angka bisa dibaca tanpa hover."""
    with st.expander(label):
        styled = df.style.format(formats or {}, decimal=",", thousands=".")
        st.dataframe(styled, hide_index=True)
