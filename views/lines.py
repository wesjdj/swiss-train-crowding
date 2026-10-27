import plotly.graph_objects as go
import streamlit as st

from crowding.parse import LEVEL_LABELS
from crowding.theme import LEVEL_COLORS
from views.common import context, level_text, load, occ_col

date, fare_class = context()
st.title("Line explorer")
col = occ_col(fare_class)
board = load("board")
day = board[(board["date"] == date) & ~board["line_label"].astype(str).str.endswith("(no timetable line)")]
run = ["operator_name", "train"]

standing = (day.assign(st=day[col] == 3).groupby("line_label", observed=True)["st"].sum()
            .sort_values(ascending=False))
options = sorted(standing.index.astype(str))
line = st.selectbox("Line", options, index=options.index(str(standing.index[0])),
                    help="The default is the line with the most departures with standing room only on this date.")
runs = day[day["line_label"] == line]
dests = runs.drop_duplicates(run)["dest_name"].astype(str).value_counts()
towards = st.radio("Direction: towards", list(dests.index[:6]), horizontal=True)
runs = runs[runs["dest_name"] == towards]

longest = runs.groupby(run, observed=True)["seq"].size().idxmax()
axis = runs.set_index(run).loc[longest].sort_values("seq")
order = {sid: i for i, sid in enumerate(dict.fromkeys(axis["stop_id"]))}
names = load("stations").set_index("stop_id")["name"].to_dict()
labels = [names.get(sid, str(sid)) for sid in order]
runs = runs[runs["stop_id"].isin(order)].assign(pos=lambda d: d["stop_id"].map(order))

n_runs = runs.drop_duplicates(run).shape[0]
m1, m2 = st.columns(2)
m1.metric("Trains in this direction", n_runs)
m2.metric("Departures crowded", f"{(runs[col] >= 2).mean():.0%}")

st.subheader("When and where")
heat = (runs.assign(hour=runs["departure"].dt.hour, level=runs[col].astype(float))
        .pivot_table(index="pos", columns="hour", values="level", aggfunc="mean")
        .reindex(index=range(len(labels)), columns=range(24)))
fig = go.Figure(go.Heatmap(
    z=heat.values, x=heat.columns, y=labels, colorscale="Viridis", zmin=1, zmax=3,
    colorbar=dict(title="Mean level", tickvals=[1, 2, 3], ticktext=list(LEVEL_LABELS.values())),
    hovertemplate="%{y}, %{x}:00<br>mean level %{z:.2f}<extra></extra>",
))
fig.update_layout(height=max(320, 22 * len(labels)), margin=dict(t=10, b=10),
                  xaxis=dict(title="Hour of departure", dtick=1), yaxis=dict(autorange="reversed"))
st.plotly_chart(fig, width="stretch")

st.subheader("Every train (Marey diagram)")
st.caption("Each line is one train: time to the right, stops from top to bottom. "
           "The colour of a section is the level when the train leaves the stop at its start.")
sections = {lvl: ([], []) for lvl in LEVEL_LABELS}
for _, trip in runs.sort_values("seq").groupby(run, observed=True):
    times = trip["departure"].tolist()
    pos = trip["pos"].tolist()
    levels = trip[col].astype("float64").tolist()
    for i in range(len(trip) - 1):
        if levels[i] in sections:
            xs, ys = sections[levels[i]]
            xs += [times[i], times[i + 1], None]
            ys += [pos[i], pos[i + 1], None]
fig = go.Figure()
for lvl, label in LEVEL_LABELS.items():
    xs, ys = sections[lvl]
    fig.add_scatter(x=xs, y=ys, mode="lines", name=label, hoverinfo="skip",
                    line=dict(color=LEVEL_COLORS[lvl], width=3 if lvl > 1 else 2))
points = runs.assign(text=runs["operator_name"].astype(str) + " " + runs["train"].astype(str) + " · "
                     + runs["stop_id"].map(names) + " · " + runs[col].map(level_text))
fig.add_scatter(x=points["departure"], y=points["pos"], mode="markers", showlegend=False,
                marker=dict(size=4, color="#848484"), text=points["text"],
                hovertemplate="%{x|%H:%M} %{text}<extra></extra>")
fig.update_layout(height=max(380, 26 * len(labels)), margin=dict(t=10, b=10),
                  legend=dict(orientation="h", y=1.05),
                  xaxis=dict(tickformat="%H:%M", showgrid=True, gridcolor="#e5e5e5"),
                  yaxis=dict(tickvals=list(range(len(labels))), ticktext=labels, autorange="reversed"))
st.plotly_chart(fig, width="stretch")
st.caption("Stops come from the longest train in this direction; stops that only other trains serve are left out. "
           "Lines come from the GTFS timetable, matched on the train number.")
