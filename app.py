import streamlit as st
from sidebar import navigation
from my_pages import availability, overview, tracker_bbm

st.set_page_config(page_title="CDC Dashboard", layout="wide")
# st.write("Available secrets keys:", list(st.secrets.keys()))
# --- Use sidebar navigation ---
selected_page = navigation()

# --- Page routing logic ---
if selected_page == "CDC Overview":
    from my_pages import overview
    overview.app()
elif selected_page == "Pengisian BBM":
    from my_pages import tracker_bbm
    tracker_bbm.app()
elif selected_page == "Availability":
    from my_pages import availability
    availability.app()
elif selected_page == "Penalty Tracker":
    from my_pages import penalty
    penalty.app()

