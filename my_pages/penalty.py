import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils.data_loader import get_drive, load_penalty_data, load_availability_vs_penalty_data
from io import BytesIO
import io
from utils.helper import render_html_table_with_scroll, prepare_penalty_table

def app_tab2():
    st.subheader("📌 Still on Development Phase")
    st.markdown("Please Stay tuned..")

def app_tab1():
    st.markdown("## Availability vs Penalty Data")
    
    df = load_availability_vs_penalty_data()
    if df.empty:
        st.warning("No data to display.")
        return

    # Define Area to Regional TI mapping
    area_to_regional = {
        "Area 1": ["Sumbagsel", "Sumbagteng"],
        "Area 3": ["Balnus", "Jatim"],
        "Area 4": ["Kalimantan", "Puma", "Sulawesi"]
    }

    # 1. Create filters in one row
    col_area, col_regional, col_site = st.columns([3, 3, 3])

    # Area filter
    area_options = ["All"] + list(area_to_regional.keys())
    selected_area = col_area.selectbox("Select Area", area_options, index=0)

    # Filter Regional TI options based on Area selection
    if selected_area == "All":
        regional_options = ["All"] + sorted(df["Regional TI"].dropna().unique().tolist())
    else:
        regional_options = ["All"] + area_to_regional.get(selected_area, [])

    selected_regional = col_regional.selectbox("Select Regional TI", regional_options, index=0)

    # Filter Site Id options based on Regional TI selection
    if selected_regional == "All":
        if selected_area == "All":
            site_options = ["All"] + sorted(df["Site Id"].dropna().unique().tolist())
        else:
            # Sites within Area's Regional TIs
            sites_in_area = df[df["Regional TI"].isin(area_to_regional[selected_area])]["Site Id"].unique().tolist()
            site_options = ["All"] + sorted(sites_in_area)
    else:
        # Sites within selected Regional TI
        sites_in_regional = df[df["Regional TI"] == selected_regional]["Site Id"].unique().tolist()
        site_options = ["All"] + sorted(sites_in_regional)

    selected_site = col_site.selectbox("Select Site Id", site_options, index=0)

    # 2. Filter DataFrame based on selections
    filtered_df = df.copy()

    if selected_area != "All":
        filtered_df = filtered_df[filtered_df["Regional TI"].isin(area_to_regional[selected_area])]

    if selected_regional != "All":
        filtered_df = filtered_df[filtered_df["Regional TI"] == selected_regional]

    if selected_site != "All":
        filtered_df = filtered_df[filtered_df["Site Id"] == selected_site]

    if filtered_df.empty:
        st.warning("No data for the selected filters.")
        return

    # Prepare data for plotting
    # Create Month-Year string for x-axis, e.g. "January-2025"
    filtered_df["Month-Year"] = filtered_df.apply(lambda r: f"{r['Month']}-{r['Year']}", axis=1)

    # Sort by Year and Month order to make line chart smooth
    filtered_df["Month_Num"] = pd.to_datetime(filtered_df["Month-Year"], format="%B-%Y").dt.month
    filtered_df = filtered_df.sort_values(by=["Year", "Month_Num"])

    #import plotly.graph_objects as go

    x_vals = filtered_df["Month-Year"].unique()

    # Step 1: Add Status column for each row in original data (not aggregated)
    filtered_df["Status"] = filtered_df.apply(
        lambda row: "Achieved" if row["Availability"] >= row["Target Availability (%)"] else "Not Achieved",
        axis=1
    )

    # Step 2: Aggregate for lines (mean/sum)
    agg_df = filtered_df.groupby("Month-Year").agg({
        "Availability": "mean",
        "Target Availability (%)": "mean",
        "Persentase Penalty": "mean",
        "Nilai Penalty": "sum"
    }).reindex(x_vals)

    agg_df["Availability_fmt"] = agg_df["Availability"].map(lambda x: f"{x*100:.2f}%")
    agg_df["Target_Availability_fmt"] = agg_df["Target Availability (%)"].map(lambda x: f"{x*100:.2f}%")
    agg_df["Persentase_Penalty_fmt"] = agg_df["Persentase Penalty"].map(lambda x: f"{x*100:.2f}%")
    agg_df["Nilai_Penalty_fmt"] = agg_df["Nilai Penalty"].map(lambda x: f"Rp {int(x):,}".replace(",", "."))

    agg_df["Availability_pct"] = agg_df["Availability"] * 100
    agg_df["Target_Availability_pct"] = agg_df["Target Availability (%)"] * 100
    agg_df["Persentase_Penalty_pct"] = agg_df["Persentase Penalty"] * 100

    # Step 3: Count Achieved and Not Achieved per Month-Year
    status_counts = filtered_df.groupby(["Month-Year", "Status"]).size().unstack(fill_value=0).reindex(x_vals, fill_value=0)

    # Make sure columns exist even if some are missing
    if "Achieved" not in status_counts.columns:
        status_counts["Achieved"] = 0
    if "Not Achieved" not in status_counts.columns:
        status_counts["Not Achieved"] = 0

    main_title = "Availability vs. Penalty"

    # Default info_line
    info_line = ""

    # Create a combined Month-Year column in "YYYY-MM" format (string)
    df['Month-Year'] = df['Year'].astype(str) + '-' + df['Month'].astype(str).str.zfill(2)
    # Helper: get latest month available in df (or filtered_df)
    latest_month = df["Month-Year"].max()

    if selected_site != "All":
        # One Site selected - show Site Id + Class Site + Site Name from latest month
        site_id = selected_site
        # Filter for latest month and selected site
        latest_site_data = df[(df["Site Id"] == site_id) & (df["Month-Year"] == latest_month)]
        if not latest_site_data.empty:
            site_class = latest_site_data.iloc[0].get("Class Site", "Unknown")
            site_name = latest_site_data.iloc[0].get("Site Name", "Unknown")
            info_line = (
                f"Site ID: <b style='color:green'>{site_id}</b> | "
                f"Site Name: <b style='color:green'>{site_name}</b> | "
                f"Site Class: <b style='color:green'>{site_class}</b>"
            )
        else:
            info_line = f"Site ID: <b>{site_id}</b>"

    elif selected_regional != "All":
        # One Regional selected - show Area and Regional info
        # We assume selected_area still holds the Area for this Regional
        info_line = f"Area: <b>{selected_area}</b> | Regional: <b>{selected_regional}</b>"

    elif selected_area != "All":
        # One Area selected - show Area info only
        info_line = f"Area: <b>{selected_area}</b>"

    else:
        # Default fallback for multiple or no specific selection
        info_line = "All Areas"

    fig = go.Figure()

    # Add stacked bar chart for counts on new yaxis 'y3'
    fig.add_trace(go.Bar(
        x=status_counts.index,
        y=status_counts["Achieved"],
        name="Achieved",
        marker_color="lightblue",
        yaxis="y3",
        opacity=0.3,
        text=status_counts["Achieved"],        # Add labels showing the count
        textposition='inside',                  # Position text inside the bar
        insidetextanchor='start',
        textfont=dict(size=14, color="black"),
        hovertemplate="Ava Achieved :</b> %{y} sites<extra></extra>"
    ))

    fig.add_trace(go.Bar(
        x=status_counts.index,
        y=status_counts["Not Achieved"],
        name="Not Achieved",
        marker_color="lightpink",
        yaxis="y3",
        opacity=0.3,
        #text=status_counts["Not Achieved"],
        #textposition='inside',
        #insidetextanchor='start',
        #textfont=dict(size=14, color="black"),
        hovertemplate="Ava Not Achieved :</b> %{y} sites<extra></extra>"
    ))

    # Add line traces with labels
    fig.add_trace(go.Scatter(
        x=agg_df.index,
        y=agg_df["Availability_pct"],
        mode='lines+markers+text',
        name="Availability",
        line=dict(color='blue', width=4),
        text=agg_df["Availability_fmt"],
        textposition='top center',
        textfont=dict(color='blue', size=16),
        hovertemplate='Availability: %{customdata[0]}<extra></extra>',
        customdata=agg_df[["Availability_fmt"]]
    ))

    fig.add_trace(go.Scatter(
        x=agg_df.index,
        y=agg_df["Target_Availability_pct"],
        mode='lines+markers',
        name="Target Availability (%)",
        line=dict(color='darkgreen', dash='dash', width=6),
        hovertemplate='Target Availability: %{customdata[0]}<extra></extra>',
        customdata=agg_df[["Target_Availability_fmt"]]
    ))

    fig.add_trace(go.Scatter(
        x=agg_df.index,
        y=agg_df["Persentase_Penalty_pct"],
        mode='lines+markers+text',
        name="Persentase Penalty",
        line=dict(color='red', width=4),
        text=agg_df["Persentase_Penalty_fmt"],
        textposition='top center',
        textfont=dict(color='red', size=16),
        hovertemplate='Persentase Penalty: %{customdata[0]}<extra></extra>',
        customdata=agg_df[["Persentase_Penalty_fmt"]]
    ))

    fig.add_trace(go.Scatter(
        x=agg_df.index,
        y=agg_df["Nilai Penalty"],
        mode='lines+markers+text',
        name="Nilai Penalty",
        yaxis='y2',
        line=dict(color='orange', width=4),
        text=agg_df["Nilai_Penalty_fmt"],
        textposition='top center',
        textfont=dict(color='black', size=16),
        hovertemplate='Nilai Penalty: %{customdata[0]}<extra></extra>',
        customdata=agg_df[["Nilai_Penalty_fmt"]]
    ))

    fig.update_layout(
        title=dict(
            text=f"<b>{main_title}</b><br><span style='font-size:16px; color:gray'>{info_line}</span>",
            font=dict(size=28, color='black'),
            x=0.5,
            xanchor='center',
            y=0.95,
            yanchor='top'
        ),
        barmode="stack",
        xaxis_title="Month-Year",
        xaxis=dict(
            tickfont=dict(size=16),
            tickangle=-45,
        ),
        yaxis=dict(
            title="Percentage / Availability",
            range=[0, 110],
            tickformat=".0f",
            tickfont=dict(size=16),
            showgrid=False,
        ),
        yaxis2=dict(
            title="Nilai Penalty",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=16)
        ),
        
        yaxis3=dict(
            showline=False,    # Hide the axis line
            showticklabels=False,  # Hide tick labels
            showgrid=False,    # Hide grid lines
            zeroline=False,    # Hide zero line if any
            title='',          # Remove axis title
            overlaying='y',
            side='right',
            position=0.95,
            anchor='x',
            rangemode='tozero',
        ),
        legend=dict(
            x=1,           # x=1 means right edge of the plotting area
            y=-0.4,           # y=0 means bottom of the plotting area
            xanchor='right',  # anchor the legend's right side at x=1
            yanchor='bottom', # anchor the legend's bottom at y=0
            orientation='h',  # horizontal legend
            bgcolor='rgba(255,255,255,0.5)',  # optional: semi-transparent background for better readability
            bordercolor='black',               # optional border color
            borderwidth=1,
            font=dict(
                size=14,       # font size in pixels
                color='blue'   # font color
            )
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="azure",
            font_size=16,
            font_family="Arial",
            font_color="black",
            bordercolor="gray",
            namelength=-1,
        ),
        height=700,
        margin=dict(l=40, r=60, t=100, b=80)
    )

    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### Tabel Penalty")
    penalty_table_df = prepare_penalty_table(filtered_df)

    # Ensure clean DataFrame (no multi-index, no index name)
    penalty_table_df = penalty_table_df.reset_index(drop=True)
    penalty_table_df.columns = penalty_table_df.columns.astype(str)

    # Convert Month to datetime (assuming format like "April-2025")
    penalty_table_df["Month"] = pd.to_datetime(
        penalty_table_df["Month"], format="%B-%Y"
    )
    # Sort it properly
    penalty_table_df = penalty_table_df.sort_values(
        by=["Month", "Regional TI", "Site Id"]
    ).reset_index(drop=True)
    # Display back as "Month-Year"
    penalty_table_df["Month"] = penalty_table_df["Month"].dt.strftime("%B-%Y")

    # Format percentage columns safely
    for col in ["Target Availability (%)", "Availability", "Gap Ava"]:
        if col in penalty_table_df.columns:
            penalty_table_df[col] = (
                pd.to_numeric(penalty_table_df[col], errors="coerce") * 100
            ).fillna(0).map("{:.2f}%".format)

    # Render table
    html_table = render_html_table_with_scroll(penalty_table_df, max_height=450)
    st.markdown(html_table, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Chart Data")

    with st.expander("📋 Show Filtered Data Table"):
        if df.empty:
            st.warning("No data available to display.")
        else:
            # Show dataframe with default Streamlit table
            st.dataframe(filtered_df, use_container_width=True)
    
    # Create a BytesIO buffer
    buffer = io.BytesIO()

    # Save filtered_df to this buffer as Excel
    filtered_df.to_excel(buffer, index=False)
    buffer.seek(0)

    # Add a download button
    st.download_button(
        label="📥 Download Data",
        data=buffer,
        file_name="filtered_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# --- Main App Entry ---
def app():
    col1, col2 = st.columns([9, 1])
    with col1:
        st.title("📊 Penalty Tracker Dashboard")
    with col2:
        if st.button("🔄 Refresh Data", help="Reload availability data"):
            st.cache_data.clear()
            st.rerun()

    df_raw = load_penalty_data()

    if df_raw.empty:
        return

    tab1, tab2 = st.tabs(["📉 Availability vs Penalty Tracker", "Tab 2 (In Development)"])
    with tab1:
        app_tab1()

    with tab2:
        app_tab2()








