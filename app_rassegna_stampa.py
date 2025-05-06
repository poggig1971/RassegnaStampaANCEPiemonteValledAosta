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
    append_log_entry
)

# === CONFIGURAZIONE ===
col1, col2 = st.columns([3, 5])
with col1:
    st.image("logo.png", width=300)

USER_CREDENTIALS = {
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

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if "logged_files" not in st.session_state:
    st.session_state.logged_files = set()

def login():
    st.markdown("## 🔐 Accesso alla Rassegna Stampa")
    username = st.text_input("👤 Nome utente", key="username_input")
    password = st.text_input("🔑 Password", type="password", key="password_input")
    if st.button("Accedi"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
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

# ... codice invariato fino a ...

    # Notifica rassegna odierna
    oggi = date.today().strftime("%Y.%m.%d")
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

# ... codice invariato successivo ...

main()
