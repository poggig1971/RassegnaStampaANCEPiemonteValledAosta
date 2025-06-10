import os
import io
import json
from datetime import datetime, date
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
import pandas as pd
from io import StringIO, BytesIO

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
            # Cancella tutti i duplicati (eccetto caso CSV log)
            if drive_filename != "log_visualizzazioni.csv":
                for f in existing_files:
                    service.files().delete(fileId=f['id']).execute()
            else:
                # ⚠️ Se è log_visualizzazioni.csv, tieni solo uno e cancella gli altri
                for f in existing_files[1:]:
                    service.files().delete(fileId=f['id']).execute()
        else:
            st.warning(f"⚠️ Il file '{drive_filename}' è già presente su Google Drive. Upload annullato.")
            return existing_files[0]['id']

    file_metadata = {'name': drive_filename, 'parents': [FOLDER_ID]}

    if is_memory_file:
        if hasattr(file_obj, 'getvalue'):
            content = file_obj.getvalue()
            if isinstance(content, str):
                file_obj = io.BytesIO(content.encode("utf-8"))
            else:
                file_obj = io.BytesIO(content)
        mimetype = 'application/pdf' if drive_filename.endswith('.pdf') else 'text/csv'
        media = MediaIoBaseUpload(file_obj, mimetype=mimetype)
    else:
        media = MediaFileUpload(file_obj, mimetype='application/pdf')

    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

    if is_memory_file:
        if hasattr(file_obj, 'getvalue'):
            content = file_obj.getvalue()
            if isinstance(content, str):
                file_obj = io.BytesIO(content.encode("utf-8"))
            else:
                file_obj = io.BytesIO(content)
        mimetype = 'application/pdf' if drive_filename.endswith('.pdf') else 'text/csv'
        media = MediaIoBaseUpload(file_obj, mimetype=mimetype)
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

def log_visualizzazione(service, utente, file_pdf):
    import pandas as pd
    from datetime import datetime
    from io import StringIO, BytesIO
    import pytz

    log_name = "log_visualizzazioni.csv"
    zona_italia = pytz.timezone("Europe/Rome")
    now = datetime.now(zona_italia)
    
    nuova_riga = {
        "data": now.strftime("%Y-%m-%d"),
        "ora": now.strftime("%H:%M:%S"),
        "utente": utente,
        "file": file_pdf
    }

    try:
        query = f"'{FOLDER_ID}' in parents and name='{log_name}' and trashed=false"
        result = service.files().list(q=query, fields="files(id, name)").execute()
        files = result.get("files", [])

        if files:
            file_id = files[0]["id"]
            content_bytes = download_pdf(service, file_id, return_bytes=True)
            content_str = content_bytes.decode("utf-8")
            df_esistente = pd.read_csv(StringIO(content_str))
        else:
            df_esistente = pd.DataFrame(columns=["data", "ora", "utente", "file"])

    except Exception as e:
        st.warning("⚠️ Errore nella lettura del file CSV, verrà ricreato.")
        df_esistente = pd.DataFrame(columns=["data", "ora", "utente", "file"])

    # Aggiungi nuova riga e rimuovi eventuali duplicati
    df_aggiornato = pd.concat([df_esistente, pd.DataFrame([nuova_riga])], ignore_index=True)
    df_aggiornato.drop_duplicates(subset=["data", "ora", "utente", "file"], inplace=True)

    try:
        csv_buffer = StringIO()
        df_aggiornato.to_csv(csv_buffer, index=False)
        upload_pdf_to_drive(
            service,
            BytesIO(csv_buffer.getvalue().encode("utf-8")),
            log_name,
            is_memory_file=True,
            overwrite=True
        )
        st.success(f"📌 Log visualizzazione aggiornato: {utente} ha consultato {file_pdf}.")
    except Exception as e:
        st.error("❌ Errore durante il salvataggio del file CSV.")
        st.exception(e)

    # 🔁 Log anche su file .txt tecnico
    try:
        append_txt_log_entry(service, utente, f"ha visualizzato il file {file_pdf}")
    except Exception as e:
        st.warning("⚠️ Impossibile scrivere nel log tecnico.")
        st.exception(e)




# === Gestione utenti ===

def read_users_file(service, filename="utenti.csv"):
    query = f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if not files:
        return {}
    file_id = files[0]['id']
    content = download_pdf(service, file_id, return_bytes=True).decode("utf-8")
    users = {}
    for line in content.strip().splitlines()[1:]:
        parts = line.strip().split(",")
        if len(parts) == 5:
            username, password, cambiata, data, email = parts
        else:
            username, password, cambiata, data = parts
            email = ""
        users[username] = {
            "password": password,
            "password_cambiata": cambiata,
            "data_modifica": data,
            "email": email
        }
    return users

def write_users_file(service, users_dict, filename="utenti.csv"):
    lines = ["username,password,password_cambiata,data_modifica,email"]
    for u, data in users_dict.items():
        email = data.get("email", "")
        lines.append(f"{u},{data['password']},{data['password_cambiata']},{data['data_modifica']},{email}")
    updated_content = "\n".join(lines)
    upload_pdf_to_drive(service, io.StringIO(updated_content), filename, is_memory_file=True, overwrite=True)

def update_user_password(service, users_dict, username, new_password, filename="utenti.csv"):
    update_user_info(service, users_dict, username, new_password=new_password, filename=filename)

def delete_user(service, users_dict, username, filename="utenti.csv"):
    if username in users_dict:
        del users_dict[username]
        write_users_file(service, users_dict, filename)

def update_user_info(service, users_dict, username, new_password=None, new_email=None, filename="utenti.csv"):
    if not users_dict or username not in users_dict:
        st.error("❌ Errore: l'utente non è presente nel dizionario.")
        return

    user_data = users_dict[username]

    if new_password:
        user_data["password"] = new_password
        user_data["password_cambiata"] = "yes"

    if new_email:
        user_data["email"] = new_email

    user_data["data_modifica"] = date.today().isoformat()
    users_dict[username] = user_data

    if not users_dict:
        st.error("❌ Errore: il file utenti risulterebbe vuoto. Operazione annullata.")
        return

    write_users_file(service, users_dict, filename)

def append_txt_log_entry(service, utente, azione_descrittiva, log_name="log_accessi.txt"):
    import pytz
    timestamp = datetime.now(pytz.timezone("Europe/Rome")).strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {utente} - {azione_descrittiva}\n"

    # Cerca TUTTI i file esistenti con quel nome
    query = f"'{FOLDER_ID}' in parents and name='{log_name}' and trashed=false"
    result = service.files().list(q=query, fields="files(id, name)").execute()
    files = result.get("files", [])

    content = ""

    # Unisci contenuti esistenti e cancella tutti i file duplicati
    for f in files:
        try:
            file_id = f["id"]
            content_bytes = download_pdf(service, file_id, return_bytes=True)
            content += content_bytes.decode("utf-8")
            service.files().delete(fileId=file_id).execute()
        except Exception as e:
            st.warning(f"⚠️ Problema con il file {log_name}. Verrà sovrascritto. Errore: {e}")

    # Aggiungi nuova riga
    updated_content = content + log_line
    media = MediaIoBaseUpload(io.BytesIO(updated_content.encode("utf-8")), mimetype="text/plain")

    # Crea un nuovo file unico
    service.files().create(
        body={'name': log_name, 'parents': [FOLDER_ID]},
        media_body=media,
        fields='id'
    ).execute()

    st.info(f"📄 Log tecnico aggiornato: {azione_descrittiva}")


