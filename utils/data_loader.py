import pandas as pd
import io
import json
import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import geopandas as gpd
import xml.etree.ElementTree as ET
import pandas as pd
from shapely.geometry import Point
import re
import os
import tempfile
import toml
import yaml 


def get_drive():
    # Automatically switch based on what's available in secrets
    if "google_service_account" in st.secrets:
        return get_drive_service()
    elif "google_oauth" in st.secrets:
        return get_drive_oauth()
    else:
        raise RuntimeError("No valid Google credentials found in Streamlit secrets.")

def get_drive_service():
    gauth = GoogleAuth()

    # Load credentials from Streamlit secrets
    service_info = st.secrets["google_service_account"]
    client_email = service_info["client_email"]

    # Save credentials temporarily
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
        json.dump(dict(service_info), temp_file)
        temp_file_path = temp_file.name

    # ✅ Define full required settings
    gauth.settings = {
        "client_config_backend": "service",
        "service_config": {
            "client_json_file_path": temp_file_path,
            "client_user_email": client_email,
        },
        # ✅ Required to avoid KeyError on oauth_scope
        "oauth_scope": [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
        ],
    }

    # Authenticate
    gauth.ServiceAuth()
    return GoogleDrive(gauth)

def get_drive_oauth():
    # Define paths
    project_root = os.path.dirname(os.path.abspath(__file__))
    creds_dir = os.path.join(project_root, '..')  # one level up = dashboard root
    secrets_file = os.path.join(creds_dir, "client_secrets.json")
    token_file = os.path.join(creds_dir, "token.json")
    settings_file = os.path.join(creds_dir, "settings.yaml")

    # Write settings.yaml dynamically
    with open(settings_file, "w") as f:
        f.write(f"""
client_config_backend: file
client_config_file: {secrets_file.replace("\\\\", "/")}

save_credentials: True
save_credentials_backend: file
save_credentials_file: {token_file.replace("\\\\", "/")}

get_refresh_token: True
oauth_scope:
  - https://www.googleapis.com/auth/drive
""")

    # Use the settings file to initialize auth
    gauth = GoogleAuth(settings_file=settings_file)
    gauth.LocalWebserverAuth()  # Opens browser the first time only

    return GoogleDrive(gauth)

# --- Constants ---
drive = get_drive()
FOLDER_ID = "1qAn7O6QEahUtVhAxRfLzDZZ36s5v2_fk"  # <- Your actual folder ID

def list_files_in_folder(drive, folder_id):
    """List all files in a specific Google Drive folder."""
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
    return file_list

# --- Read an Excel file from Drive by file ID ---
def read_excel_from_drive(drive, file_id, use_multi_header=False):
    file = drive.CreateFile({'id': file_id})
    content = file.GetContentString(encoding='ISO-8859-1')

    if use_multi_header:
        df = pd.read_excel(io.BytesIO(content.encode('ISO-8859-1')), header=[0, 1])
        df.columns = [
            f"{col[0]} - {col[1]}" if str(col[1]).strip().lower() != "nan" and not str(col[1]).lower().startswith("unnamed")
            else str(col[0]).strip()
            for col in df.columns.values
        ]
    else:
        df = pd.read_excel(io.BytesIO(content.encode('ISO-8859-1')))

    return df

# --- Load all daily Excel files from Drive ---
@st.cache_data(ttl=3600)
def load_all_daily_files():
    files = list_files_in_folder(drive, FOLDER_ID)
    
    # Filter only files starting with 'daily'
    daily_files = [
        f for f in files
        if f['title'].lower().startswith("daily") and f['title'].endswith(".xlsx")
    ]

    if not daily_files:
        st.warning("No daily files found in Google Drive.")
        return pd.DataFrame()

    df_all = []
    for f in daily_files:
        try:
            df = read_excel_from_drive(drive, f['id'])
            df_all.append(df)
        except Exception as e:
            print(f"[ERROR] Failed to read file {f['title']}: {e}")

    if not df_all:
        return pd.DataFrame()

    return pd.concat(df_all, ignore_index=True)

import geopandas as gpd

# --- Read KML file from Drive by filename ---
@st.cache_data(ttl=3600)
def parse_description(desc):
    """Extract fields from <description> CDATA HTML."""
    fields = {
        'Site ID': '',
        'Site Name': '',
        'Longitude': '',
        'Latitude': '',
        'Area': '',
        'Regional': '',
        'NS': '',
        'Site Class': '',
        'Target': '',
        'Status': ''
    }
    if not desc:
        return fields

    for key in fields:
        match = re.search(rf"<b>{key}:</b>\s*(.*?)<br>", desc)
        if match:
            fields[key] = match.group(1).strip()
    return fields

@st.cache_data(ttl=3600)
def load_kml_file(_drive, filename="site_sewa_daya_2025.kml"):
    file = next((f for f in list_files_in_folder(_drive, FOLDER_ID) if f['title'].lower() == filename.lower()), None)
    if not file:
        st.warning("KML file not found.")
        return gpd.GeoDataFrame()

    content = file.GetContentString()

    try:
        root = ET.fromstring(content)
        ns = {"kml": "http://www.opengis.net/kml/2.2"}

        placemarks = root.findall(".//kml:Placemark", ns)
        data = []

        for placemark in placemarks:
            name = placemark.find("kml:name", ns)
            point = placemark.find(".//kml:Point", ns)
            coords = point.find("kml:coordinates", ns) if point is not None else None
            description_elem = placemark.find("kml:description", ns)

            if coords is not None:
                lon, lat, *_ = coords.text.strip().split(",")

                # Parse description
                description = description_elem.text if description_elem is not None else ""
                extra_fields = parse_description(description)

                data.append({
                    "Name": name.text if name is not None else "Unnamed Site",
                    "Longitude": float(lon),
                    "Latitude": float(lat),
                    "geometry": Point(float(lon), float(lat)),
                    "description": description,
                    **extra_fields  # Unpack the parsed values
                })

        if not data:
            st.warning("No valid placemarks with coordinates found in the KML.")
            return gpd.GeoDataFrame()

        df = pd.DataFrame(data)
        gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

        # Optional: add lat/lon columns for pydeck or folium
        gdf["lat"] = gdf.geometry.y
        gdf["lon"] = gdf.geometry.x

        return gdf

    except Exception as e:
        st.error(f"Failed to parse KML: {e}")
        return gpd.GeoDataFrame()
    
@st.cache_data(ttl=3600)
def load_all_weekly_files():
    files = list_files_in_folder(drive, FOLDER_ID)
    
    # Filter only files starting with 'weekly'
    weekly_files = [
        f for f in files
        if f['title'].lower().startswith("weekly") and f['title'].endswith(".xlsx")
    ]

    if not weekly_files:
        st.warning("No weekly files found in Google Drive.")
        return pd.DataFrame()

    df_all = []
    for f in weekly_files:
        try:
            df = read_excel_from_drive(drive, f['id'])
            df_all.append(df)
        except Exception as e:
            print(f"[ERROR] Failed to read file {f['title']}: {e}")

    if not df_all:
        return pd.DataFrame()

    return pd.concat(df_all, ignore_index=True)

def find_excel_files(drive, prefix=""):
    file_list = drive.ListFile({'q': f"title contains '{prefix}' and trashed=false"}).GetList()
    return [{'id': file['id'], 'title': file['title']} for file in file_list if file['title'].endswith('.xlsx')]

@st.cache_data(ttl=3600)
def load_penalty_data():
    drive = get_drive()
    penalty_files = find_excel_files(drive, prefix="penalty")

    df_list = []
    for file in penalty_files:
        try:
            file_stream = read_excel_from_drive(drive, file['id'], use_multi_header=True)
            df_list.append(file_stream)
        except Exception as e:
            st.warning(f"❌ Failed to read {file['title']}: {e}")

    return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

def upload_file_to_drive(file_obj, folder_id, filename):
    drive = get_drive_oauth()

    # Search for existing file with the same name in the folder
    file_list = drive.ListFile({
        "q": f"'{folder_id}' in parents and title = '{filename}' and trashed=false"
    }).GetList()

    if file_list:
        file = file_list[0]  # Use existing file
    else:
        file = drive.CreateFile({
            "title": filename,
            "parents": [{"id": folder_id}]
        })

    # Set content based on type
    if hasattr(file_obj, "read"):
        file.content = file_obj  # For BytesIO
    elif isinstance(file_obj, str):
        file.SetContentFile(file_obj)  # For path
    else:
        raise ValueError("file_obj must be a file path or file-like object")

    file.Upload()
    return file["id"]

def download_file_from_drive(drive, filename, folder_id):
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
    for f in file_list:
        if f['title'] == filename:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                local_path = tmp.name
                f.GetContentFile(local_path)
                return local_path
    raise FileNotFoundError(f"{filename} not found in Google Drive folder.")

def load_bbm_tracker_data(drive, site_file, bbm_file, folder_id):
    import pandas as pd
    from datetime import datetime

    # Load site metadata
    site_path = download_file_from_drive(drive, site_file, folder_id)
    df_site = pd.read_csv(site_path)

    # Load BBM refill log
    bbm_path = download_file_from_drive(drive, bbm_file, folder_id)
    df_bbm = pd.read_excel(bbm_path)

    # Merge on site_id
    df = pd.merge(df_bbm, df_site, on="site_id", how="left")

    # Convert date
    df['tanggal_pengisian'] = pd.to_datetime(df['tanggal_pengisian'], errors='coerce')
    df['liter_per_hari'] = pd.to_numeric(df['liter_per_hari'], errors='coerce')
    df['jumlah_pengisian_liter'] = pd.to_numeric(df['jumlah_pengisian_liter'], errors='coerce')

    # Calculate derived columns
    now = datetime.now()
    df['hari_terpakai'] = (now - df['tanggal_pengisian']).dt.days
    df['liter_terpakai'] = df['hari_terpakai'] * df['liter_per_hari']
    df['persentase_terpakai'] = (df['liter_terpakai'] / df['jumlah_pengisian_liter']) * 100
    df['tanggal_habis'] = df['tanggal_pengisian'] + pd.to_timedelta(
        df['jumlah_pengisian_liter'] / df['liter_per_hari'], unit='D'
    )

    def status(p):
        if p >= 90:
            return "Segera Isi BBM"
        elif p >= 80:
            return "BBM menipis"
        else:
            return "Aman"

    df['status_bbm'] = df['persentase_terpakai'].apply(status)

    # Reorder columns
    final_cols = [
        'area', 'regional', 'site_id', 'site_name', 'tanggal_pengisian',
        'jumlah_pengisian_liter', 'liter_per_hari', 'liter_terpakai',
        'persentase_terpakai', 'tanggal_habis', 'status_bbm',
        'evidence1', 'evidence2', 'evidence3'
    ]
    df = df[final_cols].copy()
    df.insert(0, 'No.', range(1, len(df) + 1))

    return df
