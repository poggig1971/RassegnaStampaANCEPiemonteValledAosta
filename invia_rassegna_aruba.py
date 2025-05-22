import streamlit as st
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itertools import islice
from drive_utils import get_drive_service, read_users_file

# ⚙️ Configurazione da secrets
EMAIL = st.secrets["EMAIL"]
PASSWORD = st.secrets["PASSWORD"]
LINK_RASSEGNA = "https://rassegna.ancepiemonte.it"  # Puoi cambiarlo se hai link dinamico

# 🔁 Divide la lista in blocchi da 20
def dividi_blocchi(lista, blocco=20):
    it = iter(lista)
    return iter(lambda: list(islice(it, blocco)), [])

# ✉️ Crea il messaggio email
def crea_email(destinatari):
    msg = MIMEMultipart()
    msg['From'] = EMAIL
    msg['To'] = ", ".join(destinatari)
    msg['Subject'] = "Rassegna stampa ANCE Piemonte – disponibile ora"

    corpo = f"""Gentile utente,

è disponibile la rassegna stampa aggiornata di ANCE Piemonte.

📎 Puoi consultarla direttamente qui:
{LINK_RASSEGNA}

Cordiali saluti,  
Il team ANCE Piemonte

---
Se non desideri più ricevere questa comunicazione, rispondi con oggetto CANCELLA oppure scrivici a {EMAIL}.
"""

    msg.attach(MIMEText(corpo, 'plain'))
    return msg

# 📤 Invia un'email a un gruppo
def invia_email(gruppo_destinatari):
    msg = crea_email(gruppo_destinatari)
    with smtplib.SMTP("smtp.aruba.it", 587) as server:
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, gruppo_destinatari, msg.as_string())

# 🚀 Funzione principale
def invia_notifiche_email(service_drive=None):
    if service_drive is None:
        service_drive = get_drive_service()

    # ✅ Modalità test: invio a un solo destinatario
    destinatari = ["poggig71@gmail.com"]
    st.write(f"✉️ Inviando email di prova a: {destinatari}")

    gruppi = list(dividi_blocchi(destinatari, 20))
    for i, gruppo in enumerate(gruppi, start=1):
        st.write(f"📦 Inviando gruppo {i} di {len(gruppi)}: {gruppo}")
        invia_email(gruppo)

    # 🔁 Produzione - commentato per ora
    # utenti = read_users_file(service_drive)
    # destinatari = list(utenti.keys())

# 👇 Per esecuzione diretta
if __name__ == "__main__":
    invia_notifiche_email()
