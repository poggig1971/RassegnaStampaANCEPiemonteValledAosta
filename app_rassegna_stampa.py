
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
        user_data = read_users_file(service)
        if username in user_data and user_data[username]["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.user_data = user_data
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

# dashboard() e mostra_statistiche() restano invariati

def main():
    if not st.session_state.logged_in:
        login()
    else:
        user = st.session_state.username
        service = get_drive_service()
        users = read_users_file(service)

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
                with st.expander("👥 Gestione utenti"):
                    st.subheader("➕ Aggiungi o aggiorna utente")
                    nuovo_user = st.text_input("👤 Username")
                    nuova_pw = st.text_input("🔑 Password", type="password")
                    if st.button("💾 Salva utente"):
                        update_user_password(service, users, nuovo_user, nuova_pw)
                        st.success(f"Utente '{nuovo_user}' aggiunto o aggiornato.")
                        st.rerun()

                    st.subheader("🗑️ Elimina utente")
                    user_to_delete = st.selectbox("Seleziona utente da rimuovere", [u for u in users if u != "Admin"])
                    if st.button("❌ Elimina selezionato"):
                        delete_user(service, users, user_to_delete)
                        st.warning(f"Utente '{user_to_delete}' rimosso.")
                        st.rerun()

                    st.subheader("📋 Elenco utenti attivi")
                    for u, info in users.items():
                        st.markdown(f"👤 **{u}** — 🔄 {info['data_modifica']}")

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

main()
