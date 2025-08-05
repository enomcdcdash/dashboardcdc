import streamlit as st

def navigation():
    with st.sidebar:
        # --- Inject custom button CSS style ---
        button_style = """
        <style>
        div.stButton > button {
            width: 100%;
            text-align: center;
            background-color: #2F5597;
            color: white;
            font-weight: 500;
            padding: 0.5em 1em;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        </style>
        """
        st.markdown(button_style, unsafe_allow_html=True)

        # --- Sidebar header ---
        st.markdown("""
            <div style='text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 10px;'>
                📊 Dashboard CDC
            </div>
        """, unsafe_allow_html=True)

        # --- Logo ---
        st.markdown("""
            <div style="text-align: center; margin-bottom: 15px;">
                <img src="https://portal.telkominfra.com/resources/img/telkominfra-logo-2.png" width="200">
            </div>
        """, unsafe_allow_html=True)

        # --- Divider ---
        st.markdown("<hr style='margin-top: 0; margin-bottom: 15px;'>", unsafe_allow_html=True)

        # --- Persistent page selection ---
        if "selected_page" not in st.session_state:
            st.session_state.selected_page = "CDC Overview"

        # --- Navigation buttons ---
        if st.button("📈 CDC Overview", use_container_width=True):
            st.session_state.selected_page = "CDC Overview"
        if st.button("🧮 Pengisian BBM", use_container_width=True):
            st.session_state.selected_page = "Pengisian BBM"
        if st.button("🎟️ Availability", use_container_width=True):
            st.session_state.selected_page = "Availability"
        if st.button("⚖️ Penalty Tracker", use_container_width=True):
            st.session_state.selected_page = "Penalty Tracker"
        if st.button("⚙️ Tracker TDE Activity", use_container_width=True):
            st.session_state.selected_page = "Tracker TDE"
        
    return st.session_state.selected_page

