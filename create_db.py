# database.py (Corrected Version - Final)
import sqlite3
from datetime import date, timedelta
import os # For checking if DB exists

# --- Main Database Setup ---
def setup_database():
    db_file = 'gesthotel.db'
    # Check if DB exists, delete if it does to ensure a fresh start
    # You might want to comment this out if you want to preserve data between runs *after* the schema is stable
    if os.path.exists(db_file):
        print(f"Deleting existing database file: {db_file}")
        os.remove(db_file)

    print(f"Connecting to database '{db_file}'...")
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    print("Enabling foreign keys...")
    cursor.execute('PRAGMA foreign_keys = ON')

    # --- Table Creation ---
    print("Creating tables if they don't exist...")

    # Table: clients
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id_client INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            telephone TEXT,
            email TEXT UNIQUE NOT NULL,
            adresse TEXT,
            statut_fidelite TEXT DEFAULT 'Standard' NOT NULL CHECK(statut_fidelite IN ('Standard', 'VIP', 'Or'))
        )
    ''')

    # Table: chambres
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chambres (
            id_chambre INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_chambre TEXT UNIQUE NOT NULL,
            type_chambre TEXT NOT NULL CHECK(type_chambre IN ('Simple', 'Double', 'Suite', 'Familiale')),
            prix_nuit_base REAL NOT NULL CHECK(prix_nuit_base >= 0),
            statut TEXT NOT NULL CHECK(statut IN ('Libre', 'Occupé', 'En nettoyage'))
        )
    ''')

    # Table: tarifs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tarifs (
            id_tarif INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_tarif TEXT UNIQUE NOT NULL,
            description TEXT,
            reduction_pourcentage REAL DEFAULT 0.0 CHECK(reduction_pourcentage >= 0 AND reduction_pourcentage <= 100),
            condition_application TEXT
        )
    ''')

    # Table: reservations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id_reservation INTEGER PRIMARY KEY AUTOINCREMENT,
            id_client INTEGER NOT NULL,
            id_chambre INTEGER NOT NULL,
            id_tarif INTEGER NOT NULL,
            date_debut TEXT NOT NULL,
            date_fin TEXT NOT NULL,
            prix_nuit_applique REAL NOT NULL,
            statut TEXT NOT NULL CHECK(statut IN ('Confirmée', 'Annulée', 'Terminée', 'En attente')),
            FOREIGN KEY (id_client) REFERENCES clients(id_client) ON DELETE CASCADE,
            FOREIGN KEY (id_chambre) REFERENCES chambres(id_chambre) ON DELETE RESTRICT,
            FOREIGN KEY (id_tarif) REFERENCES tarifs(id_tarif) ON DELETE RESTRICT
        )
    ''')

    # Table: services
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id_service INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_service TEXT UNIQUE NOT NULL,
            description TEXT,
            prix REAL NOT NULL CHECK(prix >= 0),
            disponibilite TEXT NOT NULL CHECK(disponibilite IN ('Disponible', 'Indisponible'))
        )
    ''')

    # Table: reservation_services
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservation_services (
            id_reservation INTEGER NOT NULL,
            id_service INTEGER NOT NULL,
            quantite INTEGER DEFAULT 1 CHECK(quantite > 0),
            date_service TEXT,
            FOREIGN KEY (id_reservation) REFERENCES reservations(id_reservation) ON DELETE CASCADE,
            FOREIGN KEY (id_service) REFERENCES services(id_service) ON DELETE CASCADE,
            PRIMARY KEY (id_reservation, id_service)
        )
    ''')

    # Table: consommations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consommations (
            id_consommation INTEGER PRIMARY KEY AUTOINCREMENT,
            id_chambre INTEGER NOT NULL,
            id_reservation INTEGER,
            type_consommation TEXT NOT NULL CHECK(type_consommation IN ('Énergie', 'Eau', 'Gaz', 'Minibar')),
            date_releve TEXT NOT NULL,
            valeur REAL NOT NULL,
            unite TEXT NOT NULL,
            cout_unitaire REAL NOT NULL,
            FOREIGN KEY (id_chambre) REFERENCES chambres(id_chambre) ON DELETE CASCADE,
            FOREIGN KEY (id_reservation) REFERENCES reservations(id_reservation) ON DELETE SET NULL
        )
    ''')

    # Table: factures
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS factures (
            id_facture INTEGER PRIMARY KEY AUTOINCREMENT,
            id_reservation INTEGER UNIQUE NOT NULL,
            montant_chambre REAL NOT NULL,
            montant_services REAL NOT NULL,
            montant_consommations REAL NOT NULL,
            montant_total REAL NOT NULL,
            date_emission TEXT NOT NULL,
            statut TEXT NOT NULL CHECK(statut IN ('Payée', 'Non payée', 'Partiellement payée')),
            mode_paiement TEXT CHECK(mode_paiement IN ('Carte', 'Espèces', 'Virement', 'Chèque', NULL)),
            FOREIGN KEY (id_reservation) REFERENCES reservations(id_reservation) ON DELETE RESTRICT
        )
    ''')

    # Table: avis
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS avis (
            id_avis INTEGER PRIMARY KEY AUTOINCREMENT,
            id_client INTEGER NOT NULL,
            id_reservation INTEGER UNIQUE NOT NULL,
            note INTEGER NOT NULL CHECK(note BETWEEN 1 AND 5),
            commentaire TEXT,
            date_avis TEXT NOT NULL,
            moderated INTEGER DEFAULT 0 CHECK(moderated IN (0, 1)),
            FOREIGN KEY (id_client) REFERENCES clients(id_client) ON DELETE CASCADE,
            FOREIGN KEY (id_reservation) REFERENCES reservations(id_reservation) ON DELETE CASCADE
        )
    ''')

    # Table: users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id_user INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, -- REMINDER: HASH PASSWORDS IN PRODUCTION!
            role TEXT NOT NULL CHECK(role IN ('admin', 'staff', 'client'))
        )
    ''')

    print("Tables created successfully.")

    # --- Triggers ---
    print("Creating triggers...")
    cursor.execute("DROP TRIGGER IF EXISTS update_room_status_after_reservation")
    cursor.execute('''
        CREATE TRIGGER update_room_status_after_reservation
        AFTER UPDATE OF statut ON reservations
        WHEN NEW.statut = 'Terminée' AND OLD.statut != 'Terminée'
        BEGIN
            UPDATE chambres
            SET statut = 'En nettoyage'
            WHERE id_chambre = NEW.id_chambre;
        END;
    ''')
    print("Triggers created successfully.")

    # --- Helper Function for Sample Data Insertion (Simpler Approach) ---
    def insert_if_not_exists(sql, params):
        # Basic check based on unique constraint violation potential
        try:
            cursor.execute(sql, params)
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # print(f"Skipping insert due to potential duplicate: {params}")
            # Optionally fetch existing ID if needed elsewhere
            return None # Indicate skipped or fetch ID based on params

    # --- Sample Data Insertion ---
    print("Inserting sample data...")
    try:
        # Users
        insert_if_not_exists("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'admin'))
        insert_if_not_exists("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('staff', 'staff123', 'staff'))
        insert_if_not_exists("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('client', 'client123', 'client'))

        # Tarifs
        tarif_standard_id = insert_if_not_exists("INSERT INTO tarifs (nom_tarif, description, condition_application) VALUES (?, ?, ?)", ('Standard', 'Tarif normal', 'None')) or conn.execute("SELECT id_tarif FROM tarifs WHERE nom_tarif='Standard'").fetchone()[0]
        tarif_vip_id = insert_if_not_exists("INSERT INTO tarifs (nom_tarif, description, reduction_pourcentage, condition_application) VALUES (?, ?, ?, ?)", ('VIP Discount', 'Réduction pour clients VIP', 15.0, 'VIP Status')) or conn.execute("SELECT id_tarif FROM tarifs WHERE nom_tarif='VIP Discount'").fetchone()[0]
        tarif_promo_id = insert_if_not_exists("INSERT INTO tarifs (nom_tarif, description, reduction_pourcentage, condition_application) VALUES (?, ?, ?, ?)", ('Weekend Promo', 'Promotion spéciale weekend', 10.0, 'Weekend Booking')) or conn.execute("SELECT id_tarif FROM tarifs WHERE nom_tarif='Weekend Promo'").fetchone()[0]

        # Chambres
        chambre1_id = insert_if_not_exists("INSERT INTO chambres (numero_chambre, type_chambre, prix_nuit_base, statut) VALUES (?, ?, ?, ?)", ('101', 'Simple', 80.0, 'Libre')) or conn.execute("SELECT id_chambre FROM chambres WHERE numero_chambre='101'").fetchone()[0]
        chambre2_id = insert_if_not_exists("INSERT INTO chambres (numero_chambre, type_chambre, prix_nuit_base, statut) VALUES (?, ?, ?, ?)", ('102', 'Suite', 150.0, 'Libre')) or conn.execute("SELECT id_chambre FROM chambres WHERE numero_chambre='102'").fetchone()[0]
        chambre3_id = insert_if_not_exists("INSERT INTO chambres (numero_chambre, type_chambre, prix_nuit_base, statut) VALUES (?, ?, ?, ?)", ('103', 'Double', 100.0, 'Libre')) or conn.execute("SELECT id_chambre FROM chambres WHERE numero_chambre='103'").fetchone()[0]

        # Clients
        client1_id = insert_if_not_exists("INSERT INTO clients (nom, prenom, telephone, email, adresse, statut_fidelite) VALUES (?, ?, ?, ?, ?, ?)", ('Dupont', 'Jean', '123456789', 'jean.dupont@example.com', '123 Rue de Paris', 'Standard')) or conn.execute("SELECT id_client FROM clients WHERE email='jean.dupont@example.com'").fetchone()[0]
        client2_id = insert_if_not_exists("INSERT INTO clients (nom, prenom, telephone, email, adresse, statut_fidelite) VALUES (?, ?, ?, ?, ?, ?)", ('Martin', 'Sophie', '987654321', 'sophie.martin@example.com', '456 Avenue de Lyon', 'VIP')) or conn.execute("SELECT id_client FROM clients WHERE email='sophie.martin@example.com'").fetchone()[0]

        # Services
        service1_id = insert_if_not_exists("INSERT INTO services (nom_service, description, prix, disponibilite) VALUES (?, ?, ?, ?)", ('Petit-déjeuner', 'Buffet continental', 15.0, 'Disponible')) or conn.execute("SELECT id_service FROM services WHERE nom_service='Petit-déjeuner'").fetchone()[0]
        service2_id = insert_if_not_exists("INSERT INTO services (nom_service, description, prix, disponibilite) VALUES (?, ?, ?, ?)", ('Spa Access', 'Accès au spa', 50.0, 'Disponible')) or conn.execute("SELECT id_service FROM services WHERE nom_service='Spa Access'").fetchone()[0]
        service3_id = insert_if_not_exists("INSERT INTO services (nom_service, description, prix, disponibilite) VALUES (?, ?, ?, ?)", ('Navette Aéroport', 'Transfert aéroport aller-retour', 30.0, 'Disponible')) or conn.execute("SELECT id_service FROM services WHERE nom_service='Navette Aéroport'").fetchone()[0]

        # Sample Reservations
        res1_start = (date.today() + timedelta(days=5)).isoformat()
        res1_end = (date.today() + timedelta(days=8)).isoformat()
        res1_price = 80.0
        # Check if reservation exists before inserting
        existing_res1 = conn.execute("SELECT id_reservation FROM reservations WHERE id_client=? AND date_debut=? AND id_chambre=?", (client1_id, res1_start, chambre1_id)).fetchone()
        if not existing_res1:
            cursor.execute("INSERT INTO reservations (id_client, id_chambre, id_tarif, date_debut, date_fin, prix_nuit_applique, statut) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (client1_id, chambre1_id, tarif_standard_id, res1_start, res1_end, res1_price, 'Confirmée'))
            res1_id = cursor.lastrowid
        else:
            res1_id = existing_res1[0]

        res2_start = (date.today() + timedelta(days=10)).isoformat()
        res2_end = (date.today() + timedelta(days=15)).isoformat()
        res2_price = 127.5
        existing_res2 = conn.execute("SELECT id_reservation FROM reservations WHERE id_client=? AND date_debut=? AND id_chambre=?", (client2_id, res2_start, chambre2_id)).fetchone()
        if not existing_res2:
            cursor.execute("INSERT INTO reservations (id_client, id_chambre, id_tarif, date_debut, date_fin, prix_nuit_applique, statut) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (client2_id, chambre2_id, tarif_vip_id, res2_start, res2_end, res2_price, 'Confirmée'))
            res2_id = cursor.lastrowid
        else:
             res2_id = existing_res2[0]

        # Link services to reservations (Use INSERT OR IGNORE for safety on rerun)
        if res1_id:
             cursor.execute("INSERT OR IGNORE INTO reservation_services (id_reservation, id_service, quantite) VALUES (?, ?, ?)", (res1_id, service1_id, 3))
        if res2_id:
             cursor.execute("INSERT OR IGNORE INTO reservation_services (id_reservation, id_service) VALUES (?, ?)", (res2_id, service1_id))
             cursor.execute("INSERT OR IGNORE INTO reservation_services (id_reservation, id_service) VALUES (?, ?)", (res2_id, service2_id))

        # Sample Consommations (Use INSERT OR IGNORE)
        cons_date = (date.today() - timedelta(days=2)).isoformat()
        cursor.execute("INSERT OR IGNORE INTO consommations (id_chambre, type_consommation, date_releve, valeur, unite, cout_unitaire) VALUES (?, ?, ?, ?, ?, ?)", (chambre1_id, 'Énergie', cons_date, 5.2, 'kWh', 0.15))
        cursor.execute("INSERT OR IGNORE INTO consommations (id_chambre, type_consommation, date_releve, valeur, unite, cout_unitaire) VALUES (?, ?, ?, ?, ?, ?)", (chambre2_id, 'Eau', cons_date, 0.8, 'm³', 3.50))

        # Sample Avis (Use INSERT OR IGNORE)
        if res1_id:
            avis_date = (date.today() + timedelta(days=9)).isoformat()
            cursor.execute("INSERT OR IGNORE INTO avis (id_client, id_reservation, note, commentaire, date_avis, moderated) VALUES (?, ?, ?, ?, ?, ?)", (client1_id, res1_id, 4, 'Séjour agréable, chambre propre.', avis_date, 1))

        # Sample Factures (Use INSERT OR IGNORE)
        if res1_id:
            cursor.execute("INSERT OR IGNORE INTO factures (id_reservation, montant_chambre, montant_services, montant_consommations, montant_total, date_emission, statut) VALUES (?, ?, ?, ?, ?, ?, ?)", (res1_id, 240.0, 45.0, 0.0, 285.0, date.today().isoformat(), 'Non payée'))

        print("Sample data insertion completed.")
        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred during sample data insertion: {e}")
        print("Rolling back sample data changes...")
        conn.rollback() # Rollback changes if any error occurred

    finally:
        print("Closing database connection.")
        conn.close()

if __name__ == '__main__':
    setup_database()
    print("\nDatabase setup process finished.")
    print(f"Database file '{'gesthotel.db'}' should now be updated/created.")