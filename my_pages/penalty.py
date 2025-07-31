import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import get_drive, load_penalty_data

def app_tab1():
    st.subheader("📌 Penalty Tracker - Tab 1")

    # --- Load and flatten data ---
    raw_df = load_penalty_data()
    if raw_df.empty:
        st.warning("No penalty data available.")
        return

    # --- Step 1: Flatten headers if multi-level ---
    if isinstance(raw_df.columns, pd.MultiIndex):
        raw_df.columns = [' - '.join([str(i) for i in col if str(i) != 'nan']).strip() for col in raw_df.columns]
    else:
        raw_df.columns = raw_df.columns.astype(str)

    df = raw_df.copy()

    # --- Diagnostics ---
    #st.write("✅ Unique Areas:", df['Area'].dropna().unique())
    #st.write("✅ Columns:", df.columns.tolist())
    #st.write("✅ Shape:", df.shape)
    #st.write("✅ Preview:", df.head())

    # --- Step 2: Identify ID and Metric Columns ---
    id_cols = [col for col in df.columns if any(key in col.lower() for key in ["area", "regional", "site", "class", "target", "status"])]

    metric_keywords = ["Pencapaian", "Achievement", "Penalty"]
    value_cols = [col for col in df.columns if any(col.endswith(metric) for metric in metric_keywords)]

    if not value_cols:
        st.warning("No metric columns found.")
        return

    # --- Step 3: Convert to long format ---
    long_data = []
    for col in value_cols:
        for metric in metric_keywords:
            if col.endswith(metric):
                month = col.split(" - ")[0].strip()
                temp = df[id_cols + [col]].copy()
                temp = temp.rename(columns={col: metric})
                temp["Month"] = month
                temp["Metric"] = metric
                long_data.append(temp)

    if not long_data:
        st.warning("No valid data found after melting.")
        return

    # --- Step 4: Pivot and Merge ---
    from functools import reduce
    dfs = {}
    for metric in metric_keywords:
        temp = [d for d in long_data if d["Metric"].iloc[0] == metric]
        if temp:
            merged = pd.concat(temp, ignore_index=True).drop(columns=["Metric"])
            dfs[metric] = merged

    if not dfs:
        st.warning("No data available for metrics.")
        return

    merged_df = reduce(lambda left, right: pd.merge(left, right, on=id_cols + ["Month"], how="outer"), dfs.values())

    # --- Step 5: Clean and Convert ---
    merged_df["Pencapaian"] = pd.to_numeric(merged_df["Pencapaian"], errors="coerce") * 100
    merged_df["Penalty"] = pd.to_numeric(merged_df["Penalty"], errors="coerce") * 100
    merged_df = merged_df.dropna(subset=["Month"])
    merged_df["Month"] = pd.to_datetime(merged_df["Month"], errors="coerce")
    merged_df = merged_df.dropna(subset=["Month"])
    merged_df = merged_df.sort_values("Month")
    #st.write("✅ Preview:", merged_df.head())
    # --- Step 6: Filters ---
    col1, col2, col3 = st.columns(3)
    area_list = merged_df["Area"].dropna().unique().tolist()
    selected_area = col1.selectbox("Area", ["All"] + area_list)

    if selected_area != "All":
        merged_df = merged_df[merged_df["Area"] == selected_area]

    regional_list = merged_df["Regional"].dropna().unique().tolist()
    selected_regional = col2.selectbox("Regional", ["All"] + regional_list)

    if selected_regional != "All":
        merged_df = merged_df[merged_df["Regional"] == selected_regional]

    site_list = merged_df["Site"].dropna().unique().tolist()
    selected_site = col3.selectbox("Site", ["All"] + site_list)

    if selected_site != "All":
        merged_df = merged_df[merged_df["Site"] == selected_site]

    if merged_df.empty:
        st.warning("No data available after filtering.")
        return

    # --- Step 7: Summary ---
    summary = merged_df.groupby("Month").agg({
        "Pencapaian": "mean",
        "Penalty": "mean",
        "Achievement": lambda x: (x == "Ach").sum(),
    }).reset_index()
    summary["NotAch"] = merged_df.groupby("Month")["Achievement"].apply(lambda x: (x == "NotAch").sum()).values

    # --- Step 8: Plot ---
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=summary["Month"],
        y=summary["Achievement"],
        name="Ach",
        marker_color="lightblue",
        yaxis="y1",
        text=summary["Achievement"],
        textposition="inside",
        insidetextanchor="start",
        textfont=dict(size=16),
        hovertemplate="Ava Achieved :</b> %{y} sites<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=summary["Month"],
        y=summary["NotAch"],
        name="NotAch",
        marker_color="beige",
        yaxis="y1",
        text=summary["NotAch"],
        textposition="inside",
        insidetextanchor="start",
        textfont=dict(size=16),
        hovertemplate="Ava Not Achieved :</b> %{y} sites<extra></extra>"
    ))

    fig.add_trace(go.Scatter(
        x=summary["Month"],
        y=summary["Pencapaian"] / 100,
        name="Pencapaian (%)",
        mode="lines+markers+text",
        text=(summary["Pencapaian"] / 100).map(lambda x: f"{x:.2%}"),  # format as percentage
        textposition="top center",
        textfont=dict(size=14, color="green"),
        yaxis="y2",
        line=dict(color="blue", width=4),
        hovertemplate='%{y:.1%}<extra>Pencapaian</extra>'
    ))
    fig.add_trace(go.Scatter(
        x=summary["Month"],
        y=summary["Penalty"] / 100,
        name="Penalty (%)",
        mode="lines+markers+text",
        text=(summary["Penalty"] / 100).map(lambda x: f"{x:.0%}"),
        textposition="bottom center",
        textfont=dict(size=14, color="green"),
        yaxis="y2",
        line=dict(color="orange", width=4),
        hovertemplate='%{y:.1%}<extra>Penalty</extra>'
    ))

    title = "📊 Monthly Pencapaian vs Penalty vs Achievement"
    id_cols = [col for col in df.columns if any(key in col.lower() for key in ["area", "regional", "site", "class", "target", "status"])]
    if selected_site != "All":
        site_info = merged_df[merged_df["Site"] == selected_site].iloc[0]
        regional = site_info.get("Regional", "")
        site_class = site_info.get("Site class", "")
        title += f" — Site: {selected_site}, Regional: {regional}, Class: {site_class}"
        
    fig.update_layout(
        title=title,
        xaxis=dict(
            title=dict(text="Month", font=dict(size=16)),  # axis title font
            tickfont=dict(size=20)                         # tick labels
        ),
        yaxis=dict(
            title=dict(text="Achievement Count", font=dict(size=16)),
            tickfont=dict(size=18),
            side="left"
        ),
        yaxis2=dict(
            title=dict(text="Availability / Penalty (%)", font=dict(size=16)),
            tickfont=dict(size=18),
            overlaying="y",
            side="right",
            tickformat=".0%"
        ),
        barmode="stack",
        legend=dict(orientation="h"),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="lightcyan",
            font_size=16,
            font_family="Arial"
        ),
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Step 9: Show Filtered Table Below Chart ---
    with st.expander("📋 Show Filtered Data Table"):
        display_df = merged_df.copy()
        display_df["Pencapaian"] = (display_df["Pencapaian"]).round(2)
        display_df["Penalty"] = (display_df["Penalty"]).round(2)

        # Optional: Format Month for readability
        display_df["Month"] = display_df["Month"].dt.strftime("%b-%Y")

        # Reorder columns if needed
        cols_to_show = ["Month", "Area", "Regional", "Site", "Site Class", "Pencapaian", "Penalty", "Achievement"]
        display_df = display_df[[col for col in cols_to_show if col in display_df.columns]]

        st.dataframe(display_df, use_container_width=True)



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

    tab1, tab2 = st.tabs(["📌 Penalty Tracker", "📊 Tab 2 (Coming Soon)"])
    with tab1:
        app_tab1()
