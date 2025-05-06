Questo è app\_rassegna\_stampa.py da modificare: import streamlit as st
import os
from datetime import datetime
import pytz
import pandas as pd
from io import StringIO, BytesIO

from drive\_utils import (
get\_drive\_service,
get\_or\_create\_folder,
upload\_pdf\_to\_drive,
list\_pdfs\_in\_folder,
download\_pdf,
FOLDER\_NAME
)

# === CONFIGURAZIONE ===

col1, col2 = st.columns(\[3, 5])
with col1:
st.image("logo.png", width=300)

USER\_CREDENTIALS = {
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

if "logged\_in" not in st.session\_state:
st.session\_state.logged\_in = False
st.session\_state.username = ""
if "logged\_files" not in st.session\_state:
st.session\_state.logged\_files = set()

def login():
st.markdown("## 🔐 Accesso alla Rassegna Stampa")
username = st.text\_input("👤 Nome utente", key="username\_input")
password = st.text\_input("🔑 Password", type="password", key="password\_input")
if st.button("Accedi"):
if username in USER\_CREDENTIALS and USER\_CREDENTIALS\[username] == password:
st.session\_state.logged\_in = True
st.session\_state.username = username
st.success("✅ Accesso effettuato")
st.rerun()
else:
st.error("❌ Credenziali non valide. Riprova.")

def is\_valid\_date\_filename(filename):
try:
datetime.strptime(filename.replace(".pdf", ""), "%Y.%m.%d")
return True
except ValueError:
return False

def log\_visualizzazione(username, filename):
tz = pytz.timezone("Europe/Rome")
now = datetime.now(tz)
data = now\.strftime("%Y-%m-%d")
ora = now\.strftime("%H:%M:%S")

```
try:
    service = get_drive_service()
    folder_id = get_or_create_folder(service, FOLDER_NAME)
    existing_files = list_pdfs_in_folder(service, folder_id)

    file_id = next((f["id"] for f in existing_files if f["name"] == "log_visualizzazioni.csv"), None)
    if file_id:
        content = download_pdf(service, file_id, return_bytes=True).decode("utf-8")
        df = pd.read_csv(StringIO(content))
    else:
        df = pd.DataFrame(columns=["data", "ora", "utente", "file"])

    new_row = {"data": data, "ora": ora, "utente": username, "file": filename}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    if file_id:
        service.files().delete(fileId=file_id).execute()

    upload_pdf_to_drive(service, folder_id, csv_buffer, "log_visualizzazioni.csv", is_memory_file=True)

except Exception as e:
    st.warning(f"⚠️ Impossibile aggiornare il log su Drive: {e}")
```

def dashboard():
st.markdown("## 📚 Archivio Rassegne")
nome\_utente = st.session\_state.username
if nome\_utente == "Presidente":
st.markdown("👑 **Benvenuto Presidente**")
st.caption("Grazie.")
else:
st.markdown(f"👋 **Benvenuto da ANCE {nome\_utente}!**")
st.caption("Accedi alle rassegne stampa aggiornate giorno per giorno.")

```
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
    st.markdown("### 📄 Carica nuova rassegna stampa")
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
            file_bytes = BytesIO(uploaded_file.getbuffer())
            upload_pdf_to_drive(service, folder_id, file_bytes, filename, is_memory_file=True)
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
    [f["name"].replace(".pdf", "") for f in files if f["name"].lower().endswith(".pdf") and is_valid_date_filename(f["name"])],
    reverse=True
)

if date_options:
    selected_date = st.selectbox("🗓️ Seleziona una data", date_options)
    selected_file = f"{selected_date}.pdf"
    file_id = next((f["id"] for f in files if f["name"] == selected_file), None)
    if file_id:
        content = download_pdf(service, file_id, return_bytes=True)
        st.download_button(f"⬇️ Scarica rassegna {selected_date}", data=BytesIO(content), file_name=selected_file)
        if selected_file not in st.session_state.logged_files:
            log_visualizzazione(st.session_state.username, selected_file)
            st.session_state.logged_files.add(selected_file)
else:
    st.info("📬 Nessun file PDF trovato su Google Drive.")
```

def mostra\_statistiche():
st.markdown("## 📈 Statistiche di accesso")
try:
service = get\_drive\_service()
folder\_id = get\_or\_create\_folder(service, FOLDER\_NAME)
files = list\_pdfs\_in\_folder(service, folder\_id)
file\_id = next((f\["id"] for f in files if f\["name"] == "log\_visualizzazioni.csv"), None)

```
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
```

def main():
if not st.session\_state.logged\_in:
login()
else:
with st.sidebar:
st.markdown("## ⚙️ Pannello")
st.markdown(f"👤 Utente: **{st.session\_state.username}**")
page = st.radio("📋 Seleziona una pagina", \["Archivio", "Statistiche"])
st.write("---")
if st.button("🚪 Esci"):
st.session\_state.clear()
st.rerun()
if page == "Archivio":
dashboard()
elif page == "Statistiche":
if st.session\_state.username == "Admin":
mostra\_statistiche()
else:
st.warning("⚠️ Accesso riservato. Le statistiche sono visibili solo all'amministratore.")

main()




