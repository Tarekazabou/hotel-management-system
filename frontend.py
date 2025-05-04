import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.title("Gest'Hôtel - Hotel Management System")

# Session state for authentication
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'token' not in st.session_state:
    st.session_state.token = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Login Section
st.header("Login")
if not st.session_state.logged_in:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        response = requests.post(f"http://localhost:5000/login", json={"username": username, "password": password})
        if response.status_code == 200:
            st.session_state.logged_in = True
            st.session_state.token = response.json()['token']
            st.session_state.username = username
            st.success("Logged in successfully!")
        else:
            st.error("Invalid credentials")
else:
    st.write(f"Logged in as {st.session_state.username}")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.token = None
        st.session_state.username = None
        st.success("Logged out successfully!")

# Dynamic base URL and headers
BASE_URL = "http://localhost:5000"
headers = {"Authorization": st.session_state.token} if st.session_state.token else {}

# Rooms Section
st.header("Rooms")
if st.session_state.logged_in:
    try:
        response = requests.get(f"{BASE_URL}/chambres", headers=headers)
        if response.status_code == 200:
            chambres = response.json()
            for chambre in chambres:
                st.write(f"Room {chambre['numero_chambre']} - {chambre['type_chambre']} - €{chambre['prix_nuit']} - {chambre['statut']}")
        else:
            st.error("Access denied or server error")
    except requests.RequestException:
        st.error("Cannot connect to the backend for rooms. Ensure Flask is running.")
else:
    st.warning("Please log in to view rooms.")

st.header("Add a New Room")
if st.session_state.logged_in and st.session_state.username == 'admin':
    numero = st.text_input("Room Number")
    type_chambre = st.selectbox("Room Type", ["Simple", "Double", "Suite"])
    prix_nuit = st.number_input("Price per Night", min_value=0.0, value=100.0)
    statut = st.selectbox("Status", ["Libre", "Occupé", "En nettoyage"])
    if st.button("Add Room"):
        response = requests.post(f"{BASE_URL}/chambres", json={
            'numero_chambre': numero,
            'type_chambre': type_chambre,
            'prix_nuit': prix_nuit,
            'statut': statut
        }, headers=headers)
        if response.status_code == 201:
            st.success("Room added successfully!")
        else:
            st.error(f"Failed to add room: {response.json().get('error', 'Access denied')}")

# Clients Section
st.header("Clients")
try:
    response = requests.get(f"{BASE_URL}/clients")
    if response.status_code == 200:
        clients = response.json()
        for client in clients:
            st.write(f"Client {client['nom']} {client['prenom']} - Email: {client['email']}")
    else:
        st.error("Server error")
except requests.RequestException:
    st.error("Cannot connect to the backend for clients. Ensure Flask is running.")

st.header("Add a New Client")
nom = st.text_input("Last Name")
prenom = st.text_input("First Name")
telephone = st.text_input("Phone")
email = st.text_input("Email")
adresse = st.text_input("Address")
if st.button("Add Client"):
    response = requests.post(f"{BASE_URL}/clients", json={
        'nom': nom,
        'prenom': prenom,
        'telephone': telephone,
        'email': email,
        'adresse': adresse
    })
    if response.status_code == 201:
        st.success("Client added successfully!")
    else:
        st.error(f"Failed to add client: {response.json().get('error', 'Unknown error')}")

# Reservations Section
st.header("Reservations")
if st.session_state.logged_in:
    try:
        response = requests.get(f"{BASE_URL}/reservations", headers=headers)
        if response.status_code == 200:
            reservations = response.json()
            for reservation in reservations:
                st.write(f"Reservation {reservation['id_reservation']} - Client: {reservation['client_name']} - Room: {reservation['numero_chambre']} - From {reservation['date_debut']} to {reservation['date_fin']} - Status: {reservation['statut']}")
        else:
            st.error("Access denied or server error")
    except requests.RequestException:
        st.error("Cannot connect to the backend for reservations. Ensure Flask is running.")

st.header("Add a New Reservation")
if st.session_state.logged_in and st.session_state.username in ['staff', 'admin']:
    client_id = st.number_input("Client ID", min_value=1, step=1)
    room_id = st.number_input("Room ID", min_value=1, step=1)
    date_debut = st.date_input("Start Date")
    date_fin = st.date_input("End Date")
    if st.button("Add Reservation"):
        response = requests.post(f"{BASE_URL}/reservations", json={
            'id_client': client_id,
            'id_chambre': room_id,
            'date_debut': str(date_debut),
            'date_fin': str(date_fin),
            'statut': 'Confirmée'
        }, headers=headers)
        if response.status_code == 201:
            st.success("Reservation added successfully!")
        else:
            st.error(f"Failed to add reservation: {response.json().get('error', 'Access denied')}")

st.header("Cancel a Reservation")
if st.session_state.logged_in and st.session_state.username in ['staff', 'admin']:
    reservation_id_cancel = st.number_input("Reservation ID (to cancel)", min_value=1, step=1)
    if st.button("Cancel Reservation"):
        response = requests.delete(f"{BASE_URL}/reservations/{reservation_id_cancel}", headers=headers)
        if response.status_code == 200:
            st.success("Reservation cancelled successfully!")
        else:
            st.error(f"Failed to cancel reservation: {response.json().get('error', 'Access denied')}")

# Services Section
st.header("Services")
if st.session_state.logged_in:
    try:
        response = requests.get(f"{BASE_URL}/services", headers=headers)
        if response.status_code == 200:
            services = response.json()
            for service in services:
                st.write(f"Service {service['nom_service']} - {service['description']} - €{service['prix']} - {service['disponibilite']}")
        else:
            st.error("Access denied or server error")
    except requests.RequestException:
        st.error("Cannot connect to the backend for services. Ensure Flask is running.")

st.header("Add a New Service")
if st.session_state.logged_in and st.session_state.username == 'admin':
    nom_service = st.text_input("Service Name")
    description = st.text_input("Description")
    prix = st.number_input("Price", min_value=0.0, value=10.0)
    disponibilite = st.selectbox("Availability", ["Disponible", "Indisponible"])
    if st.button("Add Service"):
        response = requests.post(f"{BASE_URL}/services", json={
            'nom_service': nom_service,
            'description': description,
            'prix': prix,
            'disponibilite': disponibilite
        }, headers=headers)
        if response.status_code == 201:
            st.success("Service added successfully!")
        else:
            st.error(f"Failed to add service: {response.json().get('error', 'Access denied')}")

# Associate Service with Reservation
st.header("Associate Service with Reservation")
if st.session_state.logged_in and st.session_state.username in ['staff', 'admin']:
    reservation_id_service = st.number_input("Reservation ID (for service association)", min_value=1, step=1)
    service_id = st.number_input("Service ID", min_value=1, step=1)
    if st.button("Associate Service"):
        response = requests.post(f"{BASE_URL}/reservation_services", json={
            'id_reservation': reservation_id_service,
            'id_service': service_id
        }, headers=headers)
        if response.status_code == 201:
            st.success("Service associated with reservation successfully!")
        else:
            st.error(f"Failed to associate service: {response.json().get('error', 'Access denied')}")

# Factures Section
st.header("Invoices")
if st.session_state.logged_in:
    try:
        response = requests.get(f"{BASE_URL}/factures", headers=headers)
        if response.status_code == 200:
            factures = response.json()
            for facture in factures:
                st.write(f"Invoice {facture['id_facture']} - Reservation ID: {facture['id_reservation']} - Client: {facture['client_name']} - Total: €{facture['montant_total']} - Issued: {facture['date_emission']} - Status: {facture['statut']}")
        else:
            st.error("Access denied or server error")
    except requests.RequestException:
        st.error("Cannot connect to the backend for invoices. Ensure Flask is running.")

st.header("Generate a New Invoice")
if st.session_state.logged_in and st.session_state.username in ['staff', 'admin']:
    reservation_id_facture = st.number_input("Reservation ID (for invoice)", min_value=1, step=1)
    if st.button("Generate Invoice"):
        response = requests.post(f"{BASE_URL}/factures", json={
            'id_reservation': reservation_id_facture
        }, headers=headers)
        if response.status_code == 201:
            st.success(f"Invoice generated successfully! Total: €{response.json().get('montant_total')}")
        else:
            st.error(f"Failed to generate invoice: {response.json().get('error', 'Access denied')}")

st.header("Update Invoice Status")
if st.session_state.logged_in and st.session_state.username in ['staff', 'admin']:
    facture_id = st.number_input("Invoice ID (to update)", min_value=1, step=1)
    if st.button("Mark as Paid"):
        response = requests.put(f"{BASE_URL}/factures/{facture_id}", json={}, headers=headers)
        if response.status_code == 200:
            st.success("Invoice status updated to Payée!")
        else:
            st.error(f"Failed to update invoice: {response.json().get('error', 'Access denied')}")

# Avis (Reviews) Section
st.header("Reviews")
if st.session_state.logged_in:
    try:
        response = requests.get(f"{BASE_URL}/avis", headers=headers)
        if response.status_code == 200:
            avis = response.json()
            for review in avis:
                st.write(f"Review {review['id_avis']} - Client: {review['client_name']} - Reservation ID: {review['id_reservation']} - Rating: {review['note']}/5 - Comment: {review['commentaire']} - Date: {review['date_avis']}")
        else:
            st.error("Access denied or server error")
    except requests.RequestException:
        st.error("Cannot connect to the backend for reviews. Ensure Flask is running.")

st.header("Add a New Review")
client_id_avis = st.number_input("Client ID (for review)", min_value=1, step=1)
reservation_id_avis = st.number_input("Reservation ID (for review)", min_value=1, step=1)
note = st.slider("Rating (1-5)", min_value=1, max_value=5, step=1)
commentaire = st.text_area("Comment")
if st.button("Submit Review"):
    response = requests.post(f"{BASE_URL}/avis", json={
        'id_client': client_id_avis,
        'id_reservation': reservation_id_avis,
        'note': note,
        'commentaire': commentaire
    })
    if response.status_code == 201:
        st.success("Review submitted for moderation!")
    else:
        st.error(f"Failed to submit review: {response.json().get('error', 'Access denied')}")

st.header("Moderate Reviews")
if st.session_state.logged_in and st.session_state.username == 'admin':
    try:
        response = requests.get(f"{BASE_URL}/avis", headers=headers)
        if response.status_code == 200:
            avis = response.json()
            pending_reviews = [r for r in avis if r.get('moderated', 0) == 0]
            for review in pending_reviews:
                st.write(f"Pending Review {review['id_avis']} - Client: {review['client_name']} - Rating: {review['note']}/5 - Comment: {review['commentaire']}")
                if st.button(f"Approve Review {review['id_avis']}"):
                    resp = requests.put(f"{BASE_URL}/avis/{review['id_avis']}/moderate", headers=headers)
                    if resp.status_code == 200:
                        st.success(f"Review {review['id_avis']} approved!")
                    else:
                        st.error(f"Failed to approve review: {resp.json().get('error')}")
        else:
            st.error("Access denied or server error")
    except requests.RequestException:
        st.error("Cannot connect to the backend for reviews. Ensure Flask is running.")

# Dashboard Section
st.header("Dashboard")
if st.session_state.logged_in and st.session_state.username == 'admin':
    try:
        response = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        if response.status_code == 200:
            data = response.json()
            st.write(f"Occupancy Rate: {data['occupancy_rate']}%")
            st.write(f"Average Rating: {data['average_rating']}/5")

            # Create a simple chart
            chart_data = pd.DataFrame({
                'Metric': ['Occupancy Rate', 'Average Rating'],
                'Value': [data['occupancy_rate'], data['average_rating'] * 20]  # Scale rating to 0-100 for consistency
            })
            st.bar_chart(chart_data.set_index('Metric'))
        else:
            st.error("Access denied or server error")
    except requests.RequestException:
        st.error("Cannot connect to the backend for dashboard. Ensure Flask is running.")