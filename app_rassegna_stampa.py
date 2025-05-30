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
    update_user_info,  
    delete_user,
    write_users_file,
    log_visualizzazione  # ✅ AGGIUNGI QUESTA RIGA
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

    # Recupera lo username ricordato (se esiste)
    default_username = st.session_state.get("remembered_user", "")
    username = st.text_input("👤 Nome utente", value=default_username, key="username_input")
    password = st.text_input("🔑 Password", type="password", key="password_input")
    remember = st.checkbox("🔒 Ricordami su questo dispositivo")

    if st.button("Accedi"):
        service = get_drive_service()
        try:
            user_data = read_users_file(service)
            if username in user_data and user_data[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = user_data
                if remember:
                    st.session_state["remembered_user"] = username
                st.success("✅ Accesso effettuato")
                st.rerun()
                st.stop()
            elif not user_data and username == "Admin" and password == "CorsoDuca15":
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_data = {}
                if remember:
                    st.session_state["remembered_user"] = username
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
                if remember:
                    st.session_state["remembered_user"] = username
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
            log_visualizzazione(service, st.session_state.username, selected_file)

        
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

def mostra_statistiche_user():
    st.markdown("### 📊 Statistiche di utilizzo della Rassegna")
    try:
        service = get_drive_service()
        files = service.files().list(q="trashed = false", fields="files(id, name)").execute().get("files", [])
        file_id = next((f["id"] for f in files if f["name"] == "log_visualizzazioni.csv"), None)
        if not file_id:
            st.info("📍 Nessun log disponibile.")
            return

        content = download_pdf(service, file_id, return_bytes=True).decode("utf-8")
        df = pd.read_csv(StringIO(content))
        df['data'] = pd.to_datetime(df['data'] + ' ' + df['ora'])

        st.metric("📥 Totale visualizzazioni", len(df))

        ultimi_30 = df[df['data'] >= datetime.now() - pd.Timedelta(days=30)]
        if not ultimi_30.empty:
            ultimi_30['solo_data'] = ultimi_30['data'].dt.date
            st.markdown("### 📅 Accessi giornalieri (ultimi 30 giorni)")
            st.line_chart(ultimi_30.groupby('solo_data').size())

        st.markdown("### 📁 File più letti")
        top_file = df['file'].value_counts().head(5)
        st.bar_chart(top_file)

        st.markdown("### 🕒 Quando viene consultata la rassegna")
        df['giorno_settimana'] = df['data'].dt.day_name()
        df['ora'] = df['data'].dt.hour

        def fascia_oraria(ora):
            if 6 <= ora < 12:
                return 'Mattino'
            elif 12 <= ora < 18:
                return 'Pomeriggio'
            elif 18 <= ora < 24:
                return 'Sera'
            else:
                return 'Notte'

        df['fascia'] = df['ora'].apply(fascia_oraria)
        heatmap_data = df.groupby(['giorno_settimana', 'fascia']).size().unstack(fill_value=0)
        giorni_ordine = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        fasce_ordine = ['Notte', 'Mattino', 'Pomeriggio', 'Sera']
        heatmap_data = heatmap_data.reindex(giorni_ordine).reindex(columns=fasce_ordine)

        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.imshow(heatmap_data.values, cmap="YlGnBu")

        ax.set_xticks(np.arange(len(heatmap_data.columns)))
        ax.set_yticks(np.arange(len(heatmap_data.index)))
        ax.set_xticklabels(heatmap_data.columns, fontsize=8)
        ax.set_yticklabels(heatmap_data.index, fontsize=8)

        for i in range(len(heatmap_data.index)):
            for j in range(len(heatmap_data.columns)):
                valore = heatmap_data.values[i, j]
                testo = int(valore) if not pd.isna(valore) else "-"
                ax.text(j, i, testo, ha="center", va="center", color="black")

        ax.set_title("Accessi per giorno e fascia oraria", fontsize=10)
        fig.tight_layout()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ Errore durante il caricamento delle statistiche: {e}")

def mostra_statistiche():
    st.markdown("### 📊 Statistiche dettagliate per Amministratore")
    try:
        service = get_drive_service()
        files = service.files().list(q="trashed = false", fields="files(id, name)").execute().get("files", [])
        file_id = next((f["id"] for f in files if f["name"] == "log_visualizzazioni.csv"), None)
        if not file_id:
            st.info("📍 Nessun log disponibile.")
            return

        content = download_pdf(service, file_id, return_bytes=True).decode("utf-8")
        df = pd.read_csv(StringIO(content))
        df['data_ora'] = pd.to_datetime(df['data'] + ' ' + df['ora'])
        df['data'] = pd.to_datetime(df['data'])

        utenti = df['utente'].unique().tolist()
        utente_selezionato = st.selectbox("👤 Seleziona un utente", utenti)

        df_u = df[df['utente'] == utente_selezionato]

        st.metric(f"📥 Totale accessi di {utente_selezionato}", len(df_u))

        # 📅 Accessi nel tempo
        st.markdown(f"### 📅 Accessi giornalieri di {utente_selezionato}")
        accessi_giornalieri = df_u.groupby(df_u['data'].dt.date).size()
        st.line_chart(accessi_giornalieri)

        # 📁 File consultati
        st.markdown(f"### 📁 File più consultati da {utente_selezionato}")
        file_counts = df_u['file'].value_counts().head(10)
        st.bar_chart(file_counts)

        # 📊 Heatmap oraria
        st.markdown(f"### ⏰ Heatmap accessi di {utente_selezionato}")
        df_u['giorno_settimana'] = df_u['data_ora'].dt.day_name()
        df_u['ora'] = df_u['data_ora'].dt.hour

        def fascia_oraria(ora):
            if 6 <= ora < 12:
                return 'Mattino'
            elif 12 <= ora < 18:
                return 'Pomeriggio'
            elif 18 <= ora < 24:
                return 'Sera'
            else:
                return 'Notte'

        df_u['fascia'] = df_u['ora'].apply(fascia_oraria)
        heatmap_data = df_u.groupby(['giorno_settimana', 'fascia']).size().unstack(fill_value=0)
        giorni_ordine = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        fasce_ordine = ['Notte', 'Mattino', 'Pomeriggio', 'Sera']
        heatmap_data = heatmap_data.reindex(giorni_ordine).reindex(columns=fasce_ordine)

        import matplotlib.pyplot as plt
        import numpy as np
        fig, ax = plt.subplots(figsize=(8, 5))
        im = ax.imshow(heatmap_data.values, cmap="OrRd")

        ax.set_xticks(np.arange(len(heatmap_data.columns)))
        ax.set_yticks(np.arange(len(heatmap_data.index)))
        ax.set_xticklabels(heatmap_data.columns, fontsize=8)
        ax.set_yticklabels(heatmap_data.index, fontsize=8)

        for i in range(len(heatmap_data.index)):
            for j in range(len(heatmap_data.columns)):
                valore = heatmap_data.values[i, j]
                testo = int(valore) if not pd.isna(valore) else "-"
                ax.text(j, i, testo, ha="center", va="center", color="black")

        ax.set_title("Accessi per giorno e fascia oraria", fontsize=10)
        fig.tight_layout()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ Errore durante il caricamento delle statistiche: {e}")


 # 📈 Grafico globale: cosa hanno letto e quando
        st.markdown("### 🌐 Attività di tutti gli utenti: file letti nel tempo")

        import plotly.express as px
        df_global = df.copy()
        df_global['data_ora'] = pd.to_datetime(df_global['data'] + ' ' + df_global['ora'])

        fig_global = px.scatter(
            df_global,
            x="data_ora",
            y="utente",
            color="file",
            hover_data=["file"],
            title="Attività utenti: letture dei file nel tempo",
            labels={"data_ora": "Data/Ora", "utente": "Utente", "file": "File"}
        )
        fig_global.update_traces(marker=dict(size=7), selector=dict(mode='markers'))
        fig_global.update_layout(height=500)

        st.plotly_chart(fig_global, use_container_width=True)



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
        
                mostra_statistiche()  # Versione completa
            else:
                mostra_statistiche_user()  # Versione semplificata per utenti normali

                
        elif page == "Profilo":
            if user not in users:
                st.warning("⚠️ Dati utente non disponibili. Ricarica la pagina o contatta l’amministratore.")
            else:
                st.markdown("## 👤 Profilo utente")
                st.markdown(f"**Username:** `{user}`")
        
                email_corrente = users.get(user, {}).get("email", "")
                st.markdown("_Email attualmente registrata. Se desideri modificarla, riscrivila nel campo qui sotto._")
                nuova_email = st.text_input("📧 Email", value=email_corrente)
        
                st.markdown("### 🔐 Modifica password")
                vecchia_pw = st.text_input("Vecchia password", type="password")
                nuova_pw = st.text_input("Nuova password", type="password")
                conferma_pw = st.text_input("Conferma nuova password", type="password")
        
                if st.button("💾 Salva modifiche al profilo"):
                    if vecchia_pw and vecchia_pw != users[user]["password"]:
                        st.error("❌ Vecchia password errata.")
                    elif nuova_pw and nuova_pw != conferma_pw:
                        st.warning("⚠️ Le nuove password non coincidono.")
                    elif not nuova_pw and nuova_email == email_corrente:
                        st.info("ℹ️ Nessuna modifica rilevata.")
                    else:
                        new_pw = nuova_pw if nuova_pw else None
                        new_email = nuova_email if nuova_email != email_corrente else None
                        update_user_info(service, users, user, new_password=new_pw, new_email=new_email)
                        # ricarica i dati aggiornati
                        users = read_users_file(service)
                        st.session_state.user_data = users
                        st.success("✅ Modifiche salvate con successo.")
                        st.rerun()
                        st.stop()



if __name__ == "__main__":
    main()



