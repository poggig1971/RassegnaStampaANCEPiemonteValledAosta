# Questo è il file completo `app_rassegna_stampa.py` da usare con Streamlit
# Comprende: login, gestione utenti, creazione utenti.csv, dashboard PDF, log, statistiche

import streamlit as st
import os
from datetime import datetime, date
import pytz
import pandas as pd
from io import StringIO, BytesIO
from PIL import Image

# === CONFIGURAZIONE INIZIALE ===
favicon = Image.open("favicon_ance.png")
st.set_page_config(
    page_title="Rassegna ANCE Piemonte",
    page_icon=favicon,
    layout="centered"
)

st.markdown("""
    <head>
        <link rel="apple-touch-icon" sizes="180x180" href="https://raw.githubusercontent.com/poggig1971/RassegnaStampaANCEPiemonteValledAosta/main/public/app-icon.png">
        <meta name="apple-mobile-web-app-capable" content="yes">
    </head>
""", unsafe_allow_html=True)

from drive_utils import (
    get_drive_service,
    upload_pdf_to_drive,
    list_pdfs_in_folder,
    download_pdf,
    append_log_entry,
    read_users_file,
    update_user_password,
    delete_user,
    write_users_file
)

# === VARIABILI DI SESSIONE ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if "logged_files" not in st.session_state:
    st.session_state.logged_files = set()
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

# === FUNZIONE LOGIN ===
def login():
    st.markdown("## 🔐 Accesso alla Rassegna Stampa")
    username = st.text_input("🕤 Nome utente", key="username_input")
    password = st.text_input("🔑 Password", type="password", key="password_input")
    if st.button("Accedi"):
        service = get_drive_service()
        try:
            user_data = read_users_file(service)
            if username in user_data and user_data[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = user_data
                st.success("✅ Accesso effettuato")
                st.rerun()
            elif not user_data and username == "Admin" and password == "CorsoDuca15":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = {}
                st.warning("⚠️ File utenti.csv assente o vuoto. Accesso amministratore d’emergenza.")
                st.rerun()
            else:
                st.error("❌ Credenziali non valide. Riprova.")
        except Exception:
            if username == "Admin" and password == "CorsoDuca15":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = {}
                st.warning("⚠️ Errore nella lettura del file utenti. Accesso amministratore d’emergenza.")
                st.rerun()
            else:
                st.error("❌ Errore durante il login.")

# === FUNZIONI DI UTILITÀ ===
def is_valid_date_filename(filename):
    try:
        datetime.strptime(filename.replace(".pdf", ""), "%Y.%m.%d")
        return True
    except ValueError:
        return False

def log_visualizzazione(username, filename):
    tz = pytz.timezone("Europe/Rome")
    now = datetime.now(tz)
    data = now.strftime("%Y-%m-%d")
    ora = now.strftime("%H:%M:%S")
    try:
        service = get_drive_service()
        results = service.files().list(q="trashed = false", fields="files(id, name)").execute()
        files = results.get("files", [])
        file_id = next((f["id"] for f in files if f["name"] == "log_visualizzazioni.csv"), None)
        if file_id:
            content = download_pdf(service, file_id, return_bytes=True).decode("utf-8")
            df = pd.read_csv(StringIO(content))
        else:
            df = pd.DataFrame(columns=["data", "ora", "utente", "file"])
        df = pd.concat([df, pd.DataFrame([{"data": data, "ora": ora, "utente": username, "file": filename}])])
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        if file_id:
            service.files().delete(fileId=file_id).execute()
        upload_pdf_to_drive(service, csv_buffer, "log_visualizzazioni.csv", is_memory_file=True)
    except Exception as e:
        st.warning(f"⚠️ Errore nel salvataggio log: {e}")

# === FUNZIONE PRINCIPALE ===
def main():
    if not st.session_state.logged_in:
        login()
        return

    user = st.session_state.username
    service = get_drive_service()
    try:
        users = read_users_file(service)
    except:
        users = {}

    with st.sidebar:
        st.image("logo.png", width=120)
        st.success(f"🕤 {user}")
        page = st.radio("📋 Seleziona una pagina", ["Archivio", "Statistiche"])
        if st.button("🚪 Esci"):
            st.session_state.clear()
            st.rerun()

        if user == "Admin":
            if not users:
                st.info("📂 File utenti.csv mancante. Crealo ora.")
                if st.button("Crea file utenti.csv di default"):
                    users = {
                        "Admin": {
                            "password": "CorsoDuca15",
                            "password_cambiata": "no",
                            "data_modifica": date.today().isoformat()
                        }
                    }
                    write_users_file(service, users)
                    st.success("File creato con successo.")
                    st.rerun()
            with st.expander("👥 Gestione utenti"):
                nuovo_user = st.text_input("Nuovo utente")
                nuova_pw = st.text_input("Password", type="password")
                if st.button("Salva utente"):
                    update_user_password(service, users, nuovo_user, nuova_pw)
                    st.success("Utente aggiornato.")
                    st.rerun()
                user_to_delete = st.selectbox("Elimina utente", [u for u in users if u != "Admin"])
                if st.button("Elimina"):
                    delete_user(service, users, user_to_delete)
                    st.warning(f"Utente '{user_to_delete}' rimosso.")
                    st.rerun()
        else:
            with st.expander("🔑 Cambia password"):
                old = st.text_input("Vecchia password", type="password", key="old")
                new = st.text_input("Nuova password", type="password", key="new")
                conf = st.text_input("Conferma nuova password", type="password", key="conf")
                if st.button("Aggiorna password"):
                    if old != users[user]["password"]:
                        st.error("Vecchia password errata.")
                    elif new != conf:
                        st.warning("Le nuove password non coincidono.")
                    else:
                        update_user_password(service, users, user, new)
                        st.success("Password aggiornata.")
                        st.rerun()

    if page == "Archivio":
        from dashboard import dashboard
        dashboard()
    elif page == "Statistiche":
        from statistiche import mostra_statistiche
        if user == "Admin":
            mostra_statistiche()
        else:
            st.warning("Accesso riservato all'amministratore.")

main()
