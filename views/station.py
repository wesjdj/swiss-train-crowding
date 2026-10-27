import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from crowding.parse import LEVEL_LABELS
from crowding.theme import LEVEL_COLORS
from views.common import context, level_text, load, occ_col, station_select, train_text

date, fare_class = context()
st.title("Station board")
board = load("board")

stop = station_select("Station", "Zürich HB", key="board_station")
deps = board[(board["stop_id"] == stop) & (board["date"] == date)].sort_values("departure")
col = occ_col(fare_class)
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

if st.toggle("Show only crowded departures", value=True):
    deps = deps[deps[col] >= 2]
st.dataframe(
    pd.DataFrame({
        "Time": deps["departure"].dt.strftime("%H:%M"),
        "Train": train_text(deps),
        "To": deps["dest_name"],
        "Stop on trip": (deps["seq"] + 1).astype(str) + " of " + deps["trip_len"].astype(str),
        "2nd class": deps["occ_2nd"].map(level_text),
        "1st class": deps["occ_1st"].map(level_text),
    }),
    hide_index=True, width="stretch", height=420,
)
