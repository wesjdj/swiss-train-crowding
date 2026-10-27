"""Streamlit app: explore the SBB occupancy forecast."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st
from plotly.colors import sample_colorscale

from crowding.parse import LEVEL_LABELS
from crowding.theme import DIVERGING, LEVEL_COLORS, use_plotly

APP_DATA = Path(__file__).parent / "data" / "app"
CLASSES = {"2nd class": 2, "1st class": 1}

st.set_page_config(page_title="Swiss train crowding", page_icon="🚆", layout="wide")
use_plotly()


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(APP_DATA / f"{name}.parquet")


def rgb(colorscale, values) -> list[list[int]]:
    """Map values in [0, 1] to [r, g, b] lists for pydeck."""
    colors = sample_colorscale(colorscale, list(np.clip(values, 0, 1)))
    return [[int(float(c)) for c in s[s.index("(") + 1:-1].split(",")] for s in colors]


def level_text(level) -> str:
    return "–" if pd.isna(level) else LEVEL_LABELS[int(level)]


stations = load("stations")
station_hour = load("station_hour").merge(stations, on="stop_id")
board = load("board")
trains = load("trains")
daily = load("daily_levels")
dates = [pd.Timestamp(d) for d in sorted(station_hour["date"].unique())]
date_labels = {f"{d:%a %Y-%m-%d}": d for d in dates}

st.title("Swiss train crowding forecast")
st.caption(
    "Expected occupancy of SBB, BLS, Thurbo, SOB and zb trains, for each stop and class. "
    "Source: [Occupancy Forecast SIRI Dataset](https://opendata.swiss/en/dataset/occupancy-forecast-siri-dataset), "
    f"opentransportdata.swiss. Snapshot: {dates[0]:%Y-%m-%d} to {dates[-1]:%Y-%m-%d}."
)

with st.sidebar:
    date = date_labels[st.selectbox("Date", list(date_labels))]
    fare_class = CLASSES[st.radio("Class", list(CLASSES))]
    st.markdown(
        "**Crowded** means the forecast says *few seats* or *standing room only*.\n\n"
        "Stations outside Switzerland have no coordinates in the source list, so they are not on the maps."
    )

day = station_hour[(station_hour["date"] == date) & (station_hour["fare_class"] == fare_class)]
tab_map, tab_station, tab_trains, tab_tide, tab_calendar = st.tabs(
    ["Map by hour", "Station board", "Busiest trains", "Commuter tide", "Next 3 months"]
)

with tab_map:
    hour = st.slider("Hour of departure", 0, 23, 17)
    view = day[day["hour"] == hour].copy()
    view["color"] = rgb("Viridis", view["share_crowded"] / 0.6)
    view["radius"] = 300 + 250 * np.sqrt(view["departures"])
    view["crowded_pct"] = (100 * view["share_crowded"]).round(0)
    view["standing_pct"] = (100 * view["share_standing"]).round(0)
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("ScatterplotLayer", view, get_position=["lon", "lat"], get_fill_color="color",
                          get_radius="radius", opacity=0.85, pickable=True, stroked=True,
                          get_line_color=[255, 255, 255], line_width_min_pixels=0.5)],
        initial_view_state=pdk.ViewState(latitude=46.8, longitude=8.2, zoom=6.8),
        tooltip={"text": "{name}\n{departures} departures\n{crowded_pct}% crowded\n{standing_pct}% standing room only"},
        map_style="light",
    ), height=560)
    c1, c2, c3 = st.columns(3)
    c1.metric("Departures in this hour", f"{int(view['departures'].sum()):,}")
    crowded = (view["share_crowded"] * view["departures"]).sum() / max(view["departures"].sum(), 1)
    c2.metric("Crowded", f"{100 * crowded:.0f}%")
    c3.metric("Stations with standing room only", int((view["share_standing"] > 0).sum()))
    st.caption("Colour: share of crowded departures (viridis, clipped at 60%). Size: number of departures.")

with tab_station:
    stop_ids = dict(zip(stations["name"], stations["stop_id"]))
    names = sorted(stop_ids)
    name = st.selectbox("Station", names, index=names.index("Zürich HB") if "Zürich HB" in stop_ids else 0)
    stop = stop_ids[name]
    deps = board[(board["stop_id"] == stop) & (board["date"] == date)].sort_values("departure")
    col = "occ_2nd" if fare_class == 2 else "occ_1st"
    counts = (deps.assign(hour=deps["departure"].dt.hour, level=deps[col])
              .dropna(subset=["level"]).groupby(["hour", "level"]).size().reset_index(name="n"))
    fig = go.Figure()
    for lvl, label in LEVEL_LABELS.items():
        part = counts[counts["level"] == lvl]
        fig.add_bar(x=part["hour"], y=part["n"], name=label, marker_color=LEVEL_COLORS[lvl],
                    marker_line_color="white", marker_line_width=1)
    fig.update_layout(barmode="stack", height=320, margin=dict(t=10, b=10),
                      xaxis=dict(title="Hour of departure", dtick=2, range=[-0.5, 23.5]),
                      yaxis_title="Departures", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width="stretch")
    only_crowded = st.toggle("Show only crowded departures", value=True)
    if only_crowded:
        deps = deps[deps[col] >= 2]
    st.dataframe(
        pd.DataFrame({
            "Time": deps["departure"].dt.strftime("%H:%M"),
            "Train": deps["operator_name"] + " " + deps["train"],
            "Stop on trip": (deps["seq"] + 1).astype(str) + " of " + deps["trip_len"].astype(str),
            "2nd class": deps["occ_2nd"].map(level_text),
            "1st class": deps["occ_1st"].map(level_text),
        }),
        hide_index=True, width="stretch", height=360,
    )

with tab_trains:
    full = trains[(trains["date"] == date) & (trains["max_2nd"] == 3)]
    top = full.sort_values(["standing_stops_2nd", "stops"], ascending=False).head(25)
    st.markdown(f"**{len(full)}** trains have *standing room only* in 2nd class at one or more stops "
                "on this date. These are the 25 with the most such stops:")
    st.dataframe(
        pd.DataFrame({
            "Train": top["operator_name"] + " " + top["train"],
            "Start": top["start"].dt.strftime("%H:%M"),
            "From": top["from"], "To": top["to"],
            "Stops with standing room only": top["standing_stops_2nd"].astype(str) + " of " + top["stops"].astype(str),
        }),
        hide_index=True, width="stretch",
    )

with tab_tide:
    st.markdown(
        "On weekdays, is a station crowded more in the **morning** (06:00–09:00) or in the **evening** "
        "(16:00–19:00)? Tilt = (morning − evening) / (morning + evening), from the mean level above *many seats*. "
        "City hubs are crowded in the evening, when people go home. Small towns and border stations are "
        "crowded in the morning, when commuters leave."
    )
    wk = station_hour[(pd.to_datetime(station_hour["date"]).dt.day_of_week < 5) & (station_hour["fare_class"] == fare_class)]
    wk = wk.assign(load=(wk["mean_level"] - 1) * wk["departures"],
                   window=np.select([wk["hour"].between(6, 8), wk["hour"].between(16, 18)], ["am", "pm"], "other"))
    agg = wk[wk["window"] != "other"].groupby(["stop_id", "window"])[["load", "departures"]].sum()
    per = (agg["load"] / agg["departures"]).unstack().fillna(0)
    total = wk.groupby("stop_id")["departures"].sum()
    per = per[(per["am"] + per["pm"] > 0.25) & (total.reindex(per.index) >= 400)]
    per["tilt"] = (per["am"] - per["pm"]) / (per["am"] + per["pm"])
    tide = per.reset_index().merge(stations, on="stop_id")
    tide["color"] = rgb([[i / 4, c] for i, c in enumerate(DIVERGING)], (tide["tilt"] + 1) / 2)
    tide["tilt_txt"] = tide["tilt"].round(2)
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("ScatterplotLayer", tide, get_position=["lon", "lat"], get_fill_color="color",
                          get_radius=2200, opacity=0.9, pickable=True, stroked=True,
                          get_line_color=[120, 120, 120], line_width_min_pixels=0.5)],
        initial_view_state=pdk.ViewState(latitude=46.8, longitude=8.2, zoom=6.8),
        tooltip={"text": "{name}\ntilt {tilt_txt}"},
        map_style="light",
    ), height=520)
    st.caption("Orange: crowded in the morning. Blue: crowded in the evening. Light: balanced. "
               f"{len(tide)} stations with enough crowded departures.")
    c1, c2 = st.columns(2)
    show = tide.sort_values("tilt")[["name", "am", "pm", "tilt"]].round(2)
    c1.markdown("**Evening-crowded**")
    c1.dataframe(show.head(10), hide_index=True, width="stretch")
    c2.markdown("**Morning-crowded**")
    c2.dataframe(show.tail(10).iloc[::-1], hide_index=True, width="stretch")

with tab_calendar:
    d = daily[(daily["fare_class"] == fare_class) & daily["level"].notna()].groupby(["date", "level"])["n"].sum().unstack()
    share = (d[[2, 3]].sum(axis=1) / d.sum(axis=1)).rename("crowded").reset_index()
    share["weekday"] = share["date"].dt.day_name()
    fig = px.bar(share, x="date", y="crowded", hover_data={"weekday": True},
                 labels={"crowded": "Share of crowded departures", "date": ""})
    fig.update_traces(marker_color=LEVEL_COLORS[3])
    fig.update_layout(height=380, yaxis_tickformat=".0%", margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
    st.caption("All forecast days in the source file. The weekly pattern is clear: Sundays are the quietest days. "
               "Christmas Day and New Year's Day are the quietest days of all.")
