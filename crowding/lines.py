"""Line names for trains, from the Swiss GTFS timetable."""

import zipfile
from pathlib import Path

import pandas as pd

GTFS_PERMALINK = "https://data.opentransportdata.swiss/dataset/timetable-{year}-gtfs2020/permalink"


def timetable_year(date: pd.Timestamp) -> int:
    """Return the timetable year that `date` falls in (the timetable changes in mid-December)."""
    return date.year + 1 if date.month == 12 and date.day >= 13 else date.year


def load_line_map(gtfs_zip: Path, operators) -> pd.DataFrame:
    """Map (operator, train number) to the most frequent GTFS route of that train."""
    with zipfile.ZipFile(gtfs_zip) as zf:
        with zf.open("routes.txt") as fh:
            routes = pd.read_csv(fh, dtype=str, encoding="utf-8-sig",
                                 usecols=["route_id", "agency_id", "route_short_name", "route_desc"])
        with zf.open("trips.txt") as fh:
            trips = pd.read_csv(fh, dtype=str, encoding="utf-8-sig", usecols=["route_id", "trip_short_name"])
    routes = routes[routes["agency_id"].isin({str(o) for o in operators})]
    trips = trips.merge(routes, on="route_id").rename(columns={"trip_short_name": "train"})
    counts = trips.groupby(["agency_id", "train", "route_id"]).size().rename("n").reset_index()
    best = counts.sort_values("n", ascending=False).drop_duplicates(["agency_id", "train"])
    best = best.merge(routes[["route_id", "route_short_name", "route_desc"]], on="route_id")
    best["line"] = best["route_short_name"].fillna(best["route_desc"]).fillna("?")
    best["operator"] = best["agency_id"].astype(int)
    return best[["operator", "train", "route_id", "line"]]


def add_lines(departures: pd.DataFrame, line_map: pd.DataFrame) -> pd.DataFrame:
    """Add `route_id`, `line` and a readable `line_label` such as "S12: Brugg AG – Seuzach"."""
    df = departures.merge(line_map, on=["operator", "train"], how="left")
    df["line"] = df["line"].fillna("–")
    runs = df.drop_duplicates(["date", "operator", "train"])
    runs = runs[runs["route_id"].notna()]
    origin = df[df["seq"] == 0][["date", "operator", "train", "stop_name"]].rename(columns={"stop_name": "origin"})
    runs = runs.merge(origin, on=["date", "operator", "train"])
    ends = pd.concat([runs[["route_id", "origin"]].rename(columns={"origin": "end"}),
                      runs[["route_id", "dest_name"]].rename(columns={"dest_name": "end"})])
    top = ends.groupby("route_id")["end"].agg(lambda s: " – ".join(s.value_counts().index[:2]))
    labels = (runs.drop_duplicates("route_id").set_index("route_id")["line"] + ": " + top).rename("line_label")
    dup = labels.duplicated(keep=False)
    labels[dup] = labels[dup] + " (" + labels[dup].index + ")"
    df = df.merge(labels, left_on="route_id", right_index=True, how="left")
    df["line_label"] = df["line_label"].fillna(df["operator_name"] + " (no timetable line)")
    return df
