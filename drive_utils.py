import os
import io
import json
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

print("✅ drive_utils.py caricato correttamente (versione cloud)")

# === CONFIGURAZIONE ===
SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_NAME = "Rassegna ANCE"

def get_drive_service():
    try:
        service_account_info = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error("⚠️ Errore nella connessione a Google Drive.")
        st.exception(e)
        st.stop()

def get_or_create_folder(service, folder_name):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_pdf_to_drive(service, folder_id, file_obj, drive_filename, is_memory_file=False):
    file_metadata = {
        'name': drive_filename,
        'parents': [folder_id]
    }

    if is_memory_file:
        # Per CSV o altri file in memoria (es. log visualizzazioni)
        if hasattr(file_obj, 'getvalue'):
            file_obj = io.BytesIO(file_obj.getvalue().encode("utf-8"))
        media = MediaIoBaseUpload(file_obj, mimetype='text/csv')
    else:
        # Per PDF locali sul disco
        media = MediaFileUpload(file_obj, mimetype='application/pdf')

    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def list_pdfs_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    return sorted(files, key=lambda x: x['name'])

def download_pdf(service, file_id, local_path=None, return_bytes=False):
    request = service.files().get_media(fileId=file_id)

    if return_bytes:
        fh = io.BytesIO()
    else:
        fh = io.FileIO(local_path, 'wb')

    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        try:
            status, done = downloader.next_chunk()
        except Exception as e:
            st.error(f"Errore durante il download del file: {e}")
            break

    if return_bytes:
        fh.seek(0)
        return fh.read()


