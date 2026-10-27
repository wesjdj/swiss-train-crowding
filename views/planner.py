import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from crowding.parse import LEVEL_LABELS
from crowding.theme import LEVEL_COLORS
from views.common import context, level_text, load, occ_col, station_ids, station_select, train_text

date, fare_class = context()
st.title("A → B planner")
st.markdown("When is the train between two stations least crowded? The planner finds all **direct** trains "
            "on the date and shows the worst level that each train has between A and B.")

c1, c2 = st.columns(2)
with c1:
    origin = station_select("From", "Zürich HB", key="planner_from")
with c2:
    target = station_select("To", "Bern", key="planner_to")
names = {v: k for k, v in station_ids().items()}

board = load("board")
day = board[board["date"] == date]
run = ["operator_name", "train"]
at_a = day[day["stop_id"] == origin][run + ["seq", "departure", "line", "dest_name"]]
at_b = day[day["stop_id"] == target][run + ["seq", "departure"]].rename(columns={"seq": "seq_b", "departure": "time_b"})
ends_at_b = (day[day["dest_id"] == target].drop_duplicates(run)[run + ["trip_len"]]
             .rename(columns={"trip_len": "seq_b"}).assign(time_b=pd.Series(dtype=at_b["time_b"].dtype)))
trips = at_a.merge(pd.concat([at_b, ends_at_b]), on=run)
trips = trips[trips["seq_b"] > trips["seq"]].drop_duplicates(run + ["seq"])

if origin == target or trips.empty:
    st.info(f"No direct train from {names[origin]} to {names[target]} on this date.")
    st.stop()

legs = day.merge(trips[run + ["seq", "seq_b"]].rename(columns={"seq": "seq_a"}), on=run)
legs = legs[(legs["seq"] >= legs["seq_a"]) & (legs["seq"] < legs["seq_b"])]
worst = legs.groupby(run + ["seq_a"], observed=True)[["occ_1st", "occ_2nd"]].max().reset_index()
trips = (trips.merge(worst.rename(columns={"seq_a": "seq"}), on=run + ["seq"])
         .sort_values("departure").reset_index(drop=True))
col = occ_col(fare_class)

m1, m2, m3 = st.columns(3)
m1.metric("Direct trains", len(trips))
m2.metric("With few seats on the way", int((trips[col] == 2).sum()))
m3.metric("With standing room only", int((trips[col] == 3).sum()))

fig = go.Figure()
for lvl, label in LEVEL_LABELS.items():
    part = trips[trips[col] == lvl]
    fig.add_scatter(x=part["departure"], y=[label] * len(part), mode="markers", name=label,
                    marker=dict(color=LEVEL_COLORS[lvl], size=14, line=dict(color="#848484", width=1)),
                    text=train_text(part) + " to " + part["dest_name"].astype(str),
                    hovertemplate="%{x|%H:%M} %{text}<extra></extra>")
fig.update_layout(height=230, margin=dict(t=10, b=10), showlegend=False,
                  xaxis=dict(title="Departure from " + names[origin], tickformat="%H:%M", showgrid=True,
                             gridcolor="#e5e5e5"),
                  yaxis=dict(categoryorder="array", categoryarray=list(LEVEL_LABELS.values())))
st.plotly_chart(fig, width="stretch")

st.dataframe(
    pd.DataFrame({
        "Departs": trips["departure"].dt.strftime("%H:%M"),
        f"At {names[target]}": trips["time_b"].dt.strftime("%H:%M").fillna("last stop"),
        "Train": train_text(trips),
        "Towards": trips["dest_name"],
        "Stops": trips["seq_b"] - trips["seq"],
        "2nd class (worst on the way)": trips["occ_2nd"].map(level_text),
        "1st class (worst on the way)": trips["occ_1st"].map(level_text),
    }),
    hide_index=True, width="stretch", height=420,
)
st.caption(f"*At {names[target]}* is the departure time there; the source has no arrival times. "
           "The planner shows direct trains only, no changes.")
