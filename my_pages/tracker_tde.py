import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # ✅ For timezone-aware datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.drive_utils import get_drive, upload_file_to_drive, download_file_from_drive, read_excel_from_drive
import io
#from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# === Constants ===
SOW_LIST = [
    "FIRE SUPPRESSION SYSTEM",
    "COOLING SYSTEM PAC",
    "COOLING SYSTEM AC",
    "UPS",
    "ELECTRICAL DC",
    "ELECTRICAL AC Trafo & MV",
    "GENSET WU",
    "GENSET PM",
    "LIFT",
    "HYDRANT",
    "GROUND SYSTEM",
    "FUEL SYSTEM"
]

EXCEL_FILE_NAME = "activity_tracker_tde.xlsx"
EXCEL_FOLDER_ID = "1iTLqRrwbWhkIHvnXp15VTTZFl90lRyml"
EVIDENCE_FOLDER_ID = "11u1ewfwri9LyLcnhp41UnDy5jAu34IM-"

# === Tab 1: Data Submission ===
def app_tab1():
    st.header("📥 Input Activity TDE")
    jakarta_today = datetime.now(ZoneInfo("Asia/Jakarta")).date()

    if "tde_submitted" not in st.session_state:
        st.session_state["tde_submitted"] = False
        st.session_state["latest_entry"] = None

    if not st.session_state["tde_submitted"]:
        with st.form("form_tde"):
            selected_sow = st.selectbox("🔧 Scope of Work (SOW)", SOW_LIST, key="sow")
            selected_date = st.date_input("📅 Date", value=jakarta_today, key="date")
            quantity = st.number_input("🧮 Quantity", min_value=1, step=1, key="qty")
            uploaded_files = st.file_uploader(
                "📷 Upload Evidence (max 3 files, 2MB each)", 
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key="files"
            )

            submitted = st.form_submit_button("✅ Submit")

            if submitted:
                if not selected_sow or not quantity or not selected_date:
                    st.warning("Please fill in all required fields.")
                    return

                drive = get_drive()
                try:
                    excel_path = download_file_from_drive(drive, EXCEL_FILE_NAME, EXCEL_FOLDER_ID)
                    df = pd.read_excel(excel_path)
                except FileNotFoundError:
                    df = pd.DataFrame(columns=["SOW", "Date", "Quantity", "Evidence 1", "Evidence 2", "Evidence 3"])

                # Upload evidence
                evidence_urls = []
                for idx, file in enumerate(uploaded_files[:3]):
                    upload_filename = f"{selected_sow}_{selected_date.strftime('%Y%m%d')}_{idx+1}"
                    file_id = upload_file_to_drive(file, EVIDENCE_FOLDER_ID, upload_filename)
                    url = f"https://drive.google.com/file/d/{file_id}/view"
                    evidence_urls.append(url)

                while len(evidence_urls) < 3:
                    evidence_urls.append("")

                new_row = {
                    "SOW": selected_sow,
                    "Date": selected_date,
                    "Quantity": quantity,
                    "Evidence 1": evidence_urls[0],
                    "Evidence 2": evidence_urls[1],
                    "Evidence 3": evidence_urls[2]
                }

                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                df.to_excel(excel_path, index=False)
                upload_file_to_drive(excel_path, EXCEL_FOLDER_ID, EXCEL_FILE_NAME)

                st.session_state["tde_submitted"] = True
                st.session_state["latest_entry"] = new_row
                st.rerun()

    else:
        st.success("✅ Data saved and evidence uploaded successfully!")
        st.markdown("### ✅ Latest Submission Summary")
        st.dataframe(pd.DataFrame([st.session_state["latest_entry"]]))

        if st.button("➕ Add Another Submission"):
            st.session_state["tde_submitted"] = False
            st.session_state["latest_entry"] = None
            st.rerun()

# Step 1: Determine available cutoff periods (monthly/quarterly/etc.) based on selected SOW
def get_cutoff_ranges(df, sow, periods):
    date_cols = pd.to_datetime(df.columns[3:], format="%d-%b-%y")
    df_dates = pd.DataFrame({"date": date_cols})
    if periods == 12:
        df_dates["period"] = df_dates["date"].dt.to_period("M")
    elif periods == 4:
        df_dates["period"] = df_dates["date"].dt.to_period("Q")
    elif periods == 2:
        df_dates["quarter"] = df_dates["date"].dt.to_period("Q")
        df_dates["semester"] = df_dates["quarter"].astype(str).str.extract(r'(\d)')  # 1 or 2
        df_dates["period"] = df_dates["date"].dt.year.astype(str) + " S" + df_dates["semester"]
    elif periods == 48:
        df_dates["period"] = df_dates["date"].dt.to_period("W")
    else:
        df_dates["period"] = df_dates["date"].dt.to_period("M")  # default fallback
    
    # Get unique periods as strings
    return sorted(df_dates["period"].astype(str).unique())

# === Tab 2: Tracker View ===
def app_tab2():
    #st.markdown("### 📊 Tracker Activity TDE")
    col_title, col_button = st.columns([8, 1])

    with col_title:
        st.markdown("### 📊 Tracker Activity TDE")

    with col_button:
        if st.button("🔄 Refresh", help="Reload activity data"):
            st.cache_data.clear()
            st.rerun()

    sow_df = read_excel_from_drive(EXCEL_FOLDER_ID, "sow_tde.xlsx")
    activity_df = read_excel_from_drive(EXCEL_FOLDER_ID, EXCEL_FILE_NAME)

    tz = ZoneInfo("Asia/Jakarta")
    activity_df["Date"] = pd.to_datetime(activity_df["Date"], errors="coerce")

    if activity_df["Date"].dt.tz is None:
        activity_df["Date"] = activity_df["Date"].dt.tz_localize("Asia/Jakarta", ambiguous="NaT", nonexistent="NaT")

    activity_df["Date"] = activity_df["Date"].dt.normalize()

    start_date = datetime(2025, 7, 1, tzinfo=tz)
    today = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    date_range = pd.date_range(start=start_date, end=today, tz=tz)

    result = sow_df.copy()

    for date in date_range:
        date_str = date.strftime("%d-%b-%y")
        daily_df = activity_df[activity_df["Date"] == date]
        daily_summary = daily_df.groupby("SOW")["Quantity"].sum().reset_index()
        daily_summary.columns = ["SOW", date_str]
        result = result.merge(daily_summary, on="SOW", how="left")

    result.fillna(0, inplace=True)

    # Create two columns for filters
    col1, col2 = st.columns(2)

    with col1:
        sow_options = result["SOW"].unique().tolist()
        selected_sow = st.selectbox("Pilih SOW", sow_options)

    sow_row = result[result["SOW"] == selected_sow].copy()
    if sow_row.empty:
        st.warning("Data SOW tidak ditemukan.")
        st.stop()

    sow_row = sow_row.reset_index(drop=True)
    unit = sow_row.at[0, "Unit"]
    periods = sow_row.at[0, "Periods"]

    # Extract date columns
    date_cols = [col for col in sow_row.columns if isinstance(col, str) and "-" in col]
    date_range = pd.to_datetime(date_cols, format="%d-%b-%y")
    quantity_values = sow_row[date_cols].values.flatten().astype(int)
    df_chart = pd.DataFrame({
        "Date": date_range,
        "Quantity": quantity_values
    })

    # Determine period-based group
    df_chart = df_chart.sort_values("Date").reset_index(drop=True)

    # Generate period ranges
    if periods == 48:  # Weekly
        df_chart["Period"] = df_chart["Date"].dt.to_period("W").dt.start_time
    elif periods == 12:  # Monthly
        df_chart["Period"] = df_chart["Date"].dt.to_period("M").dt.start_time
    elif periods == 4:  # Quarterly
        df_chart["Period"] = df_chart["Date"].dt.to_period("Q").dt.start_time
    elif periods == 2:  # Semiannual
        df_chart["Period"] = df_chart["Date"].apply(lambda d: datetime(d.year, 1 if d.month <= 6 else 7, 1, tzinfo=tz))
    else:
        df_chart["Period"] = df_chart["Date"].min()

    # Format period options
    period_options = df_chart["Period"].sort_values(ascending=False).unique()

    if periods == 48:  # Weekly → W27-2025
        formatted_options = [f"W{d.isocalendar().week:02d} - {d.year}" for d in period_options]
    elif periods == 12:  # Monthly → August-2025
        formatted_options = [d.strftime("%B - %Y") for d in period_options]
    elif periods == 4:  # Quarterly → Q3-2025
        formatted_options = [f"Q{((d.month - 1) // 3) + 1} - {d.year}" for d in period_options]
    elif periods == 2:  # Semiannual → Semester 2 - 2025
        formatted_options = [f"Semester {2 if d.month >= 7 else 1} - {d.year}" for d in period_options]
    else:
        formatted_options = [d.strftime("%d-%B-%Y") for d in period_options]

    with col2:
        selected_formatted = st.selectbox("📅 Pilih Periode", formatted_options, key="periode_selectbox_tab2")

    # Map selected label back to datetime
    formatted_to_actual = dict(zip(formatted_options, period_options))
    selected_period = formatted_to_actual[selected_formatted]

    # Filter to selected period
    df_chart = df_chart[df_chart["Period"] == selected_period].copy()

    # Calculate progress
    df_chart["Cumulative"] = df_chart["Quantity"].cumsum()
    df_chart["%Ach"] = (df_chart["Cumulative"] / unit * 100).round(2)

    # Format the date to '01-July-2025' format
    df_chart["Date"] = df_chart["Date"].dt.strftime("%d-%B-%Y")

    # Show summary table
    st.markdown("### 📋 Tabel Ringkasan Harian")
    with st.expander("📋 Tabel Tracker Activity"):
        st.dataframe(df_chart[["Date", "Quantity", "Cumulative", "%Ach"]].style.format({
            "Quantity": "{:,.0f}",
            "Cumulative": "{:,.0f}",
            "%Ach": "{:.2f}%"
        }), use_container_width=True)

        # Strip timezone from datetime columns
        for df in [df_chart, result]:
            for col in df.select_dtypes(include=["datetimetz"]).columns:
                df[col] = df[col].dt.tz_localize(None)

        # Create Excel download from df_chart
        output_chart = io.BytesIO()
        with pd.ExcelWriter(output_chart, engine="xlsxwriter") as writer:
            df_chart.to_excel(writer, index=False, sheet_name="Tracker")
        excel_chart = output_chart.getvalue()

        # Download button for df_chart
        st.download_button(
            label="📥 Download Excel - Ringkasan Harian",
            data=excel_chart,
            file_name="tabel_ringkasan_harian.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Plotly chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_chart["Date"],
        y=df_chart["Quantity"],
        name="Quantity Harian",
        marker_color="skyblue",
        yaxis="y1",
        text=[f"{v:,}" for v in df_chart["Quantity"]],  # Show formatted value
        textposition="inside",  # or "auto", "inside", "none"
        insidetextanchor="start",
        textfont=dict(size=14, color="black"),
        hovertemplate=(
            "<b>Quantity Harian :</b> %{y:,}<extra></extra>"
        )
    ))

    fig.add_trace(go.Scatter(
        x=df_chart["Date"],
        y=df_chart["Cumulative"],
        name="Kumulatif",
        mode="lines+markers+text",
        line=dict(color="green", width=4, shape="spline"),
        yaxis="y1",
        text=[f"{v:.0f}" for v in df_chart["Cumulative"]],  # Format as integer
        textposition="top center",  # Or 'bottom center', etc.
        textfont=dict(size=14, color="green"),  # Optional styling
        hovertemplate=(
            "<b>Kumulatif :</b> %{y:,}<extra></extra>"
        )
    ))

    fig.add_trace(go.Scatter(
        x=df_chart["Date"],
        y=df_chart["%Ach"],
        name="% Completion",
        mode="lines+markers+text",
        line=dict(color="orange", width=4, shape="spline"),
        yaxis="y2",
        text=[f"{v:.1f}%" for v in df_chart["%Ach"]],  # Format as percentage
        textposition="bottom center",  # Position of the label
        textfont=dict(size=14, color="black"),  # Customize label font
        hovertemplate=(
            "<b>% Completion :</b> %{y:,}%<extra></extra>"
        )
    ))

    fig.update_layout(
        title=dict(
            text=(
                f"<span style='font-size:24px; font-weight:bold; color:black'>Tracker Activity Harian</span><br>"
                f"<span style='font-size:22px; font-weight:bold; color:green'>{selected_sow} - {selected_formatted}</span><br>"
                f"<span style='font-size:20px; font-weight:bold; color:gray'>Total Unit: {unit}</span>"
            ),
            x=0.5,
            xanchor="center"
        ),
        xaxis=dict(
            title="Tanggal",
            tickmode="linear",
            dtick="D1",  # show every day
            tickformat="%d-%b-%Y",  # format like 01-Jul-2025
            tickangle=-45,
            tickfont=dict(size=14)
        ),
        #yaxis=dict(title="Qty / Kumulatif", side="left"),
        yaxis=dict(
            title="Qty / Kumulatif",
            title_font=dict(size=16),
            side="left",
            rangemode="tozero",
            zeroline=True,
            zerolinecolor='gray',
            zerolinewidth=1,
            fixedrange=False,
            tickfont=dict(size=14)
        ),
        #yaxis2=dict(title="% Pencapaian", overlaying="y", side="right", range=[0, 100]),
        yaxis2=dict(
        title="% Completion",
            title_font=dict(size=16),
            overlaying="y",
            side="right",
            range=[0, 110],  # Explicitly set percentage range
            zeroline=True,
            zerolinecolor='gray',
            zerolinewidth=1,
            fixedrange=False,
            tickfont=dict(size=14)
        ),
        legend=dict(orientation="h", yanchor="bottom", y=-0.45, xanchor="right", x=1, font=dict(size=14)),
        margin=dict(t=100, b=80),
        height=600,
        hovermode="x unified",
        hoverlabel=dict(
            font_size=14,
            font_family="Arial",
            font_color="black",
            bgcolor="azure",  # tooltip background
            bordercolor="gray"
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    result.index = result.index + 1
    with st.expander("📋 Raw Data"):
        st.dataframe(result, use_container_width=True, height=460)

        # Strip timezone if any datetime columns have tz
        for col in result.select_dtypes(include=["datetimetz"]).columns:
            result[col] = result[col].dt.tz_localize(None)

        # Create Excel download from result
        output_result = io.BytesIO()
        with pd.ExcelWriter(output_result, engine="xlsxwriter") as writer:
            result.to_excel(writer, index=False, sheet_name="Raw Data")

        excel_result = output_result.getvalue()

        # Download button for result
        st.download_button(
            label="📥 Download Excel - Raw Data",
            data=excel_result,
            file_name="tabel_raw_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def app_tab3():
    #st.markdown("### Riwayat Activity TDE")
    col_title, col_button = st.columns([8, 1])

    with col_title:
        st.markdown("### 📊 Tracker Activity TDE")

    with col_button:
        if st.button("🔄 Refresh Data", help="Reload activity data", key="refresh_button_tab3"):
            st.cache_data.clear()
            st.rerun()

    EXCEL_FOLDER_ID = "1iTLqRrwbWhkIHvnXp15VTTZFl90lRyml"
    EXCEL_FILE_NAME = "activity_tracker_tde.xlsx"

    sow_df = read_excel_from_drive(EXCEL_FOLDER_ID, "sow_tde.xlsx")
    activity_df = read_excel_from_drive(EXCEL_FOLDER_ID, EXCEL_FILE_NAME)

    tz = ZoneInfo("Asia/Jakarta")
    activity_df["Date"] = pd.to_datetime(activity_df["Date"], errors="coerce")
    if activity_df["Date"].dt.tz is None:
        activity_df["Date"] = activity_df["Date"].dt.tz_localize(tz, ambiguous="NaT", nonexistent="NaT")
    activity_df["Date"] = activity_df["Date"].dt.normalize()

    # === Filter setup ===
    col1, col2 = st.columns(2)

    with col1:
        sow_options = ["All"] + sow_df["SOW"].unique().tolist()
        selected_sow = st.selectbox("📌 Pilih SOW", sow_options)

    # Handle All option
    if selected_sow == "All":
        activity_sow = activity_df.copy()
        unique_periods = activity_sow["SOW"].map(sow_df.set_index("SOW")["Periods"])
    else:
        sow_row = sow_df[sow_df["SOW"] == selected_sow].copy()
        if sow_row.empty:
            st.warning("Data SOW tidak ditemukan.")
            st.stop()

        periods = sow_row.iloc[0]["Periods"]
        unit = sow_row.iloc[0]["Unit"]

        activity_sow = activity_df[activity_df["SOW"] == selected_sow].copy()

    if activity_sow.empty:
        st.warning("Belum ada aktivitas untuk SOW ini.")
        st.stop()

    activity_sow = activity_sow.sort_values("Date")
    activity_sow["Date"] = activity_sow["Date"].dt.normalize()

    # Determine periods dynamically if "All" is selected
    if selected_sow == "All":
        periods = unique_periods.mode().iloc[0] if not unique_periods.empty else 12

    # Create Period column & display options based on period type
    if periods == 48:  # Weekly
        activity_sow["Period"] = activity_sow["Date"].dt.to_period("W").dt.start_time
        formatted_options = [f"W{d.isocalendar().week:02d} - {d.year}" for d in activity_sow["Period"].unique()]
    elif periods == 12:  # Monthly
        activity_sow["Period"] = activity_sow["Date"].dt.to_period("M").dt.start_time
        formatted_options = [d.strftime("%B - %Y") for d in activity_sow["Period"].unique()]
    elif periods == 4:  # Quarterly
        activity_sow["Period"] = activity_sow["Date"].dt.to_period("Q").dt.start_time
        formatted_options = [f"Q{((d.month - 1) // 3) + 1} - {d.year}" for d in activity_sow["Period"].unique()]
    elif periods == 2:  # Semiannual
        activity_sow["Period"] = activity_sow["Date"].apply(lambda d: datetime(d.year, 1 if d.month <= 6 else 7, 1, tzinfo=tz))
        formatted_options = [f"Semester {2 if d.month >= 7 else 1} - {d.year}" for d in activity_sow["Period"].unique()]
    else:
        activity_sow["Period"] = activity_sow["Date"].min()
        formatted_options = [activity_sow["Period"].iloc[0].strftime("%d-%B-%Y")]

    # Add "All" to period options if SOW is All
    if selected_sow == "All":
        formatted_options = ["All"] + formatted_options
        formatted_to_actual = {opt: val for opt, val in zip(formatted_options[1:], activity_sow["Period"].unique())}
    else:
        formatted_to_actual = dict(zip(formatted_options, activity_sow["Period"].unique()))

    with col2:
        selected_formatted = st.selectbox("📅 Pilih Periode", formatted_options, key="periode_selectbox_tab3")

    # Filter logic
    if selected_formatted == "All":
        filtered_df = activity_sow.copy()
    else:
        selected_period = formatted_to_actual[selected_formatted]
        filtered_df = activity_sow[activity_sow["Period"] == selected_period].copy()

    if filtered_df.empty:
        st.info("Tidak ada aktivitas pada periode ini.")
        return

    # Show summary table
    st.markdown("### 📋 Tabel Riwayat Acitivty TDE")  

    # 1. Convert Date to datetime format
    filtered_df["Date"] = pd.to_datetime(filtered_df["Date"], errors="coerce")

    # 2. Sort by datetime, descending (newest first)
    filtered_df = filtered_df.sort_values("Date", ascending=False)

    # 3. Reformat date for display AFTER sorting
    filtered_df["Date_display"] = filtered_df["Date"].dt.strftime("%d-%B-%Y")

    # 4. Build Evidence columns with 'Lihat' links
    for col in ["Evidence 1", "Evidence 2", "Evidence 3"]:
        if col in filtered_df.columns:
            filtered_df[col] = filtered_df[col].fillna("").apply(
                lambda x: f'<a href="{x}" target="_blank">Lihat</a>' if x.strip() != "" else ""
            )

    # 5. Select columns to show — use 'Date_display' instead of raw datetime
    display_columns = ["Date_display", "SOW", "Quantity", "Evidence 1", "Evidence 2", "Evidence 3"]
    filtered_df = filtered_df[[col for col in display_columns if col in filtered_df.columns]]

    # Optional: Rename 'Date_display' column to just 'Date' for prettier header
    filtered_df = filtered_df.rename(columns={"Date_display": "Date"})
    existing_columns = filtered_df.columns.tolist()

    # 6. Build HTML table manually
    table_html = """
    <style>
    .custom-table {
        border-collapse: collapse;
        width: 100%;
        font-size: 18px;
    }
    .custom-table th, .custom-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: center;
        vertical-align: middle;
    }
    .custom-table th {
        background-color: #4a90e2; /* header background color */
        color: white; /* header text color */
    }
    .custom-table tr:nth-child(even) {
        background-color: #f9f9f9; /* banded rows */
    }
    .custom-table a {
        color: #1a0dab;
        text-decoration: none;
        font-weight: bold;
    }
    </style>
    <table class="custom-table">
    <thead>
    <tr>
    """

    # Add headers
    for col in existing_columns:
        table_html += f"<th>{col}</th>"
    table_html += "</tr></thead><tbody>"

    # Add rows (DON'T sort again!)
    for _, row in filtered_df.iterrows():
        table_html += "<tr>"
        for cell in row:
            table_html += f"<td>{cell}</td>"
        table_html += "</tr>"

    table_html += "</tbody></table>"

    # Display in Streamlit
    st.markdown(table_html, unsafe_allow_html=True)

    # === Add download button ===
    if not filtered_df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Filtered Data")
        buffer.seek(0)

        st.download_button(
            label="📥 Download Activity History Data",
            data=buffer,
            file_name="riwayat_activity_tde.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def app_tab4():
    #st.header("📈 Kurva S Project TDE - Progress Chart")
    tab4_title, tab4_button = st.columns([9, 1])
    with tab4_title:
        st.markdown("### 📈 Kurva S Project TDE - Progress Chart")

    with tab4_button:
        if st.button("🔄 Refresh Data", help="Reload data Kurva S", key="refresh_button_tab4"):
            st.cache_data.clear()
            st.rerun()

    folder_id = EXCEL_FOLDER_ID  # 🔁 Replace with actual folder ID
    df = load_kurva_s(folder_id)

    # Ensure daily frequency, fill missing rows if any
    df = df.set_index("Date").asfreq("D").fillna(0).reset_index()

    # Recalculate cumulative values after fill
    df["Cumulative Plan"] = df["Plan"].cumsum()
    total_plan = df["Cumulative Plan"].iloc[-1]
    df["Cumulative Percentage"] = (df["Cumulative Plan"] / total_plan) * 100

    # Today's date for vertical line
    today = pd.to_datetime(date.today())

    # Create the plot
    fig = go.Figure()

    # Line chart for Cumulative Percentage
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Cumulative Percentage"],
        mode="lines+markers",
        name="Cumulative %",
        text=df["Cumulative Percentage"].apply(lambda x: f"{x:.2f}%"),
        textposition="top center",
        marker=dict(size=8),
        line=dict(shape="spline", width=5),
        hovertemplate=(
            "<b>Plan:</b> %{customdata[0]:,.0f}<br>"
            "<b>Cumulative Plan:</b> %{customdata[1]:,.0f}<br>"
            "<b>Cumulative Plan %:</b> %{y:.2f}%<extra></extra>"
        ),
        customdata=df[["Plan", "Cumulative Plan"]]
    ))

    today = pd.to_datetime("today").normalize()
    df_actual_until_today = df[df["Date"] <= today]

    fig.add_trace(go.Scatter(
        x=df_actual_until_today["Date"],
        y=df_actual_until_today["Percentage Actual"],
        mode="lines+markers",
        name="Actual %",
        text=df_actual_until_today["Percentage Actual"].apply(lambda x: f"{x:.2f}%"),
        textposition="top center",
        marker=dict(size=8),
        line=dict(shape="spline", width=5, color="orange"),
        hovertemplate=(
            "<b>Actual Quantity:</b> %{customdata[0]:,.0f}<br>"
            "<b>Cumulative Actual:</b> %{customdata[1]:,.0f}<br>"
            "<b>Actual %:</b> %{y:.2f}%<extra></extra>"
        ),
        customdata=df_actual_until_today[["Quantity", "Cumulative Actual"]]
    ))
    
    # Vertical line for today's date
    fig.add_shape(
        type="line",
        x0=today, x1=today,
        y0=0, y1=100,
        line=dict(color="red", dash="dot"),
        name="Today"
    )

    fig.add_annotation(
        x=today,
        y=100,
        text="Today",
        showarrow=False,
        font=dict(color="red", size=12),
        yshift=10
    )

    # Get first date from df (assuming sorted)
    first_date = df["Date"].min()
    quarter = f"Q{((first_date.month - 1) // 3) + 1}"
    year = first_date.year

    # Layout styling
    fig.update_layout(
        title=dict(
            text=f"<b style='color:#1f77b4; font-size:30px;'>Cumulative Progress (Kurva S)</b><br><span style='font-size:24px;'>({quarter} {year})</span>",
            x=0.5,
            xanchor="center"
        ),
        xaxis=dict(
            title=dict(text="Date", font=dict(size=18)),
            tickformat="%d-%b-%Y",
            tickangle=-45,
            tickfont=dict(size=14),
            showgrid=False,
            tickmode="array",
            tickvals=df["Date"]
        ),
        yaxis=dict(
            title=dict(text="Cumulative Percentage (Plan/Actual) (%)", font=dict(size=18)), 
            range=[0, 110],
            tickfont=dict(size=14),
            showgrid=False
        ),
        height=600,
        margin=dict(l=40, r=40, t=80, b=100),
        
        # 🔽 Hover settings
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor="gray",
            font_size=16,
            font_family="Segoe UI"
        ),
        legend=dict(
            font=dict(size=16),
            orientation="h",
            yanchor="bottom",
            y=-0.4,
            xanchor="right",
            x=1
        )
    )

    # Show the chart
    st.plotly_chart(fig, use_container_width=True)

    # Add a horizontal separator or title (optional)
    st.markdown("### 📋 Data Table")

    # Format date and select columns
    df_export = df.assign(Date=df["Date"].dt.strftime("%d-%b-%Y"))[
        ["Date", "Plan", "Cumulative Plan", "Cumulative Percentage", "Quantity", "Cumulative Actual", "Percentage Actual"]
    ]

    # Expander for table
    with st.expander("📋 Show Data Table"):
        # Show the table
        st.dataframe(df_export)
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Kurva S")
    output.seek(0)

    # Download button
    st.download_button(
        label="📥 Download as Excel",
        data=output,
        file_name="kurva_s_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# === Main App ===
def app():
    st.title("⚙️ Tracker Activity TDE")

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Activity Form", "📊 Activity Completion Tracker", "🧭 Riwayat Aktivitas TDE", "📈 Kurva-S TDE"])
    with tab1:
        app_tab1()
    with tab2:
        app_tab2()
    with tab3:
        app_tab3()
    with tab4:
        app_tab4()




