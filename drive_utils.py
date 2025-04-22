import os
import pickle
import io
import streamlit as st
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

print("✅ drive_utils.py caricato correttamente")

SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'token_drive.pkl')

# Nome predefinito della cartella su Google Drive
FOLDER_NAME = "Rassegna ANCE"

def authenticate():
    creds = None

    # Usa token locale se esiste
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    # Altrimenti, avvia l'autenticazione
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                st.error(f"Errore durante il refresh del token: {e}")
                os.remove(TOKEN_PATH)
                st.stop()
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    '.streamlit/client_secret.json', SCOPES
                )
                creds = flow.run_local_server(port=8502)
                with open(TOKEN_PATH, 'wb') as token:
                    pickle.dump(creds, token)
                st.success("✅ Autenticazione completata con successo. L'app verrà ricaricata.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Errore durante l'autenticazione: {e}")
                st.stop()

    return creds


def get_drive_service():
    try:
        creds = authenticate()
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
