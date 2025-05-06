import streamlit as st
import os
import base64
from datetime import date, datetime
from pathlib import Path
import csv
import pytz
import pandas as pd
import matplotlib.pyplot as plt

from drive_utils import (
    get_drive_service,
    get_or_create_folder,
    upload_pdf_to_drive,
    list_pdfs_in_folder,
    download_pdf,
    FOLDER_NAME
)

# === CONFIGURAZIONE ===
col1, col2 = st.columns([3, 5])
with col1:
    st.image("logo.png", width=300)

TEMP_DIR = "temp_pdfs"
Path(TEMP_DIR).mkdir(exist_ok=True)

USER_CREDENTIALS = {
    "Admin": "CorsoDuca15",
    "Torino": "Torino",
    "Alessandria": "Alessandria",
    "Asti": "Asti",
    "Biella": "Biella",
    "Verbania": "Verbania",
    "Novara": "Novara",
    "Vercelli": "Vercelli",
    "Aosta": "Aosta",
    "Cuneo": "Cuneo",
    "Presidente": "Presidente"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if "logged_files" not in st.session_state:
    st.session_state.logged_files = set()

def login():
    st.markdown("## 🔐 Accesso alla Rassegna Stampa")
    username = st.text_input("👤 Nome utente", key="username_input")
    password = st.text_input("🔑 Password", type="password", key="password_input")
    if st.button("Accedi"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("✅ Accesso effettuato")
            st.rerun()
        else:
            st.error("❌ Credenziali non valide. Riprova.")

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
    st.markdown("## 📚 Archivio Rassegne")
    nome_utente = st.session_state.username
    if nome_utente == "Presidente":
        st.markdown("👑 **Benvenuto Presidente**")
        st.caption("Grazie.")
    else:
        st.markdown(f"👋 **Benvenuto da ANCE {nome_utente}!**")
        st.caption("Accedi alle rassegne stampa aggiornate giorno per giorno.")
    try:
        service = get_drive_service()
        folder_id = get_or_create_folder(service, FOLDER_NAME)
        files = list_pdfs_in_folder(service, folder_id)
    except Exception as e:
        st.error("⚠️ Errore nella connessione a Google Drive.")
        return

    st.caption(f"🕒 Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    if st.button("🔄 Aggiorna elenco PDF"):
        st.rerun()

    if st.session_state.username == "Admin":
        st.markdown("### 📤 Carica nuova rassegna stampa")
        uploaded_files = st.file_uploader("Seleziona uno o più file PDF", type="pdf", accept_multiple_files=True)
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

    date_options = sorted(
        [f["name"].replace(".pdf", "") for f in files if f["name"].lower().endswith(".pdf") and is_valid_date_filename(f["name"])],
        reverse=True
    )

    if date_options:
        selected_date = st.selectbox("📅 Seleziona una data", date_options)
        selected_file = f"{selected_date}.pdf"
        file_id = next((f["id"] for f in files if f["name"] == selected_file), None)
        selected_local_path = os.path.join(TEMP_DIR, selected_file)
        if file_id:
            download_pdf(service, file_id, selected_local_path)
            with open(selected_local_path, "rb") as f:
                st.download_button(f"⬇️ Scarica rassegna {selected_date}", data=f, file_name=selected_file)
            if selected_file not in st.session_state.logged_files:
                log_visualizzazione(st.session_state.username, selected_file)
                st.session_state.logged_files.add(selected_file)
    else:
        st.info("📭 Nessun file PDF trovato su Google Drive.")

def mostra_statistiche():
    st.markdown("## 📈 Statistiche di accesso")
    if st.session_state.username == "Admin" and os.path.exists("log_visualizzazioni.csv"):
    with open("log_visualizzazioni.csv", "rb") as f:
        st.download_button(
            label="⬇️ Scarica log visualizzazioni (CSV)",
            data=f,
            file_name="log_visualizzazioni.csv",
            mime="text/csv"
        )
    if not os.path.exists("log_visualizzazioni.csv"):
        st.info("Nessun dato ancora disponibile.")
        return
    df = pd.read_csv("log_visualizzazioni.csv")
    st.metric("Totale visualizzazioni", len(df))
    top_utenti = df['utente'].value_counts().head(5)
    st.markdown("### 👥 Utenti più attivi")
    st.bar_chart(top_utenti)
    top_file = df['file'].value_counts().head(5)
    st.markdown("### 📁 File più visualizzati")
    st.bar_chart(top_file)
    df['data'] = pd.to_datetime(df['data'])
    oggi = pd.to_datetime(datetime.now().date())
    ultimi_30 = df[df['data'] >= oggi - pd.Timedelta(days=30)]
    if ultimi_30.empty:
        st.info("📭 Nessun accesso negli ultimi 30 giorni.")
    else:
        st.markdown("### 📆 Accessi negli ultimi 30 giorni")
        daily = ultimi_30.groupby('data').size()
        st.line_chart(daily)

def main():
    if not st.session_state.logged_in:
        login()
    else:
        with st.sidebar:
            st.markdown("## ⚙️ Pannello")
            st.markdown(f"👤 Utente: **{st.session_state.username}**")
            page = st.radio("📋 Seleziona una pagina", ["Archivio", "Statistiche"])
            st.write("---")
            if st.button("🚪 Esci"):
                st.session_state.clear()
                st.rerun()
        if page == "Archivio":
            dashboard()
        elif page == "Statistiche":
            if st.session_state.username == "Admin":
                mostra_statistiche()
            else:
                st.warning("⚠️ Accesso riservato. Le statistiche sono visibili solo all'amministratore.")

main()
