import streamlit as st
import os
import base64
import csv
import pytz
from datetime import date, datetime
from pathlib import Path
from drive_utils import (
    get_drive_service,
    get_or_create_folder,
    upload_pdf_to_drive,
    list_pdfs_in_folder,
    download_pdf,
    FOLDER_NAME
)

# === CONFIGURAZIONE ===
TEMP_DIR = "temp_pdfs"
Path(TEMP_DIR).mkdir(exist_ok=True)

USER_CREDENTIALS = {
    "A1": "A1",
    "U1": "P1",
    "U2": "P2",
    "U3": "P3",
    "U4": "P4",
    "U5": "P5",
    "U6": "P6",
    "U7": "P7",
    "U8": "P8",
    "U9": "P9",
    "U10": "P10"
}

# === LOGO ===
st.image("logo.png", width=200)

# === Blocco accesso da Desktop ===
st.markdown("""
<style>
body {
    position: relative; /* Necessario per posizionare il blocker in modo assoluto rispetto al body */
}

@media (min-width: 769px) {
    .blocker {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: rgba(0,0,0,0.95);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        color: white;
        font-family: sans-serif;
        text-align: center;
    }

    .blocker h1 {
        font-size: 2em;
        margin-bottom: 0.5em;
    }

    .blocker p {
        font-size: 1.2em;
        max-width: 80%;
    }

    .stApp {
        filter: blur(4px);
        pointer-events: none;
    }
}
</style>

<div class="blocker">
    <h1>Accesso da Desktop Disabilitato</h1>
    <p>Questa applicazione è ottimizzata solo per smartphone e tablet.<br>Per favore, accedi da un dispositivo mobile.</p>
</div>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

def login():
    st.title("Accesso Rassegna Stampa")
    username = st.text_input("Nome utente", key="username_input")
    password = st.text_input("Password", type="password", key="password_input")
    if st.button("Accedi"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Credenziali non valide")

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
    oggi = date.today().strftime("%Y.%m.%d")

    try:
        service = get_drive_service()
        folder_id = get_or_create_folder(service, FOLDER_NAME)
        files = list_pdfs_in_folder(service, folder_id)
    except Exception as e:
        st.error("⚠️ Errore nella connessione a Google Drive. Clicca 'Connetti a Google Drive' se non l'hai ancora fatto.")
        return

    if st.session_state.username == "A1":
        st.subheader("Carica la rassegna stampa in PDF")
        uploaded_files = st.file_uploader("Scegli uno o più file PDF", type="pdf", accept_multiple_files=True)

        if uploaded_files:
            existing_filenames = [f["name"] for f in files]
            for uploaded_file in uploaded_files:
                filename = uploaded_file.name
                local_path = os.path.join(TEMP_DIR, filename)
                if filename in existing_filenames:
                    st.warning(f"❗ Il file '{filename}' è già presente su Drive.")
                    continue
                with open(local_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                upload_pdf_to_drive(service, folder_id, local_path, filename)
                st.success(f"✅ Caricato: {filename}")
            st.rerun()

    st.subheader("Archivio Rassegne")
    if files:
        date_options = [f["name"].replace(".pdf", "") for f in files if f["name"].endswith(".pdf")]
        selected_date = st.selectbox("Seleziona una data", date_options)
        selected_file = f"{selected_date}.pdf"
        file_id = next((f["id"] for f in files if f["name"] == selected_file), None)
        selected_local_path = os.path.join(TEMP_DIR, selected_file)

        if file_id:
            download_pdf(service, file_id, selected_local_path)
            with open(selected_local_path, "rb") as f:
                st.download_button(f"Scarica rassegna {selected_date}", data=f, file_name=selected_file)
                log_visualizzazione(st.session_state.username, selected_file)
    else:
        st.info("Nessun file PDF trovato su Google Drive.")

def main():
    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.write(f"Utente: {st.session_state.username}")
        if st.sidebar.button("Esci"):
            st.session_state.logged_in = False
            st.session_state.username = ""
        dashboard()

main()
