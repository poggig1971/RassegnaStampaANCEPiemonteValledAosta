import streamlit as st
import os
import base64
from datetime import date, datetime
from pathlib import Path
import csv
import pytz
import pickle

from drive_utils import (
    get_drive_service,
    get_or_create_folder,
    upload_pdf_to_drive,
    list_pdfs_in_folder,
    download_pdf,
    FOLDER_NAME
)

# === CONFIGURAZIONE ===
st.image("logo.png", width=200)
TEMP_DIR = "temp_pdfs"
Path(TEMP_DIR).mkdir(exist_ok=True)

AUTH_CACHE = "auth_cache.pkl"

USER_CREDENTIALS = {
    "A1": "A1",  # Admin
    "U1": "P1", "U2": "P2", "U3": "P3", "U4": "P4", "U5": "P5",
    "U6": "P6", "U7": "P7", "U8": "P8", "U9": "P9", "U10": "P10"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if "logged_files" not in st.session_state:
    st.session_state.logged_files = set()


def login():
    st.title("Accesso Rassegna Stampa")

    # Verifica credenziali salvate
    if os.path.exists(AUTH_CACHE):
        with open(AUTH_CACHE, "rb") as f:
            saved = pickle.load(f)
            username, password = saved.get("username"), saved.get("password")
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"✅ Login automatico come **{username}**")
                return

    # Accesso manuale
    username = st.text_input("Nome utente", key="username_input")
    password = st.text_input("Password", type="password", key="password_input")
    remember = st.checkbox("Ricorda le credenziali su questo PC")

    if st.button("Accedi"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username

            if remember:
                with open(AUTH_CACHE, "wb") as f:
                    pickle.dump({"username": username, "password": password}, f)

            st.success("✅ Accesso effettuato")
            st.rerun()
        else:
            st.error("❌ Credenziali non valide")


def is_valid_date_filename(filename):
    try:
        datetime.strptime(filename.replace(".pdf", ""), "%Y.%m.%d")
        return True
    except ValueError:
        return False


def log_visualizzazione(username, filename):
    log_path = "log_visualizzazioni.csv"
    tz = pytz.timezone("Europe/Rome")
    now = datetime.now(tz)
    data = now.strftime("%Y-%m-%d")
    ora = now.strftime("%H:%M:%S")

    file_exists = os.path.exists(log_path)
    with open(log_path, mode="a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["data", "ora", "utente", "file"])
        writer.writerow([data, ora, username, filename])

    try:
        service = get_drive_service()
        folder_id = get_or_create_folder(service, FOLDER_NAME)

        existing_files = list_pdfs_in_folder(service, folder_id)
        for f in existing_files:
            if f["name"] == "log_visualizzazioni.csv":
                service.files().delete(fileId=f["id"]).execute()

        upload_pdf_to_drive(service, folder_id, log_path, "log_visualizzazioni.csv")

    except Exception as e:
        st.warning(f"⚠️ Impossibile caricare il log su Drive: {e}")


def dashboard():
    st.title("Rassegna Stampa PDF")

    try:
        service = get_drive_service()
        folder_id = get_or_create_folder(service, FOLDER_NAME)
        files = list_pdfs_in_folder(service, folder_id)
    except Exception as e:
        st.error("⚠️ Errore nella connessione a Google Drive.")
        return

    st.caption(f"Aggiornato alle {datetime.now().strftime('%H:%M:%S')}")
    if st.button("Aggiorna elenco PDF"):
        st.rerun()

    # === Caricamento PDF (solo Admin) ===
    if st.session_state.username == "A1":
        st.subheader("Carica la rassegna stampa in PDF")
        uploaded_files = st.file_uploader("Scegli uno o più file PDF", type="pdf", accept_multiple_files=True)

        if uploaded_files:
            existing_filenames = [f["name"] for f in files]

            for uploaded_file in uploaded_files:
                filename = uploaded_file.name
                if not is_valid_date_filename(filename):
                    st.warning(f"⚠️ Il nome del file '{filename}' non rispetta il formato 'YYYY.MM.DD.pdf'.")
                    continue

                if filename in existing_filenames:
                    st.warning(f"❗ Il file '{filename}' è già presente su Drive.")
                    continue

                local_path = os.path.join(TEMP_DIR, filename)
                with open(local_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                upload_pdf_to_drive(service, folder_id, local_path, filename)
                st.success(f"✅ Caricato: {filename}")
            st.rerun()

    # === Archivio PDF ===
    st.subheader("Archivio Rassegne")

    date_options = sorted(
        [
            f["name"].replace(".pdf", "")
            for f in files
            if f["name"].lower().endswith(".pdf") and is_valid_date_filename(f["name"])
        ],
        reverse=True
    )

    if date_options:
        selected_date = st.selectbox("Seleziona una data", date_options)
        selected_file = f"{selected_date}.pdf"
        file_id = next((f["id"] for f in files if f["name"] == selected_file), None)
        selected_local_path = os.path.join(TEMP_DIR, selected_file)

        if file_id:
            download_pdf(service, file_id, selected_local_path)
            with open(selected_local_path, "rb") as f:
                st.download_button(f"Scarica rassegna {selected_date}", data=f, file_name=selected_file)

            if selected_file not in st.session_state.logged_files:
                log_visualizzazione(st.session_state.username, selected_file)
                st.session_state.logged_files.add(selected_file)
    else:
        st.info("Nessun file PDF trovato su Google Drive.")


def main():
    if not st.session_state.logged_in:
        login()
    else:
        with st.sidebar:
            st.write(f"👤 Utente: **{st.session_state.username}**")
            if st.button("Esci"):
                st.session_state.clear()
                st.rerun()
            if st.button("🔓 Esci e Dimentica"):
                if os.path.exists(AUTH_CACHE):
                    os.remove(AUTH_CACHE)
                st.session_state.clear()
                st.rerun()
        dashboard()


main()
