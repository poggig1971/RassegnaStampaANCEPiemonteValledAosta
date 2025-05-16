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

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if "logged_files" not in st.session_state:
    st.session_state.logged_files = set()
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

def login():
    st.markdown("## 🔐 Accesso alla Rassegna Stampa")
    username = st.text_input("👤 Nome utente", key="username_input")
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

def main():
    if not st.session_state.logged_in:
        login()
    else:
        user = st.session_state.username
        service = get_drive_service()
        try:
            users = read_users_file(service)
        except:
            users = {}

        with st.sidebar:
            st.image("logo.png", width=120)
            st.write("----")
            st.success(f"👤 {user}")
            st.write("---")
            page = st.radio("📋 Seleziona una pagina", ["Archivio", "Statistiche"])
            st.write("---")
            if st.button("🚪 Esci"):
                st.session_state.clear()
                st.rerun()

            if user == "Admin":
                if not users:
                    st.info("📂 Nessun file utenti.csv trovato. Puoi crearne uno ora.")
                    if st.button("🆕 Crea file utenti.csv di default"):
                        users = {
                            "Admin": {
                                "password": "CorsoDuca15",
                                "password_cambiata": "no",
                                "data_modifica": "2025-05-16"
                            }
                        }
                        write_users_file(service, users)
                        st.success("✅ File utenti.csv creato con successo.")
                        st.rerun()

                with st.expander("👥 Gestione utenti"):
                    st.subheader("➕ Aggiungi o aggiorna utente")
                    nuovo_user = st.text_input("👤 Username")
                    nuova_pw = st.text_input("🔑 Password", type="password")
                    if st.button("📏 Salva utente"):
                        if not nuovo_user or not nuova_pw:
                            st.warning("⚠️ Inserire sia username che password.")
                        else:
                            update_user_password(service, users, nuovo_user, nuova_pw)
                            st.success(f"Utente '{nuovo_user}' aggiunto o aggiornato.")
                            st.rerun()

                    st.subheader("🛑 Elimina utente")
                    utenti_eliminabili = sorted([u for u in users if u != "Admin"])
                    if utenti_eliminabili:
                        user_to_delete = st.selectbox("Seleziona utente da rimuovere", utenti_eliminabili)
                        if st.button("❌ Elimina selezionato"):
                            delete_user(service, users, user_to_delete)
                            st.warning(f"Utente '{user_to_delete}' rimosso.")
                            st.rerun()
                    else:
                        st.info("ℹ️ Nessun altro utente da eliminare.")

                    st.subheader("📋 Elenco utenti attivi")
                    if users:
                        df_utenti = pd.DataFrame.from_dict(users, orient="index")
                        df_utenti.index.name = "Username"
                        df_utenti = df_utenti.reset_index()
                        st.dataframe(df_utenti)
                    else:
                        st.info("🔍 Nessun utente registrato.")
            else:
                with st.expander("🔑 Cambia password"):
                    old = st.text_input("Vecchia password", type="password", key="old")
                    new = st.text_input("Nuova password", type="password", key="new")
                    conf = st.text_input("Conferma nuova password", type="password", key="conf")
                    if st.button("Salva nuova password"):
                        if old != users[user]["password"]:
                            st.error("❌ Vecchia password errata.")
                        elif new != conf:
                            st.warning("⚠️ Le nuove password non coincidono.")
                        else:
                            update_user_password(service, users, user, new)
                            st.success("✅ Password aggiornata.")
                            st.rerun()

        if page == "Archivio":
            dashboard()
        elif page == "Statistiche":
            if user == "Admin":
                mostra_statistiche()
            else:
                st.warning("⚠️ Accesso riservato. Le statistiche sono visibili solo all'amministratore.")

def dashboard():
    st.markdown("### 📂 Area Archivio")
    st.info("Questa sezione mostrerà l'elenco dei PDF caricati su Google Drive.")

def mostra_statistiche():
    st.markdown("### 📊 Area Statistiche")
    st.info("Questa sezione mostrerà le statistiche degli accessi e dei caricamenti.")

main()

