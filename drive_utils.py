import os
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import streamlit as st

print("✅ drive_utils.py caricato correttamente")

# === CONFIGURAZIONE ===
SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'token_drive.pkl')
FOLDER_NAME = "Rassegna ANCE"

def get_drive_service():
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error("⚠️ Errore durante il caricamento delle credenziali.")
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


def upload_pdf_to_drive(service, folder_id, local_path, drive_filename):
    file_metadata = {
        'name': drive_filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(local_path, mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')


def list_pdfs_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    return sorted(files, key=lambda x: x['name'])


def download_pdf(service, file_id, local_path):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        try:
            status, done = downloader.next_chunk()
        except Exception as e:
            st.error(f"Errore durante il download del PDF: {e}")
            break

