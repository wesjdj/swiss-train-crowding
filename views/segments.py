import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

from views.common import SWISS_VIEW, context, load, rgb

date, fare_class = context()
st.title("Crowded segments")
st.markdown(
    "Each line is the stretch between two stops that a train serves one after the other, in both directions. "
    "The colour shows the share of trains that are crowded when they leave the first stop of the stretch."
)
hour = st.slider("Hour of departure", 0, 23, 17)

seg = load("segments")
stations = load("stations")[["stop_id", "name", "lon", "lat"]]
view = seg[(seg["date"] == date) & (seg["fare_class"] == fare_class) & (seg["hour"] == hour)]
view = (view.merge(stations.add_suffix("_a"), left_on="a", right_on="stop_id_a")
        .merge(stations.add_suffix("_b"), left_on="b", right_on="stop_id_b"))
km_lat = 111.0
km_lon = km_lat * np.cos(np.radians(46.8))
view = view.assign(
    length=np.hypot((view["lon_a"] - view["lon_b"]) * km_lon, (view["lat_a"] - view["lat_b"]) * km_lat),
    color=lambda d: rgb("Viridis", d["share_crowded"] / 0.6),
    width=lambda d: 1.5 + 1.2 * np.sqrt(d["trains"]),
    crowded_pct=lambda d: (100 * d["share_crowded"]).round(0),
    standing_pct=lambda d: (100 * d["share_standing"]).round(0),
).sort_values(["length", "share_crowded"], ascending=[False, True])

st.pydeck_chart(pdk.Deck(
    layers=[pdk.Layer("LineLayer", view, get_source_position=["lon_a", "lat_a"],
                      get_target_position=["lon_b", "lat_b"], get_color="color", get_width="width",
                      pickable=True, auto_highlight=True)],
    initial_view_state=SWISS_VIEW,
    tooltip={"text": "{name_a} – {name_b}\n{trains} trains\n{crowded_pct}% crowded\n{standing_pct}% standing room only"},
    map_style="dark",
), height=600)
st.caption("Colour: share of crowded trains (viridis, clipped at 60%). Width: number of trains in this hour. "
           "Express trains that skip stops show as long straight lines under the local lines.")

top = view[view["trains"] >= 2].sort_values(["share_standing", "share_crowded", "trains"], ascending=False).head(15)
st.subheader("Most crowded stretches in this hour")
st.dataframe(
    pd.DataFrame({
        "Stretch": top["name_a"] + " – " + top["name_b"],
        "Trains": top["trains"],
        "Crowded": top["crowded_pct"].astype(int).astype(str) + "%",
        "Standing room only": top["standing_pct"].astype(int).astype(str) + "%",
    }),
    hide_index=True, width="stretch",
)
