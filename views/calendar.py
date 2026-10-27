import plotly.express as px
import streamlit as st

from crowding.theme import LEVEL_COLORS
from views.common import context, load

_, fare_class = context()
st.title("Next 3 months")
daily = load("daily_levels")
d = (daily[(daily["fare_class"] == fare_class) & daily["level"].notna()]
     .groupby(["date", "level"])["n"].sum().unstack())
share = (d[[2, 3]].sum(axis=1) / d.sum(axis=1)).rename("crowded").reset_index()
share["weekday"] = share["date"].dt.day_name()
fig = px.bar(share, x="date", y="crowded", hover_data={"weekday": True},
             labels={"crowded": "Share of crowded departures", "date": ""})
fig.update_traces(marker_color=LEVEL_COLORS[3])
fig.update_layout(height=380, yaxis_tickformat=".0%", margin=dict(t=10))
st.plotly_chart(fig, width="stretch")
st.caption("All forecast days in the source file. The weekly pattern is clear: Sundays are the quietest days. "
           "Christmas Day and New Year's Day are the quietest days of all.")
