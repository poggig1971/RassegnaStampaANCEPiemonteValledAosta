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
FOLDER_ID = "1eehj6KKG3W6bGdiT10ct4_-HFzLtD_p3"  # ID cartella Archivio Rassegna

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

def upload_pdf_to_drive(service, file_obj, drive_filename, is_memory_file=False, overwrite=False):
    existing_files = service.files().list(
        q=f"'{FOLDER_ID}' in parents and name='{drive_filename}' and trashed=false",
        fields='files(id, name)'
    ).execute().get("files", [])

    if existing_files:
        if overwrite:
            for f in existing_files:
                service.files().delete(fileId=f['id']).execute()
            st.info(f"ℹ️ Il file '{drive_filename}' è stato sovrascritto.")
        else:
            st.warning(f"⚠️ Il file '{drive_filename}' è già presente su Google Drive. Upload annullato.")
            return existing_files[0]['id']

    file_metadata = {
        'name': drive_filename,
        'parents': [FOLDER_ID]
    }

    if is_memory_file:
        if hasattr(file_obj, 'getvalue'):
            content = file_obj.getvalue()
            if isinstance(content, str):
                file_obj = io.BytesIO(content.encode("utf-8"))
            else:
                file_obj = io.BytesIO(content)
        media = MediaIoBaseUpload(file_obj, mimetype='application/pdf' if drive_filename.endswith('.pdf') else 'text/csv')
    else:
        media = MediaFileUpload(file_obj, mimetype='application/pdf')

    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def list_pdfs_in_folder(service):
    query = f"'{FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false"
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

def append_log_entry(service, user_email, file_uploaded):
    import datetime

    log_filename = "log_accessi.txt"
    query = f"'{FOLDER_ID}' in parents and name='{log_filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    log_content = ""
    log_line = f"{datetime.datetime.now().isoformat()} - {user_email} ha caricato {file_uploaded}\n"

    if files:
        log_file_id = files[0]['id']
        request = service.files().get_media(fileId=log_file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        log_content = fh.getvalue().decode("utf-8")
        service.files().delete(fileId=log_file_id).execute()

    updated_content = log_content + log_line
    media = MediaIoBaseUpload(io.BytesIO(updated_content.encode("utf-8")), mimetype="text/plain")

    service.files().create(
        body={'name': log_filename, 'parents': [FOLDER_ID]},
        media_body=media,
        fields='id'
    ).execute()
