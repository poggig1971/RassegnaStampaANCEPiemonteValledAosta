import streamlit as st
import os
from datetime import date
from pathlib import Path

st.image("img_8865.jpg", width=300)

# === CONFIGURAZIONE ===
UPLOAD_DIR = "uploaded_pdfs"
Path(UPLOAD_DIR).mkdir(exist_ok=True)

USER_CREDENTIALS = {
    "Admin": "AncePiemonte",
    "U1": "P1"
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
        else:
            st.error("Credenziali non valide")

# === DASHBOARD ===
def dashboard():
    st.title("Rassegna Stampa PDF")
    oggi = date.today().strftime("%Y-%m-%d")
    pdf_filename = f"{UPLOAD_DIR}/rassegna_{oggi}.pdf"

    # Se Admin, consente caricamento
    if st.session_state.username == "Admin":
        st.subheader("Carica la rassegna stampa in PDF")
        uploaded_file = st.file_uploader("Scegli un file PDF", type="pdf")
        if uploaded_file:
            with open(pdf_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"File caricato come: rassegna_{oggi}.pdf")

    # Mostra il PDF se presente
    if os.path.exists(pdf_filename):
        st.subheader(f"Rassegna del giorno: {oggi}")
        with open(pdf_filename, "rb") as f:
            st.download_button(label="Scarica PDF", data=f, file_name=f"rassegna_{oggi}.pdf")
        st.components.v1.iframe(src=pdf_filename, height=800)
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
