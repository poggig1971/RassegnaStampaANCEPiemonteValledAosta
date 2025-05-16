import streamlit as st
import os
from datetime import datetime
import pytz
import pandas as pd
from io import StringIO, BytesIO
from PIL import Image

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

# === CONFIGURAZIONE INIZIALE ===
favicon = Image.open("favicon_ance.png")
st.set_page_config(
    page_title="Rassegna ANCE Piemonte",
    page_icon=favicon,
    layout="centered"
)

st.markdown(
    """
    <head>
        <link rel="apple-touch-icon" sizes="180x180" href="https://raw.githubusercontent.com/poggig1971/RassegnaStampaANCEPiemonteValledAosta/main/public/app-icon.png">
        <meta name="apple-mobile-web-app-capable" content="yes">
    </head>
    """,
    unsafe_allow_html=True
)


def init_session_state():
    defaults = {
        "logged_in": False,
        "username": "",
        "logged_files": set(),
        "user_data": {}
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_service():
    # Restituisce un'istanza singleton del servizio Google Drive
    if "service" not in st.session_state:
        st.session_state.service = get_drive_service()
    return st.session_state.service


def render_logo(width: int = 200):
    st.image("logo.png", width=width)


def handle_admin_emergency(username: str, password: str) -> bool:
    if username == "Admin" and password == "CorsoDuca15":
        st.session_state.logged_in = True
        st.session_state.username = username
        st.session_state.user_data = {}
        st.warning("⚠️ Accesso amministratore d’emergenza.")
        st.rerun()
        return True
    return False


def login(service):
    render_logo()
    st.markdown("## 🔐 Accesso alla Rassegna Stampa")
    username = st.text_input("👤 Nome utente", key="username_input")
    password = st.text_input("🔑 Password", type="password", key="password_input")
    if st.button("Accedi", key="login_button"):
        try:
            users = read_users_file(service)
            if username in users and users[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = users
                st.success("✅ Accesso effettuato")
                st.rerun()
            else:
                if not users and handle_admin_emergency(username, password):
                    return
                st.error("❌ Credenziali non valide. Riprova.")
        except Exception:
            if handle_admin_emergency(username, password):
                return
            st.error("❌ Errore durante il login.")


def render_sidebar(service) -> str:
    user = st.session_state.username
    try:
        users = read_users_file(service)
    except:
        users = {}

    with st.sidebar:
        render_logo(width=180)
        st.write("----")
        st.success(f"👤 {user}")
        st.write("---")
        page = st.radio(
            "📋 Seleziona una pagina",
            ["Archivio", "Statistiche", "Profilo"],
            key="sidebar_page"
        )
        st.write("---")

        if user == "Admin":
            st.markdown("### ⚙️ Gestione utenti")

            # Creazione file utenti di default
            if not users:
                st.info("📂 Nessun file utenti.csv trovato. Puoi crearne uno ora.")
                if st.button("🆕 Crea file utenti.csv di default", key="create_default_users"):
                    users = {
                        "Admin": {"password": "CorsoDuca15", "password_cambiata": "no", "data_modifica": "2025-05-16"}
                    }
                    write_users_file(service, users)
                    st.success("✅ File utenti.csv creato con successo.")
                    st.rerun()

            # Aggiungi/aggiorna utente
            st.subheader("➕ Aggiungi o aggiorna utente")
            nuovo_user = st.text_input("👤 Username", key="new_user")
            nuova_pw = st.text_input("🔑 Password", type="password", key="new_pw")
            if st.button("📏 Salva utente", key="save_user"):
                if not nuovo_user or not nuova_pw:
                    st.warning("⚠️ Inserire sia username che password.")
                else:
                    update_user_password(service, users, nuovo_user, nuova_pw)
                    st.success(f"Utente '{nuovo_user}' aggiunto o aggiornato.")
                    st.rerun()

            # Elimina utente
            st.subheader("🛑 Elimina utente")
            eliminabili = sorted([u for u in users if u != "Admin"])
            if eliminabili:
                user_to_delete = st.selectbox(
                    "👤 Seleziona utente da rimuovere",
                    eliminabili,
                    key="delete_user_select"
                )
                if st.button("❌ Elimina selezionato", key="delete_user"):
                    delete_user(service, users, user_to_delete)
                    st.warning(f"Utente '{user_to_delete}' rimosso.")
                    st.rerun()
            else:
                st.info("ℹ️ Nessun altro utente da eliminare.")

            # Elenco utenti attivi
            st.subheader("📋 Elenco utenti attivi")
            if users:
                df_utenti = pd.DataFrame.from_dict(users, orient="index").reset_index()
                df_utenti.columns = ["Username"] + list(df_utenti.columns[1:])
                st.dataframe(df_utenti)
            else:
                st.info("🔍 Nessun utente registrato.")

            # Carica nuovo file utenti.csv
            st.markdown("### 🔁 Carica nuovo file utenti.csv")
            uploaded = st.file_uploader(
                "Scegli file utenti.csv",
                type="csv",
                key="upload_users"
            )
            if uploaded:
                upload_pdf_to_drive(service, uploaded, "utenti.csv", is_memory_file=True, overwrite=True)
                st.success("✅ utenti.csv aggiornato.")
                st.rerun()

        if st.button("🚪 Esci", key="logout"):
            st.session_state.clear()
            st.rerun()

    return page


def dashboard(service):
    render_logo()
    st.markdown(f"### 👋 Benvenuto {st.session_state.username}!")
    st.markdown("## 📂 Archivio Rassegne")
    try:
        files = list_pdfs_in_folder(service)
        if not files:
            st.info("📭 Nessun PDF trovato nella cartella di Drive.")
            return

        file_names = sorted([f['name'] for f in files], reverse=True)
        today_file = datetime.now(pytz.timezone("Europe/Rome")).strftime("%Y.%m.%d.pdf")
        if today_file in file_names:
            st.success("✅ La rassegna di oggi è stata caricata.")
        else:
            st.warning("📭 La rassegna di oggi non è ancora stata caricata.")

        # Seleziona per visualizzare
        selected = st.selectbox(
            "🗂️ Seleziona un file da visualizzare",
            file_names,
            key="archive_select_view"
        )
        file_id = next((f['id'] for f in files if f['name'] == selected), None)
        if file_id:
            content = download_pdf(service, file_id, return_bytes=True)
            st.download_button(
                "⬇️ Scarica il PDF",
                data=BytesIO(content),
                file_name=selected,
                key="download_pdf_button"
            )

        # Admin: upload e delete
        if st.session_state.username == "Admin":
            st.markdown("### 📤 Carica nuova rassegna")
            uploaded = st.file_uploader(
                "Seleziona uno o più PDF",
                type="pdf",
                accept_multiple_files=True,
                key="upload_rassegne"
            )
            if uploaded:
                for f in uploaded:
                    upload_pdf_to_drive(service, f, f.name, is_memory_file=True)
                    st.success(f"✅ Caricato: {f.name}")
                st.rerun()

            st.markdown("### 🗑️ Elimina file")
            to_delete = st.selectbox(
                "🗂️ Seleziona file da eliminare",
                file_names,
                key="archive_select_delete"
            )
            if st.button("Elimina selezionato", key="archive_delete_button"):
                del_id = next((f['id'] for f in files if f['name'] == to_delete), None)
                if del_id:
                    service.files().delete(fileId=del_id).execute()
                    st.success(f"✅ File '{to_delete}' eliminato.")
                    st.rerun()
    except Exception as e:
        st.error(f"Errore durante il caricamento dei file: {e}")


def mostra_statistiche(service):
    st.markdown("### 📊 Area Statistiche")
    try:
        files = service.files().list(q="trashed = false", fields="files(id,name)").execute().get("files", [])
        log_id = next((f['id'] for f in files if f['name'] == "log_visualizzazioni.csv"), None)
        if not log_id:
            st.info("📭 Nessun log disponibile.")
            return

        content = download_pdf(service, log_id, return_bytes=True).decode('utf-8')
        df = pd.read_csv(StringIO(content))

        st.metric("Totale visualizzazioni", len(df))

        st.markdown("### 👥 Utenti più attivi")
        st.bar_chart(df['utente'].value_counts().head(5))

        st.markdown("### 📁 File più visualizzati")
        st.bar_chart(df['file'].value_counts().head(5))

        df['data'] = pd.to_datetime(df['data'])
        recent = df[df['data'] >= datetime.now() - pd.Timedelta(days=30)]
        if not recent.empty:
            st.markdown("### 📅 Accessi ultimi 30 giorni")
            st.line_chart(recent.groupby('data').size())

    except Exception as e:
        st.error(f"❌ Errore nel caricamento statistiche: {e}")


def main():
    init_session_state()
    service = get_service()

    if not st.session_state.logged_in:
        login(service)
        return

    page = render_sidebar(service)

    if page == "Archivio":
        dashboard(service)
    elif page == "Statistiche":
        if st.session_state.username == "Admin":
            mostra_statistiche(service)
        else:
            st.warning("⚠️ Accesso riservato. Le statistiche sono visibili solo all'amministratore.")
    elif page == "Profilo":
        with st.expander("🔑 Cambia password"):
            old_pw = st.text_input("Vecchia password", type="password", key="profile_old_pw")
            new_pw = st.text_input("Nuova password", type="password", key="profile_new_pw")
            conf_pw = st.text_input("Conferma nuova password", type="password", key="profile_conf_pw")
            if st.button("Salva nuova password", key="profile_save_pw"):
                users = st.session_state.user_data
                current_pw = users.get(st.session_state.username, {}).get("password", "")
                if old_pw != current_pw:
                    st.error("❌ Vecchia password errata.")
                elif new_pw != conf_pw:
                    st.warning("⚠️ Le nuove password non coincidono.")
                else:
                    update_user_password(service, users, st.session_state.username, new_pw)
                    st.success("✅ Password aggiornata.")
                    st.rerun()


if __name__ == "__main__":
    main()


