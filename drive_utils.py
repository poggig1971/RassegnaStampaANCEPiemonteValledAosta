import os
import io
import json
import datetime
import csv # Importato per una gestione più robusta dei CSV
import bcrypt # Importato per la gestione delle password hashate
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload

print("✅ drive_utils.py caricato correttamente (versione cloud)")

# --- CONFIGURAZIONE ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
# ID della cartella di Google Drive dove sono archiviati i file e i logs
# ASSICURATI CHE QUESTO ID SIA CORRETTO E CHE L'ACCOUNT DI SERVIZIO ABBIA I PERMESSI NECESSARI
FOLDER_ID = "1eehj6KKG3W6bGdiT10ct4_-HFzLtD_p3"

# --- FUNZIONI DI UTILITY ---

def get_drive_service():
    """Inizializza e restituisce un'istanza del servizio Google Drive API."""
    try:
        service_account_info = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
        creds = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error("⚠️ Errore critico: impossibile connettersi a Google Drive. Controlla le configurazioni di 'secrets.toml'.")
        st.exception(e) # Mostra i dettagli dell'eccezione per il debug
        st.stop() # Ferma l'esecuzione dell'app se non si può connettere a Drive

def upload_file_to_drive(service, file_obj, drive_filename, is_memory_file=False, overwrite=False, mime_type=None):
    """
    Carica un file su Google Drive. Può sovrascrivere un file esistente.
    file_obj: il percorso del file locale o un oggetto file-like (es. BytesIO).
    drive_filename: il nome del file su Google Drive.
    is_memory_file: True se file_obj è un oggetto file-like in memoria.
    overwrite: True per sovrascrivere file esistenti con lo stesso nome nella stessa cartella.
    mime_type: il tipo MIME del file (es. 'application/pdf', 'text/csv'). Se None, cercherà di indovinare.
    """
    # Determina il MIME type se non specificato
    if mime_type is None:
        if drive_filename.lower().endswith('.pdf'):
            mime_type = 'application/pdf'
        elif drive_filename.lower().endswith('.csv'):
            mime_type = 'text/csv'
        elif drive_filename.lower().endswith('.txt'):
            mime_type = 'text/plain'
        else:
            mime_type = 'application/octet-stream' # Tipo generico per dati binari

    existing_files = service.files().list(
        q=f"'{FOLDER_ID}' in parents and name='{drive_filename}' and trashed=false",
        fields='files(id, name)'
    ).execute().get("files", [])

    if existing_files:
        if overwrite:
            for f in existing_files:
                service.files().delete(fileId=f['id']).execute()
            # st.info(f"ℹ️ Il file '{drive_filename}' è stato sovrascritto.") # Questo feedback è meglio darlo nell'app principale
        else:
            # st.warning(f"⚠️ Il file '{drive_filename}' è già presente su Google Drive. Upload annullato.") # Feedback nell'app principale
            return existing_files[0]['id'] # Restituisce l'ID del file esistente se non si deve sovrascrivere

    file_metadata = {
        'name': drive_filename,
        'parents': [FOLDER_ID]
    }

    if is_memory_file:
        # Assicurati che l'oggetto in memoria sia trattato come BytesIO
        if isinstance(file_obj, io.StringIO):
            file_obj = io.BytesIO(file_obj.getvalue().encode("utf-8"))
        elif not isinstance(file_obj, io.BytesIO):
             # Se non è StringIO o BytesIO ma è in memoria, prova a convertirlo
            if hasattr(file_obj, 'getvalue'):
                content = file_obj.getvalue()
                if isinstance(content, str):
                    file_obj = io.BytesIO(content.encode("utf-8"))
                else: # Presume bytes
                    file_obj = io.BytesIO(content)
            else:
                st.error(f"Errore: file_obj in memoria non è un formato supportato per '{drive_filename}'.")
                return None

        media = MediaIoBaseUpload(file_obj, mimetype=mime_type, resumable=True)
    else:
        # MediaFileUpload è per file locali
        media = MediaFileUpload(file_obj, mimetype=mime_type, resumable=True)

    try:
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        st.error(f"Errore durante il caricamento del file '{drive_filename}' su Drive: {e}")
        return None

def list_pdfs_in_folder(service):
    """Elenca tutti i file PDF nella cartella Drive specificata."""
    query = f"'{FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    # Ordina i file per nome (che dovrebbe contenere la data) in ordine decrescente
    return sorted(files, key=lambda x: x['name'], reverse=True)

def download_file_from_drive(service, file_id, local_path=None, return_bytes=False):
    """
    Scarica un file da Google Drive.
    file_id: ID del file su Drive.
    local_path: Percorso locale dove salvare il file (se non si vuole ritornare i bytes).
    return_bytes: Se True, la funzione ritorna il contenuto del file come bytes.
    """
    request = service.files().get_media(fileId=file_id)

    if return_bytes:
        fh = io.BytesIO()
    else:
        # Assicurati che la directory esista se salvi in locale
        if local_path:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
        fh = io.FileIO(local_path, 'wb')

    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        try:
            status, done = downloader.next_chunk()
        except Exception as e:
            st.error(f"Errore durante il download del file con ID {file_id}: {e}")
            return None # Restituisce None in caso di errore di download

    if return_bytes:
        fh.seek(0)
        return fh.read()
    return local_path # Ritorna il percorso locale se salvato

def append_log_entry(service, username, filename, action="visualizzato"):
    """
    Registra un'azione (es. visualizzazione, caricamento) nel log_visualizzazioni.csv su Drive.
    Crea il file se non esiste.
    """
    log_filename = "log_visualizzazioni.csv"
    log_file_id = None
    log_content_bytes = b''
    headers = ["data", "utente", "file", "azione"]

    # Cerca il file di log esistente
    query = f"'{FOLDER_ID}' in parents and name='{log_filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if files:
        log_file_id = files[0]['id']
        try:
            log_content_bytes = download_file_from_drive(service, log_file_id, return_bytes=True)
            if not log_content_bytes: # Se il download fallisce o il file è vuoto
                log_content_bytes = b''
        except Exception as e:
            st.warning(f"Impossibile scaricare il log esistente '{log_filename}': {e}. Verrà creato un nuovo log o sovrascritto.")
            log_content_bytes = b'' # Inizia con contenuto vuoto in caso di errore di download

    # Preparazione della nuova riga del log
    now = datetime.datetime.now().isoformat()
    new_entry_row = [now, username, filename, action]

    # Processa il contenuto esistente e aggiungi la nuova riga
    output_buffer = io.StringIO()
    writer = csv.writer(output_buffer)

    if log_content_bytes:
        # Decodifica il contenuto esistente e lo legge come CSV
        existing_lines = log_content_bytes.decode('utf-8').strip().splitlines()
        reader = csv.reader(io.StringIO("\n".join(existing_lines)))
        
        # Determina se l'header è già presente
        current_headers = []
        if existing_lines:
            current_headers = next(reader) # Legge la prima riga come header
            if current_headers != headers: # Se l'header non corrisponde, riscrivi
                writer.writerow(headers)
                # Re-aggiungi le righe vecchie se l'header non corrisponde
                for row in reader:
                    writer.writerow(row)
            else: # Se l'header corrisponde, scrivi solo le righe esistenti
                writer.writerow(current_headers) # Scrivi l'header letto
                for row in reader:
                    writer.writerow(row)
        else: # Se il file era vuoto, scrivi l'header
            writer.writerow(headers)
    else: # Se il log non esisteva o era vuoto, scrivi l'header
        writer.writerow(headers)

    writer.writerow(new_entry_row) # Aggiungi la nuova riga

    updated_content = output_buffer.getvalue().encode("utf-8")

    # Carica il log aggiornato su Drive (sovrascrivendo il vecchio)
    if log_file_id:
        # Se il file esisteva, eliminalo prima di caricarne uno nuovo
        # Questo è un approccio semplice per appendere, ma un update potrebbe essere più efficiente
        service.files().delete(fileId=log_file_id).execute()

    upload_file_to_drive(
        service,
        io.BytesIO(updated_content),
        log_filename,
        is_memory_file=True,
        overwrite=True, # Sempre sovrascrivere il log
        mime_type='text/csv'
    )
    # st.success(f"Log: {action} {filename} by {username}") # Feedback per debug


# --- Funzioni di Gestione Utenti ---

def read_users_file(service, filename="utenti.csv"):
    """
    Legge il file utenti.csv da Google Drive e restituisce un dizionario.
    Le password nel file CSV devono essere HASHATE.
    """
    users = {}
    query = f"'{FOLDER_ID}' in parents and name='{filename}' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])

    if not files:
        return {} # Ritorna un dizionario vuoto se il file non esiste

    file_id = files[0]['id']
    try:
        content_bytes = download_file_from_drive(service, file_id, return_bytes=True)
        if not content_bytes:
            return {} # Ritorna vuoto se il download fallisce o il file è vuoto

        content = content_bytes.decode("utf-8")
        csv_file = io.StringIO(content)
        reader = csv.reader(csv_file)

        header = next(reader, None) # Legge l'header, None se il file è vuoto dopo la prima riga
        if header is None: # File vuoto o con solo l'header
            return {}

        # Assicurati che l'header sia come previsto
        expected_header = ["username", "password", "password_cambiata", "data_modifica"]
        if header != expected_header:
            st.warning(f"Attenzione: l'header del file '{filename}' non corrisponde all'atteso. "
                       f"Atteso: {expected_header}, Trovato: {header}. Potrebbero esserci problemi di lettura.")
            # Potresti aggiungere qui una logica per cercare comunque i campi se l'ordine cambia

        for row in reader:
            if len(row) >= 4: # Assicurati che ci siano abbastanza colonne
                username, hashed_password, password_changed, data_modifica = row
                users[username] = {
                    "password": hashed_password, # Questa DEVE essere la password hashata
                    "password_cambiata": password_changed,
                    "data_modifica": data_modifica
                }
    except Exception as e:
        st.error(f"Errore durante la lettura del file utenti.csv: {e}")
        return {} # Ritorna vuoto in caso di errore di lettura/parsing
    return users

def write_users_file(service, users_dict, filename="utenti.csv"):
    """
    Scrive il dizionario degli utenti in un file CSV e lo carica su Google Drive.
    Le password nel dizionario users_dict DEVONO essere HASHATE.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Scrivi l'header del CSV
    writer.writerow(["username", "password", "password_cambiata", "data_modifica"])

    # Scrivi i dati degli utenti
    for username, data in users_dict.items():
        writer.writerow([
            username,
            data["password"], # Questa DEVE essere la password hashata
            data.get("password_cambiata", "no"), # Usa .get per valori di default sicuri
            data.get("data_modifica", datetime.date.today().isoformat())
        ])

    file_content_bytes = output.getvalue().encode("utf-8")

    # Carica il file utenti.csv su Drive, sovrascrivendo quello esistente
    upload_file_to_drive(
        service,
        io.BytesIO(file_content_bytes),
        filename,
        is_memory_file=True,
        overwrite=True,
        mime_type='text/csv'
    )

def update_user_password(service, users_dict, username, new_password_hashed, filename="utenti.csv"):
    """
    Aggiorna la password (già hashata) di un utente specifico nel dizionario e salva il file.
    new_password_hashed: la password già hashata che deve essere salvata.
    """
    if username not in users_dict:
        # Se l'utente non esiste, lo aggiunge
        users_dict[username] = {
            "password": new_password_hashed,
            "password_cambiata": "yes",
            "data_modifica": datetime.date.today().isoformat()
        }
    else:
        # Se l'utente esiste, aggiorna la password e i metadati
        users_dict[username]["password"] = new_password_hashed
        users_dict[username]["password_cambiata"] = "yes"
        users_dict[username]["data_modifica"] = datetime.date.today().isoformat()
    write_users_file(service, users_dict, filename)

def delete_user(service, users_dict, username_to_delete, filename="utenti.csv"):
    """Elimina un utente dal dizionario e salva il file utenti.csv su Drive."""
    if username_to_delete in users_dict:
        del users_dict[username_to_delete]
        write_users_file(service, users_dict, filename)
