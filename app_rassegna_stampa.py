
import streamlit as st
import os
import base64
from datetime import date
from pathlib import Path
from drive_utils import (
    get_drive_service,
    get_or_create_folder,
    upload_pdf_to_drive,
    list_pdfs_in_folder,
    download_pdf,
    FOLDER_NAME
)

# === LOGO ===
st.image("logo.png", width=200)

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

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def dashboard():
    st.title("Rassegna Stampa PDF")
    oggi = date.today().strftime("%Y.%m.%d")
    pdf_filename = f"rassegna_{oggi}.pdf"
    local_path = os.path.join(TEMP_DIR, pdf_filename)

    # === Solo per ADMIN: pulsante per connettere Drive ===
    if st.session_state.username == "A1":
        if st.button("🔗 Connetti a Google Drive"):
            service = get_drive_service()
            folder_id = get_or_create_folder(service, FOLDER_NAME)
            st.success(f"Cartella '{FOLDER_NAME}' pronta su Google Drive!")

    # === Prosegui solo se connesso ===
    try:
        service = get_drive_service()
        folder_id = get_or_create_folder(service, FOLDER_NAME)
    except Exception as e:
        st.error("⚠️ Errore nella connessione a Google Drive. Clicca 'Connetti a Google Drive' se non l'hai ancora fatto.")
        return

    # === AREA ADMIN ===
    if st.session_state.username == "A1":
        st.subheader("Carica la rassegna stampa in PDF")
        uploaded_file = st.file_uploader("Scegli un file PDF", type="pdf")
        if uploaded_file:
            with open(local_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            upload_pdf_to_drive(service, folder_id, local_path, pdf_filename)
            st.success(f"File caricato su Google Drive come: {pdf_filename}")
            st.rerun()

    # === LISTA FILE PDF ===
    st.subheader("Archivio Rassegne")
    files = list_pdfs_in_folder(service, folder_id)
    if files:
        date_options = [f["name"].replace("rassegna_", "").replace(".pdf", "") for f in files]
        selected_date = st.selectbox("Seleziona una data", date_options)
        selected_file = f"rassegna_{selected_date}.pdf"
        file_id = next((f["id"] for f in files if f["name"] == selected_file), None)
        selected_local_path = os.path.join(TEMP_DIR, selected_file)
        if file_id:
            download_pdf(service, file_id, selected_local_path)
            with open(selected_local_path, "rb") as f:
                st.download_button(f"Scarica rassegna {selected_date}", data=f, file_name=selected_file)
            show_pdf(selected_local_path)
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
