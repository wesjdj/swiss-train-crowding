import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from crowding.theme import DIVERGING
from views.common import SWISS_VIEW, context, load, rgb, station_hour

_, fare_class = context()
st.title("Commuter tide")
st.markdown(
    "On weekdays, is a station crowded more in the **morning** (06:00–09:00) or in the **evening** "
    "(16:00–19:00)? Tilt = (morning − evening) / (morning + evening), from the mean level above *many seats*. "
    "City hubs are crowded in the evening, when people go home. Small towns and border stations are "
    "crowded in the morning, when commuters leave."
)
data = station_hour()
wk = data[(pd.to_datetime(data["date"]).dt.day_of_week < 5) & (data["fare_class"] == fare_class)]
wk = wk.assign(load=(wk["mean_level"] - 1) * wk["departures"],
               window=np.select([wk["hour"].between(6, 8), wk["hour"].between(16, 18)], ["am", "pm"], "other"))
agg = wk[wk["window"] != "other"].groupby(["stop_id", "window"])[["load", "departures"]].sum()
per = (agg["load"] / agg["departures"]).unstack().fillna(0)
total = wk.groupby("stop_id")["departures"].sum()
per = per[(per["am"] + per["pm"] > 0.25) & (total.reindex(per.index) >= 400)]
per["tilt"] = (per["am"] - per["pm"]) / (per["am"] + per["pm"])
tide = per.reset_index().merge(load("stations"), on="stop_id")
tide["color"] = rgb([[i / 4, c] for i, c in enumerate(DIVERGING)], (tide["tilt"] + 1) / 2)
tide["tilt_txt"] = tide["tilt"].round(2)
st.pydeck_chart(pdk.Deck(
    layers=[pdk.Layer("ScatterplotLayer", tide, get_position=["lon", "lat"], get_fill_color="color",
                      get_radius=2200, opacity=0.9, pickable=True, stroked=True,
                      get_line_color=[120, 120, 120], line_width_min_pixels=0.5)],
    initial_view_state=SWISS_VIEW,
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
