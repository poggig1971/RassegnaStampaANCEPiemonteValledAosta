Carico: import streamlit as st

# Credenziali base (da sostituire con login sicuro in futuro)
USER_CREDENTIALS = {
    "admin": "AncePiemonte",
    "utente": "CorsoDuca15"
}

# Sessione di login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

def login():
    st.title("Accesso Rassegna Stampa")
    username = st.text_input("Nome utente")
    password = st.text_input("Password", type="password")
    if st.button("Accedi"):
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Accesso effettuato con successo!")
            st.experimental_rerun()
        else:
            st.error("Credenziali non valide")

def dashboard():
    st.title("Rassegna Stampa")
    st.markdown("### Seleziona una sezione per visualizzare gli articoli")

    rassegna = {
        "DICONO DI NOI": [
            ("CORRIERE DELLA SERA", "«Città nel futuro» A ottobre a Roma la conferenza diretta da Rutelli", "Redazione"),
            ("SOLE 24 ORE", "Città nel futuro 2030-50 «Priorità a casa e acqua»", "Redazione")
        ],
        "EDILIZIA / URBANISTICA": [
            ("CORRIERE DELLA SERA", "Nagel: con il calo dei tassi Mps conviene ancora meno", "Daniela Polizzi"),
            ("CORRIERE TORINO", "Negozi in vendita: 1.286 immobili passati di mano", "Nicolò Fagone La Zita")
        ],
        "OPERE PUBBLICHE": [
            ("CORRIERE DELLA SERA", "Cdp fa utili record: 3,3 miliardi E Indica Giana per Autostrade", "Andrea Ducci"),
            ("ITALIA OGGI", "Fincantieri in Albania", "Giovanni Galli")
        ]
    }

    categoria = st.selectbox("Categoria", list(rassegna.keys()))
    for testata, titolo, autore in rassegna[categoria]:
        st.markdown(f"- **{testata}**: *{titolo}* — _{autore}_")

    st.markdown("---")
    st.markdown("Servizio a cura di **Telpress Italia S.r.l.**")

def main():
    if not st.session_state.logged_in:
        login()
    else:
        st.sidebar.write(f"Utente: {st.session_state.username}")
        if st.sidebar.button("Esci"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.experimental_rerun()
        dashboard()

main()
