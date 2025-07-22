import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_daily_files, load_all_weekly_files
import random

@st.cache_data
def get_data():
    return load_all_daily_files()

def app_tab1(df):
    st.subheader("📌 Daily Availability Summary")

    # --- Preprocess ---
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['occurrence'] = pd.to_numeric(df['occurrence'], errors='coerce')
    df['outage_2g (Hour)'] = pd.to_numeric(df['outage_2g (Hour)'], errors='coerce')
    df['outage_4g (Hour)'] = pd.to_numeric(df['outage_4g (Hour)'], errors='coerce')
    df['availability (%)'] = pd.to_numeric(df['availability (%)'], errors='coerce')
    df = df.dropna(subset=['Date'])

    # --- Filters ---
    min_date, max_date = df['Date'].min(), df['Date'].max()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        date_range = st.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date, key="tab1_date_range")

    with col2:
        area_options = sorted(df['area'].dropna().unique())
        selected_area = st.selectbox("Area", area_options, key="tab1_area")

    with col3:
        reg_df = df[df['area'] == selected_area]
        reg_options = sorted(reg_df['regional'].dropna().unique())
        selected_regional = st.selectbox("Regional", reg_options, key="tab1_regional")

    with col4:
        site_df = reg_df[reg_df['regional'] == selected_regional]
        site_options = sorted(site_df['site_id'].dropna().unique())
        selected_siteid = st.selectbox("Site ID", site_options, index=random.randint(0, len(site_options)-1), key="tab1_siteid")

    if len(date_range) == 2:
        mask = (
            (df['Date'] >= pd.to_datetime(date_range[0])) &
            (df['Date'] <= pd.to_datetime(date_range[1])) &
            (df['area'] == selected_area) &
            (df['regional'] == selected_regional) &
            (df['site_id'] == selected_siteid)
        )

        filtered_df = df[mask].sort_values('Date')

        if filtered_df.empty:
            st.warning("No data found for the selected filters.")
            return
    else:
        st.info("Please select both a start and end date to continue.")
        return

    # --- Plot Chart ---
    fig = go.Figure()

    # Bar: Occurrence
    fig.add_trace(go.Bar(
        x=filtered_df['Date'],
        y=filtered_df['occurrence'],
        name='Occurrence',
        marker_color="#F7C989",
        yaxis='y1',
        text=filtered_df['occurrence'],
        textposition='auto',
        #insidetextanchor='start',
        textfont=dict(size=16, color='black')
    ))

    # Line: Outage 2G
    fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['outage_2g (Hour)'],
        mode='lines+markers',
        name='Outage 2G (Hr)',
        yaxis='y1',
        line=dict(color='#1f77b4', width=4)
    ))

    # Line: Outage 4G
    fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['outage_4g (Hour)'],
        mode='lines+markers',
        name='Outage 4G (Hr)',
        yaxis='y1',
        line=dict(color='#d62728', width=4)
    ))

    # Add formatted labels
    filtered_df['availability_label'] = filtered_df['availability (%)'].round(2).astype(str) + '%'
    filtered_df['outage_4g_label'] = filtered_df['outage_4g (Hour)'].round(2).astype(str) + ' hrs'

    # Line: Availability %
    fig.add_trace(go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['availability (%)'],
        mode='lines+markers+text',
        name='Availability (%)',
        yaxis='y2',
        line=dict(color='#2ca02c', width=4),
        text=filtered_df['availability (%)'].round(2).astype(str) + '%',
        textposition='top center',
        textfont=dict(size=16, color='#2ca02c'),
        hovertemplate='Availability: %{y:.2f}%<extra></extra>'
    ))

    fig.update_layout(
        title="📊 Daily Performance",
        xaxis=dict(
            title=dict(text="Date", font=dict(size=16, family="Arial", color="black")),
            tickfont=dict(size=14),
            tickformat="%d-%b-%Y"  # 👈 Format to show as 17-Jul-2025
        ),
        yaxis=dict(
            title=dict(text="Jumlah Kejadian / Outage Hours", font=dict(size=16, family="Arial", color="black")),
            tickfont=dict(size=14),
            side='left',
            showgrid=False
        ),
        yaxis2=dict(
            title=dict(text="Availability (%)", font=dict(size=16, family="Arial", color="black")),
            tickfont=dict(size=14),
            overlaying='y',
            side='right',
            showgrid=True,
            gridcolor='lightgrey'
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="Arial"
        ),
        legend=dict(
            orientation="h",
            font=dict(size=16)
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🧾 Filtered Data Details"):
        df_to_display = filtered_df.copy()
        df_to_display['Date'] = df_to_display['Date'].dt.strftime('%d-%B-%Y')
        st.dataframe(df_to_display, use_container_width=True)

    # --- Download filtered data ---
    csv_filtered = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered CSV",
        data=csv_filtered,
        file_name="filtered_availability_data.csv",
        mime="text/csv",
        key="download_filtered"
    )

    # --- Download raw (unfiltered) data ---
    csv_raw = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📄 Download Raw CSV",
        data=csv_raw,
        file_name="raw_availability_data.csv",
        mime="text/csv",
        key="download_raw"
    )

def app_tab2(df):
    import plotly.graph_objects as go
    st.subheader("📊 Availability Achievement Trend")

    # --- Prepare Date column ---
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df['Date'] = df['Date'].dt.date

    min_date = df['Date'].min()
    max_date = df['Date'].max()

    # --- Filter UI ---
    with st.expander("🔍 Filter Data"):
        col1, col2, col3, col4 = st.columns(4)

        date_range = col1.date_input(
            "Date Range",
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date,
            key="filter_date_range"
        )

        area_options = ['All'] + sorted(df['area'].dropna().unique())
        selected_area = col2.selectbox("Area", area_options, key="tab2_area")

        # --- Cascading Regional Options ---
        if selected_area == 'All':
            regional_filtered_df = df
        else:
            regional_filtered_df = df[df['area'] == selected_area]

        regional_options = ['All'] + sorted(regional_filtered_df['regional'].dropna().unique())
        selected_regional = col3.selectbox("Regional", regional_options, key="tab2_regional")

        # --- Cascading Site Options ---
        if selected_regional == 'All':
            site_filtered_df = regional_filtered_df
        else:
            site_filtered_df = regional_filtered_df[regional_filtered_df['regional'] == selected_regional]

        site_options = ['All'] + sorted(site_filtered_df['networksite'].dropna().unique())
        selected_site = col4.selectbox("Network Site", site_options, key="tab2_site")

    # --- Apply Filters ---
    filtered_df = df.copy()

    start_date, end_date = date_range
    filtered_df = filtered_df[(filtered_df['Date'] >= start_date) & (filtered_df['Date'] <= end_date)]

    if selected_area != 'All':
        filtered_df = filtered_df[filtered_df['area'] == selected_area]
    if selected_regional != 'All':
        filtered_df = filtered_df[filtered_df['regional'] == selected_regional]
    if selected_site != 'All':
        filtered_df = filtered_df[filtered_df['networksite'] == selected_site]

    # --- Group Data ---
    grouped = (
        filtered_df.groupby(['Date', 'Achievement'])
        .size()
        .reset_index(name='Count')
    )

    pivoted = grouped.pivot(index='Date', columns='Achievement', values='Count').fillna(0)
    if 'Achieved' not in pivoted.columns:
        pivoted['Achieved'] = 0
    if 'Not Achieved' not in pivoted.columns:
        pivoted['Not Achieved'] = 0
    pivoted = pivoted[['Achieved', 'Not Achieved']].sort_index()

    # --- Plot ---
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=pivoted.index,
        y=pivoted['Achieved'],
        name="Achieved",
        marker_color="#F6AB42",
        text=pivoted['Achieved'],
        textposition='inside',
        textfont=dict(size=16),
        insidetextanchor='start'
    ))

    fig.add_trace(go.Bar(
        x=pivoted.index,
        y=pivoted['Not Achieved'],
        name="Not Achieved",
        marker_color="beige",
        text=pivoted['Not Achieved'],
        textposition='inside',
        textfont=dict(size=16),
        insidetextanchor='end'
    ))

    fig.update_layout(
        barmode='stack',
        title='🎯 Daily Availability Achievement',
        xaxis=dict(
            title=dict(
                text='Date',
                font=dict(size=16)
            ),
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            title=dict(
                text='Number of Sites',
                font=dict(size=16)
            ),
            tickfont=dict(size=14)
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(size=16)
        ),
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

def app_tab3(df):
    st.subheader("📅 Weekly Availability Summary")

    # --- Extract and clean Week info ---
    df['Week'] = df['Week'].astype(str)

    # Extract numeric week number (e.g., from '2025-W14' -> 14)
    df['Week_Num'] = df['Week'].str.extract(r'W(\d+)')[0]
    df['Week_Num'] = pd.to_numeric(df['Week_Num'], errors='coerce')

    # Drop rows missing either
    df = df.dropna(subset=['Week', 'Week_Num'])

    # Get unique sorted week labels
    week_df = df[['Week', 'Week_Num']].drop_duplicates().sort_values('Week_Num')
    unique_weeks = week_df['Week'].tolist()

    # Error handling
    if not unique_weeks:
        st.warning("No valid week data available. Check the 'Week' column format.")
        return

    # Convert relevant columns to numeric
    df['occurrence'] = pd.to_numeric(df['occurrence'], errors='coerce')
    df['outage_2g (Hour)'] = pd.to_numeric(df['outage_2g (Hour)'], errors='coerce')
    df['outage_4g (Hour)'] = pd.to_numeric(df['outage_4g (Hour)'], errors='coerce')
    df['availability (%)'] = pd.to_numeric(df['availability (%)'], errors='coerce')
    df['Year'] = df['period'].astype(str).str[:4].astype(int)

    # Drop rows where Week or Week_Num is missing
    df = df.dropna(subset=['Week', 'Week_Num'])

    # --- Week Range Filter Logic ---
    # Get unique week labels, sorted by their numeric week number
    week_df = df[['Week', 'Week_Num']].drop_duplicates().sort_values('Week_Num', ascending=True)
    unique_weeks = week_df['Week'].tolist()

    # If no weeks are found, stop
    if not unique_weeks:
        st.warning("No valid week data available.")
        return

    # Set range indices for slider
    week_index_min, week_index_max = 0, len(unique_weeks) - 1
    week_min, week_max = unique_weeks[0], unique_weeks[-1]

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        week_range = st.slider(
            "Week Range",
            min_value=0,
            max_value=week_index_max,
            value=(week_index_min, week_index_max),
            step=1
        )
        selected_weeks = unique_weeks[week_range[0]:week_range[1]+1]

    with col2:
        year_min, year_max = df['Year'].min(), df['Year'].max()
        selected_year = st.slider("Year", min_value=year_min, max_value=year_max, value=year_max, step=1)

    with col3:
        area_options = sorted(df['area'].dropna().unique())
        selected_area = st.selectbox("Area", area_options, key="tab3_area")

    with col4:
        reg_df = df[df['area'] == selected_area]
        reg_options = sorted(reg_df['regional'].dropna().unique())
        selected_regional = st.selectbox("Regional", reg_options, key="tab3_regional")

    with col5:
        site_df = reg_df[reg_df['regional'] == selected_regional]
        site_options = sorted(site_df['site_id'].dropna().unique())
        selected_siteid = st.selectbox("Site ID", site_options, index=random.randint(0, len(site_options)-1), key="tab3_siteid")

    # --- Filter Data ---
    mask = (
        (df['Week'].isin(selected_weeks)) &
        (df['Year'] == selected_year) &
        (df['area'] == selected_area) &
        (df['regional'] == selected_regional) &
        (df['site_id'] == selected_siteid)
    )
    filtered_df = df[mask].sort_values('Week_Num')

    if filtered_df.empty:
        st.warning("No data found for the selected filters.")
        return

    # --- Chart ---
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=filtered_df['Week'],
        y=filtered_df['occurrence'],
        name='Occurrence',
        marker_color="#F7C989",
        text=filtered_df['occurrence'],
        textposition='auto',
        textfont=dict(size=16, color='black')
    ))

    fig.add_trace(go.Scatter(
        x=filtered_df['Week'],
        y=filtered_df['outage_2g (Hour)'],
        mode='lines+markers',
        name='Outage 2G (Hr)',
        line=dict(color='#1f77b4', width=4)
    ))

    fig.add_trace(go.Scatter(
        x=filtered_df['Week'],
        y=filtered_df['outage_4g (Hour)'],
        mode='lines+markers',
        name='Outage 4G (Hr)',
        line=dict(color='#d62728', width=4)
    ))

    fig.add_trace(go.Scatter(
        x=filtered_df['Week'],
        y=filtered_df['availability (%)'],
        mode='lines+markers+text',
        name='Availability (%)',
        yaxis='y2',
        line=dict(color='#2ca02c', width=4),
        text=filtered_df['availability (%)'].round(2).astype(str) + '%',
        textposition='top center',
        textfont=dict(size=16, color='#2ca02c')
    ))

    fig.update_layout(
        title="📊 Weekly Performance",
        xaxis=dict(
            title=dict(text="Week", font=dict(size=16)),
            tickfont=dict(size=14),
        ),
        yaxis=dict(
            title=dict(text="Occurrence / Outage Hours", font=dict(size=16)),
            tickfont=dict(size=14),
            side='left',
            showgrid=False
        ),
        yaxis2=dict(
            title=dict(text="Availability (%)", font=dict(size=16)),
            tickfont=dict(size=14),
            overlaying='y',
            side='right',
            showgrid=True,
            gridcolor='lightgrey'
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="white",
            font_size=16,
            font_family="Arial"
        ),
        legend=dict(orientation="h", font=dict(size=14)),
        margin=dict(l=40, r=40, t=60, b=40),
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Details ---
    with st.expander("🧾 Filtered Weekly Data"):
        st.dataframe(filtered_df, use_container_width=True)

    # --- Download Buttons ---
    st.download_button(
        label="📥 Download Filtered CSV",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="weekly_filtered_data.csv",
        mime="text/csv"
    )

    st.download_button(
        label="📄 Download Raw Weekly CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="weekly_raw_data.csv",
        mime="text/csv"
    )

def app():
    col1, col2 = st.columns([9, 1])
    with col1:
        st.title("🎟️ Availability Dashboard")
    with col2:
        if st.button("🔄 Refresh Data", help="Reload availability data"):
            st.cache_data.clear()
            st.rerun()

    # Load daily and weekly data
    df_daily = load_all_daily_files()
    df_weekly = load_all_weekly_files()  # <-- Add this line

    if df_daily.empty and df_weekly.empty:
        st.warning("No availability data found.")
        return

    # Define tabs
    tab1, tab2, tab3 = st.tabs([
        "📌 Daily Availability",
        "📈 Daily Achievement",
        "📅 Weekly Availability"         # <-- New Tab 3
    ])

    # Render each tab
    with tab1:
        app_tab1(df_daily)
    with tab2:
        app_tab2(df_daily)
    with tab3:
        if df_weekly.empty:
            st.warning("No weekly data available.")
        else:
            app_tab3(df_weekly)   # <-- You will define this
