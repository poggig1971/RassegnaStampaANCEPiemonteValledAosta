
import os
import pickle
import io
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.file']
TOKEN_PATH = 'token_drive.pkl'
FOLDER_NAME = 'Rassegna ANCE'


def authenticate():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('.streamlit/client_secret.json', SCOPES)
            auth_url, _ = flow.authorization_url(prompt='consent')

            st.warning("🔐 Autenticazione richiesta")
            st.markdown(f"[Clicca qui per autorizzare l'accesso a Google Drive]({auth_url})")
            auth_code = st.text_input("Inserisci il codice di autorizzazione", type="default")

            if st.button("Conferma codice"):
                try:
                    flow.fetch_token(code=auth_code)
                    creds = flow.credentials
                    with open(TOKEN_PATH, 'wb') as token:
                        pickle.dump(creds, token)
                    st.success("✅ Autenticazione completata con successo. Ricarica l'app.")
                    st.stop()
                except Exception as e:
                    st.error(f"Errore durante l'autenticazione: {e}")
                    st.stop()
            else:
                st.stop()
    return creds


def get_drive_service():
    creds = authenticate()
    return build('drive', 'v3', credentials=creds)

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
    return sorted(results.get('files', []), key=lambda x: x['name'], reverse=True)

def download_pdf(service, file_id, local_path):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
