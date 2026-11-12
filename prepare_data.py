"""Menyiapkan tabel kecil untuk dashboard dari keluaran pipeline Spark.

Jalankan sekali dari folder proyek:   python prepare_data.py

Masukan  : folder source/  -> CSV keluaran notebook PySpark (run 20261105T083506447654Z)
Keluaran : folder data/    -> tabel ringkas yang dibaca app.py

Skrip ini TIDAK melatih atau mengubah model. Isinya hanya:
  1. merapikan bentuk tabel supaya dashboard cepat dibuka, dan
  2. memeriksa bahwa angka hasil olahan sama dengan keluaran pipeline.
Kalau ada angka yang tidak cocok, skrip berhenti dengan AssertionError.
"""
from pathlib import Path
import json
import shutil

import numpy as np
import pandas as pd

SOURCE = Path(__file__).parent / "source"
DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)

LOCAL_TZ = "America/New_York"
# Batas waktu sama dengan notebook (waktu lokal, batas akhir eksklusif).
START_UTC = pd.Timestamp("2019-05-01 00:00", tz=LOCAL_TZ).tz_convert("UTC")
TRAIN_END_UTC = pd.Timestamp("2019-06-16 00:00", tz=LOCAL_TZ).tz_convert("UTC")
END_UTC = pd.Timestamp("2019-08-01 00:00", tz=LOCAL_TZ).tz_convert("UTC")


def to_local(series_utc: pd.Series) -> pd.Series:
    """UTC -> waktu lokal New York tanpa info zona (lebih ringkas untuk grafik)."""
    return series_utc.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)


# ---------------------------------------------------------------- 1. Perjalanan
trips = pd.read_csv(
    SOURCE / "trips_core.csv",
    dtype={"start_station_id": str, "end_station_id": str},
)
trips["start_utc"] = pd.to_datetime(trips["start_time_utc"], utc=True, format="ISO8601")
trips["end_utc"] = pd.to_datetime(trips["end_time_utc"], utc=True, format="ISO8601")
trips["start_hour_utc"] = trips["start_utc"].dt.floor("h")
trips["end_hour_utc"] = trips["end_utc"].dt.floor("h")
trips["end_within_period"] = trips["end_utc"] < END_UTC
assert len(trips) == 119_311, "Jumlah perjalanan berbeda dari laporan (119.311)."

# --------------------------------------------------- 2. Stasiun dalam cakupan
# Aturan notebook: stasiun asal yang sudah muncul sebelum akhir periode pelatihan.
first_seen = (
    trips[trips["start_utc"] < TRAIN_END_UTC]
    .groupby("start_station_id")["start_hour_utc"].min()
    .rename("active_from_utc")
)
stations = (
    trips.groupby("start_station_id")
    .agg(station_name=("start_station_name", "first"),
         lat=("start_latitude", "first"),
         lon=("start_longitude", "first"))
    .join(first_seen, how="inner")
    .rename_axis("station_id")
    .reset_index()
    .sort_values("station_id")
)
graph_nodes = pd.read_csv(SOURCE / "graph_nodes.csv", dtype={"station_id": str})
assert set(stations["station_id"]) == set(graph_nodes["station_id"]), "Cakupan stasiun berbeda dari graph_nodes.csv"
assert len(stations) == 52

# ------------------------------------------- 3. Tabel stasiun-jam (Mei-Juli)
# Satu baris per stasiun per jam sejak keberangkatan pertama stasiun itu.
# Jam tanpa perjalanan diisi nol, sama dengan notebook.
all_hours = pd.date_range(START_UTC, END_UTC - pd.Timedelta(hours=1), freq="h")
grid = stations[["station_id", "active_from_utc"]].merge(
    pd.DataFrame({"hour_utc": all_hours}), how="cross"
)
grid = grid[grid["hour_utc"] >= grid["active_from_utc"]].drop(columns="active_from_utc")

departures = (
    trips.groupby(["start_station_id", "start_hour_utc"]).size()
    .rename("departures").reset_index()
    .rename(columns={"start_station_id": "station_id", "start_hour_utc": "hour_utc"})
)
arrivals = (
    trips[trips["end_within_period"]]
    .groupby(["end_station_id", "end_hour_utc"]).size()
    .rename("arrivals").reset_index()
    .rename(columns={"end_station_id": "station_id", "end_hour_utc": "hour_utc"})
)
hourly = (
    grid.merge(departures, on=["station_id", "hour_utc"], how="left")
    .merge(arrivals, on=["station_id", "hour_utc"], how="left")
    .fillna({"departures": 0, "arrivals": 0})
    .astype({"departures": "int32", "arrivals": "int32"})
)
hourly["hour_local"] = to_local(hourly["hour_utc"])
assert len(hourly) == 113_617, f"Baris stasiun-jam {len(hourly)} != 113.617 (Tabel 4.5)."

# ------------------------------------------------ 4. Prediksi pada data uji
pred_long = pd.read_csv(SOURCE / "predictions_test.csv", dtype={"station_id": str})
assert len(pred_long) == 232_128
pred = (
    pred_long.pivot(index=["station_id", "hour_start_utc", "hour_start_local", "target"],
                    columns="variant", values="prediction")
    .reset_index()
)
actual = (
    pred_long.groupby(["station_id", "hour_start_utc", "target"])["actual"]
    .agg(["first", "nunique"]).reset_index()
)
assert (actual["nunique"] == 1).all(), "Nilai aktual berbeda antarvarian."
pred = pred.merge(actual.drop(columns="nunique").rename(columns={"first": "actual"}),
                  on=["station_id", "hour_start_utc", "target"])
pred["hour_local"] = pd.to_datetime(pred["hour_start_local"])
pred["hour_utc"] = pd.to_datetime(pred["hour_start_utc"], utc=True)
pred = pred[["station_id", "hour_utc", "hour_local", "target", "actual",
             "baseline_minggu_lalu", "tanpa_cuaca", "dengan_cuaca"]]
pred = pred.sort_values(["target", "station_id", "hour_local"]).reset_index(drop=True)
assert len(pred) == 38_688 * 2

VARIANTS = ["baseline_minggu_lalu", "tanpa_cuaca", "dengan_cuaca"]

# Pemeriksaan A: MAE/RMSE dari tabel ini sama dengan test_metrics.csv
test_metrics = pd.read_csv(SOURCE / "test_metrics.csv")
for row in test_metrics.itertuples():
    part = pred[pred["target"] == row.target]
    err = part[row.variant] - part["actual"]
    assert np.isclose(err.abs().mean(), row.mae, atol=1e-9), (row.variant, row.target)
    assert np.isclose(np.sqrt((err ** 2).mean()), row.rmse, atol=1e-9), (row.variant, row.target)

# Pemeriksaan B: MAE per stasiun sama dengan metrics_by_station.csv
by_station = pd.read_csv(SOURCE / "metrics_by_station.csv", dtype={"station_id": str})
for variant in VARIANTS:
    mine = (
        pred.assign(abs_err=(pred[variant] - pred["actual"]).abs())
        .groupby(["station_id", "target"])["abs_err"].mean().rename("mae_mine").reset_index()
    )
    both = by_station[by_station["variant"] == variant].merge(mine, on=["station_id", "target"])
    assert len(both) == 104 and np.allclose(both["mae"], both["mae_mine"], atol=1e-9), variant

# Pemeriksaan C: nilai aktual Juli sama dengan agregasi ulang dari trips_core.csv
check = pred.pivot(index=["station_id", "hour_utc"], columns="target", values="actual").reset_index()
check = check.merge(hourly, on=["station_id", "hour_utc"], how="left", suffixes=("_pred", ""))
assert (check["departures_pred"] == check["departures"]).all()
assert (check["arrivals_pred"] == check["arrivals"]).all()

# ----------------------------------------------------------------- 5. Graph
edges = pd.read_csv(SOURCE / "graph_edges.csv", dtype={"src": str, "dst": str})
in_scope = set(stations["station_id"])
graph_trips = trips[
    trips["end_within_period"]
    & trips["start_station_id"].isin(in_scope)
    & trips["end_station_id"].isin(in_scope)
]
edges_mine = (
    graph_trips.groupby(["start_station_id", "end_station_id"]).size().rename("weight_mine")
    .reset_index().rename(columns={"start_station_id": "src", "end_station_id": "dst"})
)
both = edges.merge(edges_mine, on=["src", "dst"], how="outer")
assert len(both) == len(edges) == 2_379 and (both["weight"] == both["weight_mine"]).all()
assert edges["weight"].sum() == graph_nodes["out_strength"].sum() == graph_nodes["in_strength"].sum() == 117_016

# ---------------------------------------------- 6. Ringkasan harian + cuaca
weather = pd.read_csv(SOURCE / "weather_hourly.csv")
weather["time_utc"] = pd.to_datetime(weather["weather_time_utc"], utc=True)
# Suhu dan angin: nilai pada awal jam. Presipitasi: akumulasi satu jam SEBELUM
# timestamp, jadi digeser mundur satu jam supaya jatuh pada jam yang benar.
instant = weather.assign(date=to_local(weather["time_utc"]).dt.normalize())
rain = weather.assign(date=to_local(weather["time_utc"] - pd.Timedelta(hours=1)).dt.normalize())
daily_weather = (
    instant.groupby("date").agg(temp_mean_c=("temperature_c", "mean"),
                                temp_max_c=("temperature_c", "max"),
                                wind_mean_ms=("wind_speed_ms", "mean"))
    .join(rain.groupby("date").agg(precip_mm=("precipitation_previous_hour_mm", "sum")))
)
trips["start_date"] = to_local(trips["start_utc"]).dt.normalize()
daily = (
    trips.groupby("start_date").size().rename("trips").rename_axis("date").to_frame()
    .join(daily_weather, how="left").reset_index()
)
assert len(daily) == 92 and daily["trips"].sum() == 119_311 and daily.notna().all().all()
daily = daily.round({"temp_mean_c": 2, "temp_max_c": 1, "wind_mean_ms": 2, "precip_mm": 1})

# ------------------------------------------------------------- 7. Simpan
stations.drop(columns="active_from_utc").to_csv(DATA / "stations.csv", index=False)
hourly[["station_id", "hour_local", "departures", "arrivals"]].to_parquet(DATA / "station_hourly.parquet", index=False)
pred.drop(columns="hour_utc").to_parquet(DATA / "predictions_test.parquet", index=False)
daily.to_csv(DATA / "daily.csv", index=False)
shutil.copy(SOURCE / "graph_nodes.csv", DATA / "graph_nodes.csv")
shutil.copy(SOURCE / "graph_edges.csv", DATA / "graph_edges.csv")

month_names = {5: "Mei", 6: "Juni", 7: "Juli"}
summary = {
    "run_id": "20261105T083506447654Z",
    "trips_total": int(len(trips)),
    "trips_by_month": {month_names[m]: int(n) for m, n in trips.groupby(trips["start_date"].dt.month).size().items()},
    "days": int(len(daily)),
    "stations_in_scope": int(len(stations)),
    "station_hour_rows": int(len(hourly)),
    "test_rows_per_target": int(len(pred) // 2),
    "graph_trips": int(edges["weight"].sum()),
    "graph_edges": int(len(edges)),
    "graph_self_loop_trips": int(edges.loc[edges["src"] == edges["dst"], "weight"].sum()),
}
(DATA / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print("Semua pemeriksaan cocok dengan keluaran pipeline.")
print(json.dumps(summary, indent=2, ensure_ascii=False))
for f in sorted(DATA.iterdir()):
    print(f"  data/{f.name:28s} {f.stat().st_size / 1024:8.1f} KB")
