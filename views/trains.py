import pandas as pd
import streamlit as st

from views.common import context, load, train_text

date, _ = context()
st.title("Busiest trains")
trains = load("trains")

full = trains[(trains["date"] == date) & (trains["max_2nd"] == 3)]
top = full.sort_values(["standing_stops_2nd", "stops"], ascending=False).head(25)
st.markdown(f"**{len(full)}** trains have *standing room only* in 2nd class at one or more stops "
            "on this date. These are the 25 with the most such stops:")
st.dataframe(
    pd.DataFrame({
        "Train": train_text(top),
        "Start": top["start"].dt.strftime("%H:%M"),
        "From": top["from"], "To": top["to"],
        "Stops with standing room only": top["standing_stops_2nd"].astype(str) + " of " + top["stops"].astype(str),
    }),
    hide_index=True, width="stretch",
)

by_line = (full.groupby("line_label").size().sort_values(ascending=False).head(15)
           .rename("Trains with standing room only").reset_index().rename(columns={"line_label": "Line"}))
st.subheader("Lines with the most such trains")
st.dataframe(by_line, hide_index=True, width="stretch")
st.caption("Open a line in the *Line explorer* to see where and when it is crowded.")
