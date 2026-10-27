"""Data loading and helpers shared by the app pages."""

from pathlib import Path

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st
from plotly.colors import sample_colorscale

from crowding.parse import LEVEL_LABELS

APP_DATA = Path(__file__).parents[1] / "data" / "app"
CLASSES = {"2nd class": 2, "1st class": 1}
SWISS_VIEW = pdk.ViewState(latitude=46.8, longitude=8.2, zoom=6.8)


@st.cache_resource
def load(name: str) -> pd.DataFrame:
    """Read one app table. The frame is shared between sessions, so never change it in place."""
    return pd.read_parquet(APP_DATA / f"{name}.parquet")


@st.cache_resource
def station_hour() -> pd.DataFrame:
    return load("station_hour").merge(load("stations"), on="stop_id")


def dates() -> list[pd.Timestamp]:
    return [pd.Timestamp(d) for d in sorted(load("station_hour")["date"].unique())]


def context() -> tuple[pd.Timestamp, int]:
    """Return the date and fare class picked in the sidebar."""
    return st.session_state["date"], st.session_state["fare_class"]


def occ_col(fare_class: int) -> str:
    return "occ_2nd" if fare_class == 2 else "occ_1st"


def station_ids() -> dict[str, int]:
    stations = load("stations")
    return dict(sorted(zip(stations["name"], stations["stop_id"])))


def station_select(label: str, default: str, key: str) -> int:
    """Station picker that returns the station id."""
    ids = station_ids()
    names = list(ids)
    return ids[st.selectbox(label, names, index=names.index(default) if default in ids else 0, key=key)]


def rgb(colorscale, values) -> list[list[int]]:
    """Map values in [0, 1] to [r, g, b] lists for pydeck."""
    colors = sample_colorscale(colorscale, list(np.clip(values, 0, 1)))
    return [[int(float(c)) for c in s[s.index("(") + 1:-1].split(",")] for s in colors]


def level_text(level) -> str:
    return "–" if pd.isna(level) else LEVEL_LABELS[int(level)]


def train_text(df: pd.DataFrame) -> pd.Series:
    """Readable train name such as "S12 (SBB 19234)"."""
    return df["line"].astype(str) + " (" + df["operator_name"].astype(str) + " " + df["train"].astype(str) + ")"
