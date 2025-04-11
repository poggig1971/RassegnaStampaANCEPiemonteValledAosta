import streamlit as st
import os
from datetime import date
from pathlib import Path
import base64

# === LOGO ===
st.image("logo.png", width=200)

# === CONFIGURAZIONE ===
UPLOAD_DIR = "uploaded_pdfs"
Path(UPLOAD_DIR).mkdir(exist_ok=True)

USER_CREDENTIALS = {
    "A1": "A1",  # Admin
    "U1": "P1"   # Utente semplice
}

# === INIZIALIZZAZIONE SESSIONE ===
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# === LOGIN ===
def login():
    st.title("Accesso Rassegna Stampa")
    username = st.text_input("Nome utente", key="username_input")
    password = st.text_input("Password", type="password", key="password_input")

    if st.button("Accedi"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
    st.session_state.logged_in = True
    st.session_state.username = username
    st.experimental_rerun()
        else:
            st.error("Credenziali non valide")

# === VISUALIZZATORE PDF ===
def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# === DASHBOARD ===
def dashboard():
    st.title("Rassegna Stampa PDF")
    oggi = date.today().strftime("%Y-%m-%d")
    pdf_filename = f"{UPLOAD_DIR}/rassegna_{oggi}.pdf"

    # === AREA ADMIN ===
    if st.session_state.username == "A1":
        st.subheader("Carica la rassegna stampa in PDF")
        uploaded_file = st.file_uploader("Scegli un file PDF", type="pdf")
        if uploaded_file:
            with open(pdf_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"File caricato come: rassegna_{oggi}.pdf")

        # Pulsante per eliminare il file
        if os.path.exists(pdf_filename):
            if st.button("Elimina la rassegna di oggi"):
                os.remove(pdf_filename)
                st.success("Rassegna eliminata con successo.")
                st.experimental_rerun()

    # === VISUALIZZAZIONE PDF ===
    if os.path.exists(pdf_filename):
        st.subheader(f"🔵: {oggi}")
        with open(pdf_filename, "rb") as f:
            st.download_button(label="Scarica PDF", data=f, file_name=f"rassegna_{oggi}.pdf")
        show_pdf(pdf_filename)
    else:
        st.info("La rassegna di oggi non è ancora stata caricata.")

# === MAIN ===
def main():
    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.write(f"Utente: {st.session_state.username}")
        if st.sidebar.button("Esci"):
            st.session_state.logged_in = False
            st.session_state.username = ""
        dashboard()

main()
