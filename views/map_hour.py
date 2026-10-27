import numpy as np
import pydeck as pdk
import streamlit as st

from views.common import SWISS_VIEW, context, rgb, station_hour

date, fare_class = context()
st.title("Stations by hour")
data = station_hour()
day = data[(data["date"] == date) & (data["fare_class"] == fare_class)]

hour = st.slider("Hour of departure", 0, 23, 17)
view = day[day["hour"] == hour].assign(
    color=lambda d: rgb("Viridis", d["share_crowded"] / 0.6),
    radius=lambda d: 300 + 250 * np.sqrt(d["departures"]),
    crowded_pct=lambda d: (100 * d["share_crowded"]).round(0),
    standing_pct=lambda d: (100 * d["share_standing"]).round(0),
)
st.pydeck_chart(pdk.Deck(
    layers=[pdk.Layer("ScatterplotLayer", view, get_position=["lon", "lat"], get_fill_color="color",
                      get_radius="radius", opacity=0.85, pickable=True, stroked=True,
                      get_line_color=[255, 255, 255], line_width_min_pixels=0.5)],
    initial_view_state=SWISS_VIEW,
    tooltip={"text": "{name}\n{departures} departures\n{crowded_pct}% crowded\n{standing_pct}% standing room only"},
    map_style="light",
), height=560)
c1, c2, c3 = st.columns(3)
c1.metric("Departures in this hour", f"{int(view['departures'].sum()):,}")
crowded = (view["share_crowded"] * view["departures"]).sum() / max(view["departures"].sum(), 1)
c2.metric("Crowded", f"{100 * crowded:.0f}%")
c3.metric("Stations with standing room only", int((view["share_standing"] > 0).sum()))
st.caption("Colour: share of crowded departures (viridis, clipped at 60%). Size: number of departures.")
