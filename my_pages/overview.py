import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from utils.data_loader import get_drive, load_kml_file
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px

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
        status_off = sub_df[sub_df["Status"].str.lower().str.contains("cut")].shape[0]

        with cols[i]:
            st.markdown(f"""
                <div style="
                    background-color: {get_card_color(reg)};
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
                    <p style="margin: 0; font-size: 16px;"><b>Site Cut Off:</b> {status_off}</p>
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

    gdf = st.session_state.get("cdc_sites_gdf")
    if gdf is None or gdf.empty:
        st.warning("Data is not available. Please refresh from Tab 1.")
        return

    # Use 1:2 ratio layout (wider pie chart column now)
    col1, col2 = st.columns([2, 4])

    # ----- DONUT CHART: Status Breakdown -----
    with col1:
        status_counts = gdf["Status"].str.strip().str.lower().value_counts()
        on_count = status_counts.get("on service", 0)
        off_count = status_counts.get("cut off", 0)
        total_sites = on_count + off_count

        donut_fig = go.Figure(data=[go.Pie(
            labels=["On Service", "Cut Off"],
            values=[on_count, off_count],
            hole=0.55,
            textinfo="label+percent+value",
            marker=dict(
                colors=["mediumseagreen", "lightcoral"],  # 🌈 More visible colors
                line=dict(color="white", width=2)         # ✏️ Add border
            ),
            textfont=dict(size=18, color="white"),
            showlegend=False
        )])

        donut_fig.update_layout(
            title=dict(
                text="Site Status Distribution",
                x=0.05,
                font=dict(size=20)
            ),
            annotations=[dict(
                text=f"<b>{total_sites} Sites</b>",
                x=0.5,
                y=0.5,
                font=dict(size=40),
                showarrow=False
            )],
            height=500,
            hoverlabel=dict(
                font_size=16,
                bgcolor="lightyellow",
                font_family="Arial",
                font_color="black"
            ),
            margin=dict(t=80, b=20, l=0, r=0)
        )

        st.plotly_chart(donut_fig, use_container_width=True)

    # ----- BAR CHART: Regional Breakdown -----
    with col2:
        regional_counts = gdf["Regional"].value_counts().reset_index()
        regional_counts.columns = ["Regional", "Count"]

        custom_order = [
            "Sumbagteng", "Sumbagsel", "Jawa Timur",
            "Bali Nusra", "Kalimantan", "Sulawesi", "Puma"
        ]
        bar_fig = px.bar(
            regional_counts,
            x="Regional",
            y="Count",
            color="Regional",
            color_discrete_sequence=px.colors.qualitative.Set2,
            #title="Number of Sites per Regional",
            text_auto=True,
            category_orders={"Regional": custom_order}
        )
        # Increase text label size
        bar_fig.update_traces(
            textfont=dict(size=16, color="black"),
            hoverlabel=dict(
                font_size=16,
                bgcolor="lightyellow",
                font_family="Arial",
                font_color="black"
            )
        )
        bar_fig.update_layout(
            title=dict(
                text="Number of Sites per Regional",
                font=dict(size=20, family="Segoe UI", color="black"),
                x=0.0  # Center-align the title
            ),
            xaxis=dict(
                title=dict(
                    text="Regional",
                    font=dict(size=16)  # ✅ X-axis title font size
                ),
                tickfont=dict(size=16)  # ✅ X-axis tick labels
            ),
            yaxis=dict(
                title=dict(
                    text="Total Sites",
                    font=dict(size=16)  # ✅ Y-axis title font size
                ),
                tickfont=dict(size=14)  # ✅ Y-axis tick labels
            ),
            showlegend=False,
            height=500,
            margin=dict(t=60, b=20)
        )

        st.plotly_chart(bar_fig, use_container_width=True)
    
    st.markdown("---")  # horizontal divider

    # New row for Site Class charts
    class_col1, class_col2 = st.columns([1, 2])

    # ----- BAR CHART: Distribution by Site Class -----
    with class_col1:
        site_class_counts = gdf["Site Class"].value_counts().reset_index()
        site_class_counts.columns = ["Site Class", "Count"]

        custom_order = ["Platinum", "Gold", "Silver", "Bronze"]

        class_bar = px.bar(
            site_class_counts,
            x="Count",
            y="Site Class",  # Horizontal bar
            color="Site Class",
            orientation="h",
            text_auto=True,
            color_discrete_sequence=px.colors.qualitative.Set2,
            category_orders={"Site Class": custom_order}  # << Set desired order
        )

        class_bar.update_layout(
            title="Site Distribution by Site Class",
            title_font_size=20,
            xaxis_title="Total Sites",
            yaxis_title="Site Class",
            xaxis=dict(title_font=dict(size=16), tickfont=dict(size=16)),
            yaxis=dict(title_font=dict(size=16), tickfont=dict(size=16)),
            showlegend=False,
            height=500,
            margin=dict(t=60, b=20)
        )

        class_bar.update_traces(
            textfont=dict(size=16),
            hoverlabel=dict(
                font_size=16,
                bgcolor="mintcream",
                font_family="Arial",
                font_color="black"
            )
        )

        st.plotly_chart(class_bar, use_container_width=True)

    with class_col2:
        grouped = gdf.groupby(["Regional", "Site Class"]).size().reset_index(name="Count")

        regional_order = ["Sumbagteng", "Sumbagsel", "Jawa Timur", "Bali Nusra", "Kalimantan", "Sulawesi", "Puma"]
        site_class_order = ["Bronze", "Silver", "Gold", "Platinum"]

        class_facet = px.bar(
            grouped,
            x="Site Class",
            y="Count",
            color="Site Class",
            facet_col="Regional",
            category_orders={
                "Regional": regional_order,
                "Site Class": site_class_order
            },
            color_discrete_sequence=px.colors.qualitative.Pastel
        )

        class_facet.update_layout(
            title=dict(
                text="📊 Site Class Distribution per Regional (Faceted)",
                font=dict(size=20),
                y=0.95,  # Keep the title near the top (0.0 = bottom, 1.0 = top)
                yanchor="top"
            ),
            height=500,
            margin=dict(t=100, b=80),
            font=dict(size=12),  # affects all text unless overridden
            annotations=[dict(font=dict(size=16)) for _ in class_facet.layout.annotations],
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.25,
                xanchor="center",
                x=0.5,
                font=dict(size=14)
            ),
            showlegend=False
        )

        class_facet.update_traces(
            texttemplate="%{y}",
            textposition="outside",
            textfont_size=16,
            hoverlabel=dict(
                font_size=16,
                bgcolor="lavender",
                font_family="Arial",
                font_color="black"
            )
        )
        class_facet.update_xaxes(
            tickangle=-45,
            title=None,
            title_font=dict(size=14),
            tickfont=dict(size=14)
        )
        class_facet.update_yaxes(
            #title="Total Sites",
            range=[0, 32],
            title_font=dict(size=14),
            tickfont=dict(size=14)
        )
        # Adjust facet label position and text together
        for annotation in class_facet.layout.annotations:
            if "Regional=" in annotation.text:
                annotation.text = annotation.text.replace("Regional=", "")
                annotation.y += 0.03  # Adjust vertical position
            elif annotation.text in regional_order:
                annotation.y += 0.03  # Just adjust position if already clean

        st.plotly_chart(class_facet, use_container_width=True)

def app():
    st.title("CDC Overview Dashboard")

    col1, col2 = st.columns([9, 1])
    with col1:
        st.title("🎟️ CDC Overview")
    with col2:
        if st.button("🔄 Refresh Data", help="Reload data"):
            st.cache_data.clear()
            st.session_state.pop("cdc_sites_gdf", None)  # Clear only this key
            st.rerun()

    # Load data only if not already in session state
    if "cdc_sites_gdf" not in st.session_state:
        with st.spinner("Loading CDC site data..."):
            drive = get_drive()
            gdf = load_kml_file(drive)
            st.session_state["cdc_sites_gdf"] = gdf

    tab1, tab2 = st.tabs(["📍 Site Map", "📊 CDC Site Summary"])

    with tab1:
        app_tab1()

    with tab2:
        app_tab2()
