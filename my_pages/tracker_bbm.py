import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import io
import re
import streamlit.components.v1 as components
from utils.data_loader import get_drive_oauth, upload_file_to_drive, download_file_from_drive, load_bbm_tracker_data
from utils.data_loader import get_drive as get_drive_auto

# Constants
DATA_FOLDER_ID = "1qAn7O6QEahUtVhAxRfLzDZZ36s5v2_fk"
UPLOAD_FOLDER_ID = "1BMBHGRHjzIPeekIXE3KQl55J0fKxohU2"
ALL_SITE_FILE = "all_site_cdc.csv"
BBM_FILE = "pengisian_bbm.xlsx"

@st.cache_resource
def get_drive():
    return get_drive_auto()

def app_tab1():
    st.subheader("⛽ Input Data Pengisian BBM")

    drive = get_drive()
    try:
        site_csv_path = download_file_from_drive(drive, ALL_SITE_FILE, DATA_FOLDER_ID)
        df_sites = pd.read_csv(site_csv_path)
        site_ids = df_sites['site_id'].dropna().unique()
    except Exception as e:
        st.error(f"Gagal memuat data site: {e}")
        return

    with st.form("form_pengisian_bbm"):
        site_id = st.selectbox("Pilih Site ID", sorted(site_ids))

        gmt7 = pytz.timezone("Asia/Jakarta")
        tanggal = st.date_input("Tanggal Pengisian", datetime.now(gmt7).date())

        jumlah = st.number_input("Jumlah Pengisian (Liter)", min_value=0.0, step=0.1)

        photos = st.file_uploader("Upload Foto Evidence (max 3, max 2MB each)",
                                  type=["jpg", "jpeg", "png"],
                                  accept_multiple_files=True)

        submit = st.form_submit_button("Submit")

    if submit:
        photos = photos or []

        if len(photos) > 3:
            st.error("❌ Maksimal 3 foto saja.")
            return
        for photo in photos:
            if photo.size > 2 * 1024 * 1024:
                st.error(f"❌ {photo.name} melebihi 2MB.")
                return

        site_name = df_sites.loc[df_sites['site_id'] == site_id, 'site_name'].values[0] \
            if 'site_name' in df_sites.columns else site_id

        gmt7 = pytz.timezone("Asia/Jakarta")
        timestamp = datetime.now(gmt7).strftime("%Y%m%d_%H%M%S")

        uploaded_urls = ["", "", ""]
        for idx, photo in enumerate(photos):
            ext = os.path.splitext(photo.name)[-1]
            clean_name = site_name.replace(" ", "_").replace("/", "_")
            filename = f"{clean_name}_{timestamp}_{idx+1}{ext}"

            # NEW - using BytesIO in-memory
            photo_bytes = io.BytesIO(photo.read())
            photo_bytes.seek(0)

            uploaded_id = upload_file_to_drive(photo_bytes, folder_id=UPLOAD_FOLDER_ID, filename=filename)
            uploaded_urls[idx] = f"https://drive.google.com/uc?id={uploaded_id}"

        # --- Load existing BBM file or create new ---
        try:
            excel_path = download_file_from_drive(drive, BBM_FILE, DATA_FOLDER_ID)
            df_bbm = pd.read_excel(excel_path)
        except Exception as e:
            st.warning(f"Gagal membaca file BBM, membuat baru: {e}")
            df_bbm = pd.DataFrame(columns=[
                "site_id", "tanggal_pengisian", "jumlah_pengisian_liter",
                "evidence1", "evidence2", "evidence3"
            ])

        new_row = {
            "site_id": site_id,
            "tanggal_pengisian": tanggal,
            "jumlah_pengisian_liter": jumlah,
            "evidence1": uploaded_urls[0],
            "evidence2": uploaded_urls[1],
            "evidence3": uploaded_urls[2]
        }

        df_bbm = pd.concat([df_bbm, pd.DataFrame([new_row])], ignore_index=True)

        # --- Save Excel to memory (not file) ---
        buffer = io.BytesIO()
        df_bbm.to_excel(buffer, index=False)
        buffer.seek(0)

        try:
            upload_file_to_drive(
                buffer,
                folder_id=DATA_FOLDER_ID,
                filename=BBM_FILE
            )
        except Exception as e:
            st.error(f"Gagal menyimpan file BBM: {e}")
            return

        st.success("✅ Data pengisian berhasil disimpan!")

# --- Cached Data Loading ---
@st.cache_data(ttl=3600)
def load_processed_data():
    #from data_loader import load_bbm_tracker_data, get_drive  # Adjust imports if needed
    df = load_bbm_tracker_data(
        drive=get_drive(),
        site_file="all_site_cdc.csv",
        bbm_file="pengisian_bbm.xlsx",
        folder_id="1qAn7O6QEahUtVhAxRfLzDZZ36s5v2_fk"
    )

    df['tanggal_pengisian'] = pd.to_datetime(df['tanggal_pengisian'], errors='coerce')
    df = df.sort_values('tanggal_pengisian', ascending=False)
    df = df.drop_duplicates(subset='site_id', keep='first')

    df['tanggal_pengisian'] = df['tanggal_pengisian'].dt.strftime("%d-%B-%Y")
    df['tanggal_habis'] = df['tanggal_habis'].dt.strftime("%d-%B-%Y")
    df['persentase_terpakai'] = df['persentase_terpakai'].map("{:.2f}".format)

    # Add row number
    df.reset_index(drop=True, inplace=True)
    df["No."] = df.index + 1

    return df

def app_tab2():
    st.subheader("📄 Tracker Pengisian BBM")

    try:
        df_tracker = load_processed_data()

        # --- Prepare filter options ---
        area_list = ["All"] + sorted(df_tracker['area'].dropna().unique())
        regional_list_all = sorted(df_tracker["regional"].dropna().unique())
        site_list_all = sorted(df_tracker["site_id"].dropna().unique())

        # --- Unified Filter Row ---
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_area = st.selectbox("Area", area_list, key="area_filter")
        with col2:
            if selected_area != "All":
                regional_list = ["All"] + sorted(df_tracker[df_tracker["area"] == selected_area]["regional"].dropna().unique())
            else:
                regional_list = ["All"] + regional_list_all
            selected_regional = st.selectbox("Regional", regional_list, key="regional_filter")
        with col3:
            if selected_regional != "All":
                site_list = ["All"] + sorted(df_tracker[df_tracker["regional"] == selected_regional]["site_id"].dropna().unique())
            elif selected_area != "All":
                site_list = ["All"] + sorted(df_tracker[df_tracker["area"] == selected_area]["site_id"].dropna().unique())
            else:
                site_list = ["All"] + site_list_all
            selected_site = st.selectbox("Site ID", site_list, key="site_filter")

        # --- Apply filters ---
        df_filtered = df_tracker.copy()
        if selected_area != "All":
            df_filtered = df_filtered[df_filtered["area"] == selected_area]
        if selected_regional != "All":
            df_filtered = df_filtered[df_filtered["regional"] == selected_regional]
        if selected_site != "All":
            df_filtered = df_filtered[df_filtered["site_id"] == selected_site]

        # --- Format evidence links ---
        def to_view_link(x):
            if isinstance(x, str) and "drive.google.com" in x:
                match = re.search(r'(?:id=|/d/)([a-zA-Z0-9_-]{10,})', x)
                if match:
                    file_id = match.group(1)
                    return f'<a href="https://drive.google.com/file/d/{file_id}/view" target="_blank">Lihat</a>'
            return ""

        for col in ["evidence1", "evidence2", "evidence3"]:
            df_filtered[col] = df_filtered[col].apply(to_view_link)

        # --- Reorder columns ---
        columns = [
            "No.", "area", "regional", "site_id", "site_name",
            "tanggal_pengisian", "jumlah_pengisian_liter", "liter_per_hari",
            "liter_terpakai", "persentase_terpakai", "tanggal_habis",
            "status_bbm", "evidence1", "evidence2", "evidence3"
        ]
        df_filtered = df_filtered[columns]

        # --- Generate HTML table ---
        table_rows = ""
        for _, row in df_filtered.iterrows():
            status_color = {
                "Segera Isi BBM": "#ed9d9d",
                "BBM menipis": "#d79c44",
                "Aman": "#7efe7e"
            }.get(row["status_bbm"], "#ffffff")

            table_rows += "<tr>"
            for col in columns:
                style = f"background-color:{status_color};" if col == "status_bbm" else ""
                table_rows += f"<td style='{style}'>{row[col]}</td>"
            table_rows += "</tr>"

        html_code = f"""
        <style>
            table {{
                width: 100%;
                border-collapse: collapse;
                font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 16px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: center;
                vertical-align: middle;
            }}
            th {{
                background-color: #f2f2f2;
            }}
            tbody tr:nth-child(even) {{ background-color: #f9f9f9; }}
            tbody tr:nth-child(odd) {{ background-color: #ffffff; }}
            tr:hover {{ background-color: #e6f7ff; }}
        </style>
        <h5 style="font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 900; font-size: 18px;">
            📌 Hanya data dengan tanggal pengisian terbaru per site
        </h5>
        <table>
            <thead>
                <tr>{''.join([f"<th>{col.replace('_', ' ').title()}</th>" for col in columns])}</tr>
            </thead>
            <tbody>{table_rows}</tbody>
        </table>
        """

        components.html(html_code, height=700, scrolling=True)

        # --- Prepare and show download button ---
        to_export = df_filtered.copy()
        for col in ['evidence1', 'evidence2', 'evidence3']:
            to_export[col] = to_export[col].str.extract(r'href="([^"]+)"')
        to_export["tanggal_pengisian"] = to_export["tanggal_pengisian"].astype(str)

        excel_buffer = io.BytesIO()
        to_export.to_excel(excel_buffer, index=False)
        excel_data = excel_buffer.getvalue()

        # Spacing then download button
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 Download Excel",
            data=excel_data,
            file_name="tracker_pengisian_bbm.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Gagal memuat data tracker: {e}")

def app():
    st.title("📊 Dashboard Tracker BBM")

    tabs = st.tabs([
        "⛽ Input Data Pengisian BBM",
        "📄 Tracker Pengisian BBM",
        "📈 Visualisasi"
    ])

    with tabs[0]:
        app_tab1()

    with tabs[1]:
        #st.info("📄 Tracker Pengisian BBM.")
        app_tab2()

    with tabs[2]:
        st.info("📈 Visualisasi belum diimplementasikan.")
        # from tracker_bbm_tab3 import app_tab3
        # app_tab3()
