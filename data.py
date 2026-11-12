"""Membaca tabel di folder data/ (hasil prepare_data.py). Dibaca sekali lalu disimpan di cache."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"
ALL_STATIONS = "Semua stasiun"


@st.cache_data
def summary() -> dict:
    return json.loads((DATA / "summary.json").read_text(encoding="utf-8"))


@st.cache_data
def stations() -> pd.DataFrame:
    df = pd.read_csv(DATA / "stations.csv", dtype={"station_id": str})
    df["label"] = df["station_name"] + " (" + df["station_id"] + ")"
    return df


@st.cache_data
def hourly() -> pd.DataFrame:
    """Peminjaman dan pengembalian per stasiun per jam, Mei–Juli 2019 (waktu lokal)."""
    df = pd.read_parquet(DATA / "station_hourly.parquet")
    df["date"] = df["hour_local"].dt.normalize()
    df["hour"] = df["hour_local"].dt.hour
    df["dow"] = df["hour_local"].dt.dayofweek          # 0 = Senin
    df["month"] = df["hour_local"].dt.month
    return df


@st.cache_data
def predictions() -> pd.DataFrame:
    """Aktual dan tiga prediksi per stasiun per jam pada Juli 2019."""
    df = pd.read_parquet(DATA / "predictions_test.parquet")
    df["date"] = df["hour_local"].dt.normalize()
    df["hour"] = df["hour_local"].dt.hour
    return df


@st.cache_data
def daily() -> pd.DataFrame:
    return pd.read_csv(DATA / "daily.csv", parse_dates=["date"])


@st.cache_data
def graph():
    """Node (stasiun) dan edge berarah (asal -> tujuan, bobot = jumlah perjalanan)."""
    names = stations()[["station_id", "station_name", "label", "lat", "lon"]]
    nodes = pd.read_csv(DATA / "graph_nodes.csv", dtype={"station_id": str}).merge(names, on="station_id")
    edges = pd.read_csv(DATA / "graph_edges.csv", dtype={"src": str, "dst": str})
    lookup = names.set_index("station_id")
    for side in ["src", "dst"]:
        edges[f"{side}_name"] = edges[side].map(lookup["station_name"])
        edges[f"{side}_lat"] = edges[side].map(lookup["lat"])
        edges[f"{side}_lon"] = edges[side].map(lookup["lon"])
    return nodes, edges


def station_picker(key: str, default_id: str | None = None) -> str | None:
    """Pilihan stasiun; mengembalikan station_id atau None untuk semua stasiun."""
    table = stations().sort_values("station_name")
    options = [ALL_STATIONS] + table["label"].tolist()
    index = 0
    if default_id is not None:
        index = options.index(table.loc[table["station_id"] == default_id, "label"].iloc[0])
    choice = st.selectbox("Stasiun", options, index=index, key=key)
    if choice == ALL_STATIONS:
        return None
    return table.loc[table["label"] == choice, "station_id"].iloc[0]


def station_name(station_id: str) -> str:
    table = stations()
    return table.loc[table["station_id"] == station_id, "station_name"].iloc[0]
