import streamlit as st
import os
from datetime import datetime, date
import pytz
import pandas as pd
from io import StringIO, BytesIO
from PIL import Image
import bcrypt # Importa la libreria bcrypt

# === CONFIGURAZIONE INIZIALE ===
# Assicurati che 'favicon_ance.png' sia nella stessa directory dell'app
try:
    favicon = Image.open("favicon_ance.png")
except FileNotFoundError:
    st.error("Errore: favicon_ance.png non trovato. Assicurati che sia nella stessa directory dell'app.")
    favicon = None # Gestisce il caso in cui l'icona non sia trovata

st.set_page_config(
    page_title="Rassegna ANCE Piemonte",
    page_icon=favicon, # Sarà None se il favicon non è stato trovato
    layout="centered"
)

# Aggiunto CSS per nascondere la barra di navigazione laterale di Streamlit se non in uso
# e per migliorare l'aspetto dell'app mobile.
st.markdown("""
    <style>
        .reportview-container .main .block-container{
            padding-top: 2rem;
            padding-right: 1rem;
            padding-left: 1rem;
            padding-bottom: 2rem;
        }
        .sidebar .sidebar-content {
            padding-top: 2rem;
            padding-right: 1rem;
            padding-left: 1rem;
            padding-bottom: 2rem;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    <head>
        <link rel="apple-touch-icon" sizes="180x180" href="https://raw.githubusercontent.com/poggig1971/RassegnaStampaANCEPiemonteValledAosta/main/public/app-icon.png">
        <meta name="apple-mobile-web-app-capable" content="yes">
    </head>
""", unsafe_allow_html=True)

# Importa le utility di Google Drive
# NOTA: Queste funzioni DEVONO essere aggiornate per gestire le password hashate
# in particolare `read_users_file` e `update_user_password`.
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

# --- FUNZIONI DI UTILITY PER L'HASHING DELLE PASSWORD ---
# Queste funzioni dovrebbero idealmente risiedere in drive_utils.py
# o in un file di utility separato per la gestione delle password.
def hash_password(password):
    """Hashes una password usando bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(plain_password, hashed_password):
    """Verifica una password in chiaro contro un hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# === INIZIALIZZAZIONE DELLO STATO DELLA SESSIONE ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if "logged_files" not in st.session_state: # Questa variabile sembra non essere usata. Potrebbe essere rimossa.
    st.session_state.logged_files = set()
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

# === FUNZIONE DI LOGIN ===
def login():
    # Assicurati che 'logo.png' sia nella stessa directory dell'app
    try:
        st.image("logo.png", width=200)
    except FileNotFoundError:
        st.warning("Attenzione: logo.png non trovato.")

    st.markdown("## 🔐 Accesso alla Rassegna Stampa")
    username = st.text_input("👤 Nome utente", key="username_input")
    password = st.text_input("🔑 Password", type="password", key="password_input")

    if st.button("Accedi"):
        try:
            service = get_drive_service()
            user_data = read_users_file(service) # user_data dovrebbe contenere gli hash delle password

            # Controllo credenziali standard
            if username in user_data and check_password(password, user_data[username]["password"]):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = user_data
                st.success("✅ Accesso effettuato con successo!")
                st.rerun()
            # Controllo credenziali Admin d'emergenza (solo se il file utenti è vuoto/inesistente)
            elif (not user_data or user_data == {"Admin": {"password": hash_password("CorsoDuca15"), "password_cambiata": "no", "data_modifica": "2025-05-16"}} ) \
                 and username == "Admin" and password == "CorsoDuca15":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = user_data # In questo caso, sarà vuoto o solo con l'Admin di default
                st.warning("⚠️ File utenti.csv assente/vuoto o default. Accesso amministratore d’emergenza.")
                st.rerun()
            else:
                st.error("❌ Credenziali non valide. Riprova.")
        except Exception as e:
            # Gestione errori di connessione o lettura file utenti.csv
            if username == "Admin" and password == "CorsoDuca15":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = {} # Nessun dato utente letto in caso di errore
                st.warning("⚠️ Errore nella lettura del file utenti. Accesso amministratore d’emergenza abilitato.")
                st.rerun()
            else:
                st.error(f"❌ Errore durante il login. Controlla la connessione o le credenziali. Dettaglio: {e}")

# === FUNZIONE PRINCIPALE DELL'APP ===
def main():
    if not st.session_state.logged_in:
        login()
    else:
        user = st.session_state.username
        service = get_drive_service()
        users = {} # Inizializza users per evitare ReferenceBeforeAssignment
        try:
            users = read_users_file(service)
        except Exception as e:
            st.error(f"❌ Impossibile leggere il file utenti.csv da Google Drive. Dettaglio: {e}")
            # Se la lettura fallisce, e l'admin è loggato, potrebbe comunque procedere con un dizionario utenti vuoto
            # per permettere la creazione del file.
            if user != "Admin": # Se non è l'admin e c'è un errore, forza il logout per sicurezza
                st.session_state.clear()
                st.rerun()

        with st.sidebar:
            try:
                st.image("logo.png", width=180)
            except FileNotFoundError:
                st.warning("Attenzione: logo.png non trovato nella sidebar.")

            st.write("----")
            st.success(f"👤 **{user}**")
            st.write("---")

            # Navigazione principale
            page = st.radio("📋 Seleziona una pagina", ["Archivio", "Statistiche", "Profilo"])
            st.write("---")

            # Sezione Admin (solo per Admin)
            if user == "Admin":
                st.markdown("### ⚙️ Gestione Admin")
                if not users:
                    st.info("📂 Nessun file utenti.csv trovato su Drive. Puoi crearne uno predefinito.")
                    if st.button("🆕 Crea utenti.csv di default"):
                        # La password di default viene hashata al momento della creazione
                        default_admin_password_hashed = hash_password("CorsoDuca15")
                        users = {
                            "Admin": {
                                "password": default_admin_password_hashed,
                                "password_cambiata": "no",
                                "data_modifica": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                        }
                        write_users_file(service, users)
                        st.success("✅ File utenti.csv creato con utente 'Admin' predefinito.")
                        st.rerun()
                st.subheader("➕ Aggiungi/Aggiorna utente")
                with st.form("add_update_user_form"):
                    nuovo_user = st.text_input("👤 Username", key="new_user_input")
                    nuova_pw = st.text_input("🔑 Password", type="password", key="new_pw_input")
                    submitted = st.form_submit_button("📏 Salva utente")
                    if submitted:
                        if not nuovo_user or not nuova_pw:
                            st.warning("⚠️ Inserire sia username che password.")
                        else:
                            # update_user_password deve hashare la nuova_pw prima di salvare
                            update_user_password(service, users, nuovo_user, hash_password(nuova_pw))
                            st.success(f"Utente '{nuovo_user}' aggiunto o aggiornato.")
                            st.rerun()

                st.subheader("🛑 Elimina utente")
                utenti_eliminabili = sorted([u for u in users if u != "Admin"])
                if utenti_eliminabili:
                    user_to_delete = st.selectbox("Seleziona utente da rimuovere", utenti_eliminabili, key="delete_user_select")
                    if st.button("❌ Elimina selezionato", key="delete_user_button"):
                        # Potresti aggiungere una conferma qui prima di eliminare
                        delete_user(service, users, user_to_delete)
                        st.warning(f"Utente '{user_to_delete}' rimosso.")
                        st.rerun()
                else:
                    st.info("ℹ️ Nessun altro utente da eliminare.")

                st.subheader("📋 Elenco utenti attivi")
                if users:
                    # Rimuovi la password dal dataframe per visualizzazione (o mostra solo un asterisco)
                    df_utenti_display = pd.DataFrame.from_dict(users, orient="index")
                    if 'password' in df_utenti_display.columns:
                        df_utenti_display['password'] = '********' # Nasconde la password per la visualizzazione
                    df_utenti_display.index.name = "Username"
                    df_utenti_display = df_utenti_display.reset_index()
                    st.dataframe(df_utenti_display, hide_index=True)
                else:
                    st.info("🔍 Nessun utente registrato.")

                st.markdown("### 🔁 Carica nuovo file utenti.csv")
                uploaded_users_file = st.file_uploader("Scegli file utenti.csv", type="csv", key="upload_users_csv")
                if uploaded_users_file:
                    # Potresti voler validare il contenuto del CSV qui prima di caricarlo
                    # E assicurarti che le password nel CSV siano già hashate o vengano hashate al caricamento
                    upload_pdf_to_drive(service, uploaded_users_file, "utenti.csv", is_memory_file=True, overwrite=True)
                    st.success("✅ utenti.csv aggiornato su Google Drive.")
                    st.rerun()
            st.write("---") # Separatore dopo la sezione Admin

            if st.button("🚪 Esci", key="logout_button_sidebar"):
                st.session_state.clear()
                st.rerun()

        # Renderizza la pagina selezionata
        if page == "Archivio":
            dashboard()
        elif page == "Statistiche":
            if user == "Admin":
                mostra_statistiche()
            else:
                st.warning("⚠️ Accesso riservato. Le statistiche sono visibili solo all'amministratore.")
        elif page == "Profilo":
            show_profile_page(user, users, service) # Chiamata a funzione dedicata per la pagina Profilo

# === FUNZIONE DASHBOARD (ARCHIVIO) ===
def dashboard():
    try:
        st.image("logo.png", width=200) # Immagine nella dashboard
    except FileNotFoundError:
        st.warning("Attenzione: logo.png non trovato.")

    st.markdown(f"### 👋 Benvenuto **{st.session_state.username}**!")
    st.markdown("## 📂 Archivio Rassegne")
    try:
        service = get_drive_service()
        files = list_pdfs_in_folder(service)
        if not files:
            st.info("📭 Nessun PDF trovato nella cartella di Drive.")
            # Rimuovi l'upload/delete se non ci sono file da gestire
            if st.session_state.username == "Admin":
                st.markdown("### 📤 Carica nuova rassegna")
                uploaded_files = st.file_uploader("Seleziona uno o più PDF", type="pdf", accept_multiple_files=True, key="upload_pdf_empty")
                if uploaded_files:
                    for uploaded_file in uploaded_files:
                        upload_pdf_to_drive(service, uploaded_file, uploaded_file.name, is_memory_file=True)
                        st.success(f"✅ Caricato: {uploaded_file.name}")
                    st.rerun()
            return

        file_names = sorted([file["name"] for file in files], reverse=True)
        # Ottieni la data e ora attuali nel fuso orario di Roma
        roma_tz = pytz.timezone("Europe/Rome")
        oggi = datetime.now(roma_tz).strftime("%Y.%m.%d.pdf")

        if oggi in file_names:
            st.success("✅ La rassegna di oggi è stata caricata.")
        else:
            st.warning("📭 La rassegna di oggi non è ancora stata caricata.")

        # SELECTBOX per visualizzazione
        selected_file = st.selectbox("🗂️ Seleziona un file da visualizzare", file_names, key="selectbox_visualizza_dashboard")
        file_id = next((file["id"] for file in files if file["name"] == selected_file), None)

        if file_id:
            try:
                content = download_pdf(service, file_id, return_bytes=True)
                st.download_button("⬇️ Scarica il PDF", data=BytesIO(content), file_name=selected_file, key="download_pdf_button")
                # Qui potresti aggiungere la logica per loggare la visualizzazione del file
                # append_log_entry(service, st.session_state.username, selected_file)
            except Exception as e:
                st.error(f"❌ Errore durante il download del PDF: {e}")

        # Se Admin, abilita caricamento e cancellazione
        if st.session_state.username == "Admin":
            st.markdown("---") # Separatore per le azioni Admin
            st.markdown("### 📤 Carica nuova rassegna")
            uploaded_files = st.file_uploader("Seleziona uno o più PDF", type="pdf", accept_multiple_files=True, key="upload_pdf_admin")
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    # Assicurati che upload_pdf_to_drive possa gestire correttamente BytesIO
                    upload_pdf_to_drive(service, uploaded_file, uploaded_file.name, is_memory_file=True)
                    st.success(f"✅ Caricato: {uploaded_file.name}")
                st.rerun()

            st.markdown("### 🗑️ Elimina file")
            # Assicurati che l'opzione di eliminazione sia diversa da quella di visualizzazione per chiarezza
            file_to_delete = st.selectbox("Seleziona il PDF da eliminare", file_names, key="selectbox_elimina_dashboard")
            if st.button("❌ Elimina file selezionato", key="delete_file_button"):
                file_id_to_delete = next((file["id"] for file in files if file["name"] == file_to_delete), None)
                if file_id_to_delete:
                    try:
                        service.files().delete(fileId=file_id_to_delete).execute()
                        st.success(f"✅ File '{file_to_delete}' eliminato con successo.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Errore durante l'eliminazione del file: {e}")
                else:
                    st.error("Errore: ID del file non trovato per l'eliminazione.")
    except Exception as e:
        st.error(f"❌ Errore generale nell'area Archivio: {e}")

# === FUNZIONE PAGINA PROFILO (CAMBIO PASSWORD) ===
def show_profile_page(user, users_data, drive_service):
    st.markdown("## 👤 Il tuo Profilo")
    st.markdown("### 🔑 Cambia password")
    with st.form("change_password_form"):
        old_password = st.text_input("Vecchia password", type="password", key="old_pw")
        new_password = st.text_input("Nuova password", type="password", key="new_pw")
        confirm_new_password = st.text_input("Conferma nuova password", type="password", key="conf_pw")
        password_change_submitted = st.form_submit_button("Salva nuova password")

        if password_change_submitted:
            if user not in users_data:
                st.error("Errore: Utente non trovato nel database.")
                st.rerun()

            # Usa check_password per confrontare la vecchia password
            if not check_password(old_password, users_data[user]["password"]):
                st.error("❌ Vecchia password errata.")
            elif new_password != confirm_new_password:
                st.warning("⚠️ Le nuove password non coincidono.")
            else:
                # Hash della nuova password prima di passarla a update_user_password
                hashed_new_password = hash_password(new_password)
                update_user_password(drive_service, users_data, user, hashed_new_password)
                st.success("✅ Password aggiornata con successo!")
                st.rerun()

# === FUNZIONE STATISTICHE ===
def mostra_statistiche():
    st.markdown("### 📊 Area Statistiche")
    try:
        service = get_drive_service()
        # Cerca solo il file di log_visualizzazioni.csv
        file_list = service.files().list(q="name='log_visualizzazioni.csv' and trashed = false",
                                         fields="files(id, name)").execute().get("files", [])
        file_id = file_list[0]["id"] if file_list else None

        if not file_id:
            st.info("📭 Nessun log di visualizzazioni disponibile (log_visualizzazioni.csv non trovato).")
            return

        # Scarica e decodifica il contenuto del log
        content = download_pdf(service, file_id, return_bytes=True).decode("utf-8")
        df = pd.read_csv(StringIO(content))

        st.metric("Totale visualizzazioni", len(df))

        # Assicurati che 'utente' e 'file' siano colonne valide
        if 'utente' in df.columns:
            top_utenti = df['utente'].value_counts().head(5)
            st.markdown("### 👥 Utenti più attivi")
            st.bar_chart(top_utenti)
        else:
            st.info("Colonna 'utente' non trovata nel log.")

        if 'file' in df.columns:
            top_file = df['file'].value_counts().head(5)
            st.markdown("### 📁 File più visualizzati")
            st.bar_chart(top_file)
        else:
            st.info("Colonna 'file' non trovata nel log.")

        if 'data' in df.columns:
            df['data'] = pd.to_datetime(df['data'])
            # Filtra per gli ultimi 30 giorni basandosi sul timestamp attuale
            ultimi_30 = df[df['data'] >= datetime.now(pytz.utc) - pd.Timedelta(days=30)] # Confronta con UTC per sicurezza
            if not ultimi_30.empty:
                st.markdown("### 📅 Accessi ultimi 30 giorni")
                # Group by data per evitare problemi con l'ora esatta
                accessi_giornalieri = ultimi_30.groupby(ultimi_30['data'].dt.date).size()
                st.line_chart(accessi_giornalieri)
            else:
                st.info("Nessun accesso registrato negli ultimi 30 giorni.")
        else:
            st.info("Colonna 'data' non trovata nel log.")

    except pd.errors.EmptyDataError:
        st.info("Il file log_visualizzazioni.csv è vuoto.")
    except Exception as e:
        st.error(f"❌ Errore durante il caricamento o l'analisi delle statistiche: {e}")

# === ESECUZIONE DELL'APP ===
if __name__ == "__main__":
    main()
