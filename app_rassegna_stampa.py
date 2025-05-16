# Tutto il codice aggiornato incluso dashboard corretto
# Inserisci qui tutto il contenuto integrato

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
            if f["name"].lower().endswith(".pdf") and is_valid_date_filename(f["name"])
        ]
        most_recent = max(date_strings)
        st.caption(f"🕒 Ultimo file disponibile: {most_recent}")
    else:
        st.caption("🕒 Nessun file PDF trovato su Google Drive.")

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

    seen = set()
    date_options = []
    for f in files:
        name = f["name"]
        if name.lower().endswith(".pdf") and is_valid_date_filename(name):
            date_str = name.replace(".pdf", "")
            if date_str not in seen:
                seen.add(date_str)
                date_options.append(date_str)
    date_options = sorted(date_options, reverse=True)

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
