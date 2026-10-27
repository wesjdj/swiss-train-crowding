"""Download the forecast and build the tables for the notebook and the app.

Usage: python -m crowding.build [--days 14] [--data-dir data]
"""

import argparse
import urllib.request
from pathlib import Path

import pandas as pd

from crowding.lines import GTFS_PERMALINK, add_lines, load_line_map, timetable_year
from crowding.parse import OPERATORS, count_levels, parse_zip
from crowding.stations import SERVICE_POINTS_URL, load_stations

FORECAST_URL = (
    "https://data.opentransportdata.swiss/dataset/b11c0afa-c439-420e-b6d8-658db2fc603f/resource/"
    "6deeedc3-701a-4903-a9bd-a3d366c80ebf/download/occupancyforecastsiri.zip"
)


def download(url: str, target: Path, refresh: bool = False) -> Path:
    """Download `url` to `target` unless it is already there."""
    if refresh or not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {target.name} ...", flush=True)
        urllib.request.urlretrieve(url, target)
    return target


def by_class(departures: pd.DataFrame, id_vars: list[str]) -> pd.DataFrame:
    """One row per departure and class, with the level and crowded/standing flags."""
    long = departures.melt(id_vars=id_vars, value_vars=["occ_1st", "occ_2nd"],
                           var_name="fare_class", value_name="level").dropna(subset=["level"])
    long["fare_class"] = long["fare_class"].map({"occ_1st": 1, "occ_2nd": 2}).astype("int8")
    level = long["level"].astype(float)
    return long.assign(level=level, crowded=level >= 2, standing=level == 3)


def build_segments(departures: pd.DataFrame) -> pd.DataFrame:
    """Crowding per stop-to-stop segment (both directions together), date, hour and class."""
    runs = departures.sort_values(["date", "operator", "train", "seq"])
    next_id = runs.groupby(["date", "operator", "train"])["stop_id"].shift(-1)
    runs = runs.assign(next_id=next_id.fillna(runs["dest_id"]).astype("int64"))
    long = by_class(runs, ["date", "hour", "stop_id", "next_id"])
    long["a"] = long[["stop_id", "next_id"]].min(axis=1)
    long["b"] = long[["stop_id", "next_id"]].max(axis=1)
    seg = (long.groupby(["date", "hour", "fare_class", "a", "b"])
           .agg(trains=("level", "size"), share_crowded=("crowded", "mean"), share_standing=("standing", "mean"))
           .reset_index())
    seg[["share_crowded", "share_standing"]] = seg[["share_crowded", "share_standing"]].astype("float32")
    return seg


def build_app_tables(departures: pd.DataFrame, stations: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Make the small tables that the Streamlit app reads."""
    long = by_class(departures, ["date", "stop_id", "hour"])
    station_hour = (
        long.groupby(["date", "stop_id", "hour", "fare_class"])
        .agg(departures=("level", "size"), mean_level=("level", "mean"),
             share_crowded=("crowded", "mean"), share_standing=("standing", "mean"))
        .reset_index()
    )
    station_hour[["mean_level", "share_crowded", "share_standing"]] = (
        station_hour[["mean_level", "share_crowded", "share_standing"]].astype("float32")
    )
    board = departures[["date", "departure", "stop_id", "operator_name", "train", "seq", "trip_len",
                        "occ_1st", "occ_2nd", "dest_id", "dest_name", "line", "line_label"]].copy()
    for col in ["operator_name", "dest_name", "line", "line_label"]:
        board[col] = board[col].astype("category")
    ends = departures.sort_values("seq").groupby(["date", "operator_name", "train"])
    trains = pd.DataFrame({
        "line": ends["line"].first(),
        "line_label": ends["line_label"].first(),
        "from": ends["stop_name"].first(),
        "to": ends["dest_name"].first(),
        "start": ends["departure"].first(),
        "stops": ends["seq"].size(),
        "max_2nd": ends["occ_2nd"].max(),
        "max_1st": ends["occ_1st"].max(),
        "standing_stops_2nd": ends["occ_2nd"].agg(lambda s: int((s == 3).sum())),
    }).reset_index()
    return {"station_hour": station_hour, "board": board, "trains": trains,
            "segments": build_segments(departures), "stations": stations}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=14, help="forecast days to parse in full")
    parser.add_argument("--app-days", type=int, default=7, help="forecast days to keep for the app")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--refresh", action="store_true", help="download the files again")
    args = parser.parse_args()

    raw = args.data_dir / "raw"
    zip_path = download(FORECAST_URL, raw / "occupancyforecastsiri.zip", args.refresh)
    sp_path = download(SERVICE_POINTS_URL, raw / "service-points.csv", args.refresh)

    print(f"Parsing {args.days} forecast days ...", flush=True)
    departures = parse_zip(zip_path, days=args.days)
    years = sorted({timetable_year(pd.Timestamp(d)) for d in departures["date"].unique()})
    line_map = pd.concat([
        load_line_map(download(GTFS_PERMALINK.format(year=y), raw / f"gtfs-{y}.zip", args.refresh), OPERATORS)
        for y in years
    ]).drop_duplicates(["operator", "train"])
    departures = add_lines(departures, line_map)
    print(f"  {(departures['route_id'].notna()).mean():.1%} of departures matched to a timetable line", flush=True)
    departures.to_parquet(args.data_dir / "departures.parquet", index=False)
    print(f"  {len(departures):,} departures", flush=True)

    print("Counting levels for all forecast days ...", flush=True)
    daily = count_levels(zip_path)
    daily.to_parquet(args.data_dir / "daily_levels.parquet", index=False)

    stations = load_stations(sp_path, set(departures["stop_id"]) | set(departures["dest_id"]))
    stations.to_parquet(args.data_dir / "stations.parquet", index=False)

    app_dir = args.data_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    first_days = sorted(departures["date"].unique())[: args.app_days]
    tables = build_app_tables(departures[departures["date"].isin(first_days)], stations)
    tables["daily_levels"] = daily
    for name, table in tables.items():
        table.to_parquet(app_dir / f"{name}.parquet", index=False, compression="zstd")
        print(f"  app/{name}.parquet: {len(table):,} rows", flush=True)


if __name__ == "__main__":
    main()
