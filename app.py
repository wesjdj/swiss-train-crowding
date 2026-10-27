"""Streamlit app: explore the SBB occupancy forecast."""

import streamlit as st

from crowding.theme import use_plotly
from views.common import CLASSES, dates

st.set_page_config(page_title="Swiss train crowding", page_icon="🚆", layout="wide")
use_plotly()

days = dates()
with st.sidebar:
    labels = {f"{d:%a %Y-%m-%d}": d for d in days}
    st.session_state["date"] = labels[st.selectbox("Date", list(labels), key="date_label")]
    st.session_state["fare_class"] = CLASSES[st.radio("Class", list(CLASSES), key="class_label")]
    st.markdown(
        "**Crowded** means the forecast says *few seats* or *standing room only*.\n\n"
        "Stations outside Switzerland have no coordinates in the source list, so they are not on the maps."
    )
    st.caption(
        "Source: [Occupancy Forecast SIRI Dataset](https://opendata.swiss/en/dataset/occupancy-forecast-siri-dataset) "
        "and the GTFS timetable, opentransportdata.swiss. "
        f"Snapshot: {days[0]:%Y-%m-%d} to {days[-1]:%Y-%m-%d}."
    )

page = st.navigation({
    "Maps": [
        st.Page("views/map_hour.py", title="Stations by hour", icon=":material/location_on:", default=True),
        st.Page("views/segments.py", title="Crowded segments", icon=":material/route:"),
        st.Page("views/tide.py", title="Commuter tide", icon=":material/compare_arrows:"),
    ],
    "Plan a trip": [
        st.Page("views/planner.py", title="A → B planner", icon=":material/directions_railway:"),
        st.Page("views/station.py", title="Station board", icon=":material/departure_board:"),
    ],
    "Lines and trains": [
        st.Page("views/lines.py", title="Line explorer", icon=":material/timeline:"),
        st.Page("views/trains.py", title="Busiest trains", icon=":material/train:"),
    ],
    "Outlook": [
        st.Page("views/calendar.py", title="Next 3 months", icon=":material/calendar_month:"),
    ],
})
page.run()
