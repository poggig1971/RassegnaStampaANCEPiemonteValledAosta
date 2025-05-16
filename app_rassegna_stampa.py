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

main()
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
        results = service.files().list(q="trashed = false", fields="files(id, name)").execute()
        files = results.get("files", [])
    except Exception as e:
        st.error("⚠️ Errore nella connessione a Google Drive.")
        return

    oggi = datetime.now(pytz.timezone("Europe/Rome")).strftime("%Y.%m.%d")
    if any(f["name"] == f"{oggi}.pdf" for f in files):
        st.success("✅ La rassegna di oggi è disponibile.")
    else:
        st.warning("📭 La rassegna di oggi non è ancora caricata.")

    if files:
        date_strings = [
            f["name"].replace(".pdf", "")
            for f in files
            if f["name"].lower().endswith(".pdf")
        ]
        if date_strings:
            most_recent = max(date_strings)
            st.caption(f"🕒 Ultimo file disponibile: {most_recent}")

    if st.button("🔄 Aggiorna elenco PDF"):
        st.rerun()

    if st.session_state.username == "Admin":
        st.markdown("### 📄 Carica nuova rassegna stampa")
        uploaded_files = st.file_uploader("Seleziona uno o più file PDF", type="pdf", accept_multiple_files=True)
        if uploaded_files:
            existing_filenames = [f["name"] for f in files]
            for uploaded_file in uploaded_files:
                filename = uploaded_file.name
                if filename in existing_filenames:
                    st.warning(f"❗ Il file '{filename}' è già presente su Drive.")
                    continue
                file_bytes = BytesIO(uploaded_file.getbuffer())
                upload_pdf_to_drive(service, file_bytes, filename, is_memory_file=True)
                append_log_entry(service, st.session_state.username, filename)
                st.success(f"✅ Caricato: {filename}")
            st.rerun()

        st.markdown("### 🗑️ Elimina file da Drive")
        deletable_files = [f for f in files if f["name"].lower().endswith(".pdf")]
        file_to_delete = st.selectbox("Seleziona un file da eliminare", [f["name"] for f in deletable_files])
        if st.button("Elimina file selezionato"):
            file_id = next((f["id"] for f in deletable_files if f["name"] == file_to_delete), None)
            if file_id:
                service.files().delete(fileId=file_id).execute()
                st.success(f"✅ File '{file_to_delete}' eliminato da Google Drive.")
                st.rerun()

    date_options = sorted(
        list({f["name"].replace(".pdf", "") for f in files if f["name"].lower().endswith(".pdf")}),
        reverse=True
    )
    if date_options:
        selected_date = st.selectbox("🗓️ Seleziona una data", date_options)
        selected_file = f"{selected_date}.pdf"
        file_id = next((f["id"] for f in files if f["name"] == selected_file), None)
        if file_id:
            content = download_pdf(service, file_id, return_bytes=True)
            st.download_button(f"⬇️ Scarica rassegna {selected_date}", data=BytesIO(content), file_name=selected_file)

def mostra_statistiche():
    st.markdown("## 📈 Statistiche di accesso")
    try:
        service = get_drive_service()
        results = service.files().list(q="trashed = false", fields="files(id, name)").execute()
        files = results.get("files", [])
        file_id = next((f["id"] for f in files if f["name"] == "log_visualizzazioni.csv"), None)

        if not file_id:
            st.info("📬 Nessun dato ancora disponibile.")
            return

        content = download_pdf(service, file_id, return_bytes=True).decode("utf-8")
        df = pd.read_csv(StringIO(content))

        if st.session_state.username == "Admin":
            st.download_button(
                label="⬇️ Scarica log visualizzazioni (CSV)",
                data=content,
                file_name="log_visualizzazioni.csv",
                mime="text/csv"
            )

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
            st.info("📬 Nessun accesso negli ultimi 30 giorni.")
        else:
            st.markdown("### 🗖️ Accessi negli ultimi 30 giorni")
            daily = ultimi_30.groupby('data').size()
            st.line_chart(daily)

    except Exception as e:
        st.error(f"❌ Errore durante il recupero delle statistiche: {e}")

