import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from utils.data_loader import get_drive, load_kml_file
import folium
from streamlit_folium import st_folium 

# Utility: define color per Regional
def get_color(regional):
    color_map = {
        'Sumbagteng': 'red',
        'Sumbagut': 'purple',
        'Sumbagsel': 'pink',
        'Jawa Timur': 'green',
        'Jawa Tengah': 'blue',
        'Jawa Barat': 'orange',
        'Kalimantan': 'cadetblue',
        'Bali Nusra': 'lightgreen',
        'Sulawesi': 'beige',
        'Puma' : 'lightred'
    }
    return color_map.get(regional, 'gray')

# --- Regional color mapping ---
REGIONAL_COLORS = {
    "Bali Nusra": "lightpink",
    "Jawa Timur": "palegreen",
    "Kalimantan": "lightsalmon",
    "Puma": "powderblue",
    "Sulawesi": "lightyellow",
    "Sumbagsel": "papayawhip",
    "Sumbagteng": "peachpuff"
}

def get_card_color(regional):
    return REGIONAL_COLORS.get(regional, "#dfe6e9")  # default light gray if not found

def app_tab1():
    col1, col2 = st.columns([9, 1])  # Title wide, button narrow

    with col1:
        st.markdown("### 📍 Site Locations Map")

    with col2:
        refresh = st.button("🔄 Refresh from Drive", help="Reload the latest KML file")
    
    #--- Load data only once per session ---
    if refresh or "cdc_sites_gdf" not in st.session_state:
        with st.spinner("Loading site data..."):
            drive = get_drive()
            gdf = load_kml_file(drive)
        st.session_state["cdc_sites_gdf"] = gdf

    gdf = st.session_state["cdc_sites_gdf"]

    if gdf.empty:
        st.warning("No data to display. Please check your KML file.")
        return

    # --- Summary Cards: Regional Info ---
    #st.markdown("#### 🗂️ Site Summary by Regional")

    unique_regionals = sorted(gdf["Regional"].dropna().unique())
    cols = st.columns(len(unique_regionals))  # One column per Regional

    for i, reg in enumerate(unique_regionals):
        sub_df = gdf[gdf["Regional"] == reg]

        total_sites = len(sub_df)
        class_counts = sub_df["Site Class"].value_counts().to_dict()
        status_on = sub_df[sub_df["Status"].str.lower().str.contains("on")].shape[0]

        with cols[i]:
            st.markdown(f"""
                <div style="
                    background-color: {get_color(reg)};
                    border-radius: 12px;
                    padding: 15px 20px;
                    margin-bottom: 10px;
                    box-shadow: 1px 1px 6px rgba(0, 0, 0, 0.1);
                    font-family: 'Segoe UI', sans-serif;
                ">
                    <h5 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 22px;">{reg}</h5>
                    <p style="margin: 0; font-size: 16px;"><b>Total Sites:</b> {total_sites}</p>
                    <p style="margin: 0; font-size: 16px;">
                        <b>Class:</b> 
                        Platinum ({class_counts.get('Platinum', 0)}), 
                        Gold ({class_counts.get('Gold', 0)}), 
                        Silver ({class_counts.get('Silver', 0)}), 
                        Bronze ({class_counts.get('Bronze', 0)})
                    </p>
                    <p style="margin: 0; font-size: 16px;"><b>Site On Service:</b> {status_on}</p>
                </div>
            """, unsafe_allow_html=True)

    # Ensure lat/lon columns
    if "Latitude" not in gdf.columns or "Longitude" not in gdf.columns:
        gdf["Latitude"] = gdf.geometry.y
        gdf["Longitude"] = gdf.geometry.x

    # --- Folium map setup ---
    m = folium.Map(location=[-2, 118], zoom_start=5)

    for _, row in gdf.iterrows():
        popup_html = f"""
        <div style="font-size: 14px; font-family: Arial, sans-serif;">
            <b>Site ID:</b> {row.get('Site Id', row.get('Name', ''))}<br>
            <b>Site Name:</b> {row.get('Site Name', '')}<br>
            <b>Longitude:</b> {row.get('Longitude', '')}<br>
            <b>Latitude:</b> {row.get('Latitude', '')}<br>
            <b>Area:</b> {row.get('Area', '')}<br>
            <b>Regional:</b> {row.get('Regional', '')}<br>
            <b>NS:</b> {row.get('NS', '')}<br>
            <b>Site Class:</b> {row.get('Site Class', '')}<br>
            <b>Target AVA:</b> {row.get('Target', '')}<br>
            <b>Status:</b> {row.get('Status', '')}
        </div>
        """
        if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                tooltip=row.get("Site Name", ""),
                popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=get_color(row.get("Regional")))
            ).add_to(m)

    st.markdown("""
        <style>
        .folium-map {
            height: 90vh !important;
        }
        </style>
    """, unsafe_allow_html=True)

    folium_static(m, width=2015, height=800)
# --- TAB 2: Summary View ---
def app_tab2():
    st.subheader("📊 CDC Sites Summary")

    # Placeholder content – update with your own summary logic
    st.info("This section will contain CDC site summary statistics, KPIs, charts, etc.")
    # Example:
    # - Total number of sites
    # - Site distribution by class/region
    # - Availability stats
    # - Achievement by region

def app():
    st.title("CDC Overview Dashboard")
    col1, col2 = st.columns([9, 1])
    with col1:
        st.title("🎟️ CDC Overview")
    with col2:
        if st.button("🔄 Refresh Data", help="Reload availability data"):
            st.cache_data.clear()
            st.rerun()
            
    drive = get_drive()
    gdf = load_kml_file(drive)  # This loads the KML file into gdf

    tab1, tab2 = st.tabs(["📍 Site Map", "📊 Other Tab"])

    with tab1:
        app_tab1()

    with tab2:
        st.info("Other tab content here...")
