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
    st.image("logo.png", width=200)
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
                st.stop()
            elif not user_data and username == "Admin" and password == "CorsoDuca15":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = {}
                st.warning("⚠️ File utenti.csv assente o vuoto. Accesso amministratore d’emergenza.")
                st.rerun()
                st.stop()
            else:
                st.error("❌ Credenziali non valide. Riprova.")
        except Exception:
            if username == "Admin" and password == "CorsoDuca15":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = {}
                st.warning("⚠️ Errore nella lettura del file utenti. Accesso amministratore d’emergenza.")
                st.rerun()
                st.stop()
            else:
                st.error("❌ Errore durante il login.")

def dashboard():
    st.image("logo.png", width=200)
    st.markdown(f"### 👋 Benvenuto {st.session_state.username}!")
    st.markdown("## 📂 Archivio Rassegne")
    try:
        service = get_drive_service()
        files = list_pdfs_in_folder(service)
        if not files:
            st.info("📍 Nessun PDF trovato nella cartella di Drive.")
            return

        file_names = sorted([file["name"] for file in files], reverse=True)
        oggi = datetime.now(pytz.timezone("Europe/Rome")).strftime("%Y.%m.%d.pdf")
        if oggi in file_names:
            st.success("✅ La rassegna di oggi è stata caricata.")
        else:
            st.warning("📍 La rassegna di oggi non è ancora stata caricata.")

        selected_file = st.selectbox(
            "📂 Seleziona un file da visualizzare",
            file_names,
            key=f"selectbox_visualizza_{st.session_state.username}"
        )
        file_id = next((file["id"] for file in files if file["name"] == selected_file), None)
        if file_id:
            content = download_pdf(service, file_id, return_bytes=True)
            st.download_button("📂 Scarica il PDF", data=BytesIO(content), file_name=selected_file)

        if st.session_state.username == "Admin":
            st.markdown("### 📄 Carica nuova rassegna")
            uploaded_files = st.file_uploader("Seleziona uno o più PDF", type="pdf", accept_multiple_files=True)
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    upload_pdf_to_drive(service, uploaded_file, uploaded_file.name, is_memory_file=True)
                    st.success(f"✅ Caricato: {uploaded_file.name}")
                st.rerun()
                st.stop()

            st.markdown("### 🔎 Elimina file")
            file_to_delete = st.selectbox(
                "Seleziona file da eliminare",
                file_names,
                key=f"selectbox_elimina_{st.session_state.username}"
            )
            if st.button("Elimina selezionato"):
                file_id = next((file["id"] for file in files if file["name"] == file_to_delete), None)
                if file_id:
                    service.files().delete(fileId=file_id).execute()
                    st.success(f"✅ File '{file_to_delete}' eliminato.")
                    st.rerun()
                    st.stop()
    except Exception as e:
        st.error(f"Errore durante il caricamento dei file: {e}")

def mostra_statistiche():
    st.markdown("### 📊 Area Statistiche")
    try:
        service = get_drive_service()
        files = service.files().list(q="trashed = false", fields="files(id, name)").execute().get("files", [])
        file_id = next((f["id"] for f in files if f["name"] == "log_visualizzazioni.csv"), None)
        if not file_id:
            st.info("📍 Nessun log disponibile.")
            return

        content = download_pdf(service, file_id, return_bytes=True).decode("utf-8")
        df = pd.read_csv(StringIO(content))

        st.metric("Totale visualizzazioni", len(df))

        top_utenti = df['utente'].value_counts().head(5)
        st.markdown("### 👥 Utenti più attivi")
        st.bar_chart(top_utenti)

        top_file = df['file'].value_counts().head(5)
        st.markdown("### 📁 File più visualizzati")
        st.bar_chart(top_file)

        df['data'] = pd.to_datetime(df['data'])
        ultimi_30 = df[df['data'] >= datetime.now() - pd.Timedelta(days=30)]
        if not ultimi_30.empty:
            st.markdown("### 📅 Accessi ultimi 30 giorni")
            st.line_chart(ultimi_30.groupby('data').size())

    except Exception as e:
        st.error(f"❌ Errore durante il caricamento delle statistiche: {e}")

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
            st.image("logo.png", width=180)
            st.write("----")
            st.success(f"👤 {user}")
            st.write("---")
            page = st.radio("📋 Seleziona una pagina", ["Archivio", "Statistiche", "Profilo"])
            st.write("---")
            if user == "Admin":
                st.markdown("### ⚙️ Gestione utenti")
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
                        st.stop()

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
                        st.stop()

                st.subheader("🚩 Elimina utente")
                utenti_eliminabili = sorted([u for u in users if u != "Admin"])
                if utenti_eliminabili:
                    user_to_delete = st.selectbox("Seleziona utente da rimuovere", utenti_eliminabili, key=f"delete_user_{user}")
                    if st.button("❌ Elimina selezionato"):
                        delete_user(service, users, user_to_delete)
                        st.warning(f"Utente '{user_to_delete}' rimosso.")
                        st.rerun()
                        st.stop()
                else:
                    st.info("ℹ️ Nessun altro utente da eliminare.")

                try:
                    files = service.files().list(q="trashed = false", fields="files(id, name)").execute().get("files", [])
                    file_id = next((f["id"] for f in files if f["name"] == "utenti.csv"), None)
                    if file_id:
                        content = download_pdf(service, file_id, return_bytes=True)
                        st.download_button("⬇️ Scarica utenti.csv", data=content, file_name="utenti.csv")
                except Exception as e:
                    st.error(f"Errore nel download del file utenti: {e}")



                
                st.subheader("📋 Elenco utenti attivi")
                if users:
                    df_utenti = pd.DataFrame.from_dict(users, orient="index")
                    df_utenti.index.name = "Username"
                    df_utenti = df_utenti.reset_index()
                    st.dataframe(df_utenti)
                else:
                    st.info("🔍 Nessun utente registrato.")

                st.markdown("### 🔀 Carica nuovo file utenti.csv")
                uploaded = st.file_uploader("Scegli file utenti.csv", type="csv")
                if uploaded:
                    upload_pdf_to_drive(service, uploaded, "utenti.csv", is_memory_file=True, overwrite=True)
                    st.success("✅ utenti.csv aggiornato.")
                    st.rerun()
                    st.stop()

            if st.button("🚪 Esci"):
                st.session_state.clear()
                st.rerun()
                st.stop()

        if page == "Archivio":
            dashboard()
        elif page == "Statistiche":
            if user == "Admin":
                try:
                    service = get_drive_service()
                    files = service.files().list(q="trashed = false", fields="files(id, name)").execute().get("files", [])
                    file_id = next((f["id"] for f in files if f["name"] == "log_visualizzazioni.csv"), None)
                    if file_id:
                        content = download_pdf(service, file_id, return_bytes=True)
                        st.download_button("⬇️ Scarica log CSV", data=content, file_name="log_visualizzazioni.csv")
                except Exception as e:
                    st.error(f"Errore nel download del CSV: {e}")

                mostra_statistiche()
            else:
                st.warning("⚠️ Accesso riservato. Le statistiche sono visibili solo all'amministratore.")
                
                
        elif page == "Profilo":
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
                        st.stop()

if __name__ == "__main__":
    main()



