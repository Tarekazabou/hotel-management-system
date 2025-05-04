import sqlite3

# Connect to the database (creates gesthotel.db if it doesn't exist)
conn = sqlite3.connect('gesthotel.db')
cursor = conn.cursor()

# Enable foreign key support
cursor.execute('PRAGMA foreign_keys = ON')

# Create the chambres table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS chambres (
        id_chambre INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_chambre TEXT UNIQUE NOT NULL,
        type_chambre TEXT NOT NULL,
        prix_nuit REAL NOT NULL,
        statut TEXT NOT NULL CHECK(statut IN ('Libre', 'Occupé', 'En nettoyage'))
    )
''')

# Insert sample data into chambres and get the IDs
cursor.execute('''
    INSERT OR IGNORE INTO chambres (numero_chambre, type_chambre, prix_nuit, statut)
    VALUES ('101', 'Simple', 80.0, 'Libre')
''')
chambre1_id = cursor.lastrowid
cursor.execute('''
    INSERT OR IGNORE INTO chambres (numero_chambre, type_chambre, prix_nuit, statut)
    VALUES ('102', 'Suite', 150.0, 'Occupé')
''')
chambre2_id = cursor.lastrowid
cursor.execute('''
    INSERT OR IGNORE INTO chambres (numero_chambre, type_chambre, prix_nuit, statut)
    VALUES ('103', 'Double', 100.0, 'Libre')
''')
chambre3_id = cursor.lastrowid

# Create the clients table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id_client INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        telephone TEXT,
        email TEXT UNIQUE NOT NULL,
        adresse TEXT
    )
''')

# Insert sample data into clients and get the IDs
cursor.execute('''
    INSERT OR IGNORE INTO clients (nom, prenom, telephone, email, adresse)
    VALUES ('Dupont', 'Jean', '123456789', 'jean.dupont@gmail.com', '123 Rue de Paris')
''')
client1_id = cursor.lastrowid
cursor.execute('''
    INSERT OR IGNORE INTO clients (nom, prenom, telephone, email, adresse)
    VALUES ('Martin', 'Sophie', '987654321', 'sophie.martin@gmail.com', '456 Avenue de Lyon')
''')
client2_id = cursor.lastrowid

# Create the reservations table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS reservations (
        id_reservation INTEGER PRIMARY KEY AUTOINCREMENT,
        id_client INTEGER NOT NULL,
        id_chambre INTEGER NOT NULL,
        date_debut TEXT NOT NULL,
        date_fin TEXT NOT NULL,
        statut TEXT NOT NULL CHECK(statut IN ('Confirmée', 'Annulée', 'Terminée')),
        FOREIGN KEY (id_client) REFERENCES clients(id_client),
        FOREIGN KEY (id_chambre) REFERENCES chambres(id_chambre)
    )
''')

# Insert sample data into reservations using the captured IDs

# Create the services table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS services (
        id_service INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_service TEXT NOT NULL,
        description TEXT,
        prix REAL NOT NULL,
        disponibilite TEXT NOT NULL CHECK(disponibilite IN ('Disponible', 'Indisponible'))
    )
''')

# Insert sample data into services
cursor.execute('''
    INSERT OR IGNORE INTO services (nom_service, description, prix, disponibilite)
    VALUES ('Petit-déjeuner', 'Buffet continental', 15.0, 'Disponible')
''')
service1_id = cursor.lastrowid
cursor.execute('''
    INSERT OR IGNORE INTO services (nom_service, description, prix, disponibilite)
    VALUES ('Spa', 'Accès au spa avec massage', 50.0, 'Disponible')
''')
service2_id = cursor.lastrowid

# Create the reservation_services junction table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS reservation_services (
        id_reservation INTEGER NOT NULL,
        id_service INTEGER NOT NULL,
        FOREIGN KEY (id_reservation) REFERENCES reservations(id_reservation),
        FOREIGN KEY (id_service) REFERENCES services(id_service),
        PRIMARY KEY (id_reservation, id_service)
    )
''')

# Insert sample data into reservation_services using the captured IDs
cursor.execute('''
    INSERT OR IGNORE INTO reservation_services (id_reservation, id_service)
    VALUES ((SELECT id_reservation FROM reservations WHERE id_client = ? AND id_chambre = ? LIMIT 1), ?)
''', (client1_id, chambre2_id, service1_id))
cursor.execute('''
    INSERT OR IGNORE INTO reservation_services (id_reservation, id_service)
    VALUES ((SELECT id_reservation FROM reservations WHERE id_client = ? AND id_chambre = ? LIMIT 1), ?)
''', (client2_id, chambre1_id, service2_id))

# Create the factures table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS factures (
        id_facture INTEGER PRIMARY KEY AUTOINCREMENT,
        id_reservation INTEGER NOT NULL,
        montant_total REAL NOT NULL,
        date_emission TEXT NOT NULL,
        statut TEXT NOT NULL CHECK(statut IN ('Payée', 'Non payée')),
        FOREIGN KEY (id_reservation) REFERENCES reservations(id_reservation)
    )
''')

# Insert sample data into factures using the captured reservation IDs
cursor.execute('''
    INSERT OR IGNORE INTO factures (id_reservation, montant_total, date_emission, statut)
    VALUES ((SELECT id_reservation FROM reservations WHERE id_client = ? AND id_chambre = ? LIMIT 1), 350.0, '2025-05-03', 'Non payée')
''', (client1_id, chambre2_id))
cursor.execute('''
    INSERT OR IGNORE INTO factures (id_reservation, montant_total, date_emission, statut)
    VALUES ((SELECT id_reservation FROM reservations WHERE id_client = ? AND id_chambre = ? LIMIT 1), 250.0, '2025-05-12', 'Non payée')
''', (client2_id, chambre1_id))

# Create the avis (reviews) table with moderation
cursor.execute('''
    CREATE TABLE IF NOT EXISTS avis (
        id_avis INTEGER PRIMARY KEY AUTOINCREMENT,
        id_client INTEGER NOT NULL,
        id_reservation INTEGER NOT NULL,
        note INTEGER NOT NULL CHECK(note BETWEEN 1 AND 5),
        commentaire TEXT,
        date_avis TEXT NOT NULL,
        moderated INTEGER DEFAULT 0 CHECK(moderated IN (0, 1)), -- 0 = Pending, 1 = Approved
        FOREIGN KEY (id_client) REFERENCES clients(id_client),
        FOREIGN KEY (id_reservation) REFERENCES reservations(id_reservation)
    )
''')

# Insert sample data into avis
cursor.execute('''
    INSERT OR IGNORE INTO avis (id_client, id_reservation, note, commentaire, date_avis, moderated)
    VALUES (?, (SELECT id_reservation FROM reservations WHERE id_client = ? AND id_chambre = ? LIMIT 1), 4, 'Excellent séjour, le spa était super !', '2025-05-04', 1)
''', (client1_id, client1_id, chambre2_id))

# Create the users table for authentication
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id_user INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'staff', 'client'))
    )
''')

# Insert sample data into users
cursor.execute('''
    INSERT OR IGNORE INTO users (username, password, role)
    VALUES ('admin', 'admin123', 'admin')
''')
cursor.execute('''
    INSERT OR IGNORE INTO users (username, password, role)
    VALUES ('staff', 'staff123', 'staff')
''')
cursor.execute('''
    INSERT OR IGNORE INTO users (username, password, role)
    VALUES ('client', 'client123', 'client')
''')

# Add trigger to update room status to "En nettoyage" after reservation ends
cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_room_status_after_reservation
    AFTER UPDATE OF statut ON reservations
    WHEN NEW.statut = 'Terminée'
    BEGIN
        UPDATE chambres
        SET statut = 'En nettoyage'
        WHERE id_chambre = (SELECT id_chambre FROM reservations WHERE id_reservation = NEW.id_reservation);
    END;
''')

# Commit changes and close connection
conn.commit()
conn.close()
print("Database and tables created successfully.")