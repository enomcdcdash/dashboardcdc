import os
import json
import tempfile
import pandas as pd
from io import BytesIO
import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

@st.cache_resource
def get_drive():
    if "google_service_account" in st.secrets:
        return get_drive_service()
    elif "google_oauth" in st.secrets and "STREAMLIT_SERVER_HEADLESS" not in os.environ:
        return get_drive_oauth()
    else:
        raise RuntimeError("No valid Google credentials found.")

def get_drive_service():
    gauth = GoogleAuth()
    service_info = dict(st.secrets["google_service_account"])
    client_email = service_info["client_email"]

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as f:
        json.dump(service_info, f)
        json_path = f.name

    gauth.settings = {
        "client_config_backend": "service",
        "service_config": {
            "client_json_file_path": json_path,
            "client_user_email": client_email
        },
        "oauth_scope": [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file"
        ],
    }

    gauth.ServiceAuth()
    return GoogleDrive(gauth)

def get_drive_oauth():
    project_root = os.path.dirname(os.path.abspath(__file__))
    creds_dir = os.path.join(project_root, '..')
    secrets_file = os.path.join(creds_dir, "client_secrets.json")
    token_file = os.path.join(creds_dir, "token.json")
    settings_file = os.path.join(creds_dir, "settings.yaml")

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

    gauth = GoogleAuth(settings_file=settings_file)
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)

# === Google Drive File Utilities ===

@st.cache_data(show_spinner="📥 Loading Excel from Drive...", ttl=3600)
def read_excel_from_drive(folder_id, filename):
    drive = get_drive()
    file_id = get_file_id_from_name(drive, folder_id, filename)
    file = drive.CreateFile({'id': file_id})
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        file.GetContentFile(tmp.name)
        df = pd.read_excel(tmp.name)
    return df

def upload_file_to_drive(file_obj, folder_id, filename):
    drive = get_drive()
    file_list = drive.ListFile({
        "q": f"'{folder_id}' in parents and title = '{filename}' and trashed=false"
    }).GetList()

    if file_list:
        file = file_list[0]
    else:
        file = drive.CreateFile({
            "title": filename,
            "parents": [{"id": folder_id}]
        })

    if hasattr(file_obj, "read"):
        file.content = file_obj
    elif isinstance(file_obj, str):
        file.SetContentFile(file_obj)
    else:
        raise ValueError("file_obj must be a file path or file-like object")

    file.Upload()
    return file["id"]

def download_file_from_drive(drive, filename, folder_id):
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
    for f in file_list:
        if f['title'] == filename:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                f.GetContentFile(tmp.name)
                return tmp.name
    raise FileNotFoundError(f"{filename} not found in Google Drive folder.")

@st.cache_data
def list_files_in_folder(folder_id):
    drive = get_drive()
    return drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()

def get_file_id_from_name(drive, folder_id, filename):
    file_list = drive.ListFile({
        "q": f"'{folder_id}' in parents and trashed=false and title='{filename}'"
    }).GetList()

    if not file_list:
        raise FileNotFoundError(f"File '{filename}' not found in folder '{folder_id}'")

    return file_list[0]["id"]

