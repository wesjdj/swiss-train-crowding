"""Station names and coordinates from the Swiss service points list."""

from pathlib import Path

import pandas as pd

SERVICE_POINTS_URL = (
    "https://data.opentransportdata.swiss/dataset/39e5f264-257a-4f3f-bccc-5322c37058c5/resource/"
    "d5ccb649-0adf-493e-99a1-8863c37a45b9/download/actual-date-swiss-service-point.csv"
)


def load_stations(csv_path: Path, stop_ids=None) -> pd.DataFrame:
    """Load station id, name, canton and WGS84 coordinates, optionally only for `stop_ids`."""
    cols = {"number": "stop_id", "designationOfficial": "name", "cantonAbbreviation": "canton",
            "wgs84East": "lon", "wgs84North": "lat"}
    df = pd.read_csv(csv_path, sep=";", usecols=list(cols), encoding="utf-8-sig").rename(columns=cols)
    df = df.dropna(subset=["lat", "lon"]).drop_duplicates("stop_id")
    if stop_ids is not None:
        df = df[df["stop_id"].isin(set(stop_ids))]
    return df.reset_index(drop=True)
