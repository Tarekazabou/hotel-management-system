# app.py (Corrected - Includes view_services and other Phase 2 updates)

import sqlite3
from datetime import datetime, timedelta, date
from functools import wraps
from flask import (Flask, abort, flash, jsonify, redirect,
                   render_template, request, session, url_for)
import os
import math # For ceiling calculation

app = Flask(__name__, template_folder='templates')

# --- Configuration ---
# IMPORTANT: Set a strong, unique secret key! Use environment variables in production.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback - change this default key very securely')
app.permanent_session_lifetime = timedelta(hours=8) # Example session duration

# --- Context Processor ---
@app.context_processor
def inject_now():
    """Makes 'now' available in all templates for the current UTC time."""
    return {'now': datetime.utcnow}

# --- Database Connection Helper ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect('gesthotel.db')
    conn.row_factory = sqlite3.Row # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON") # Ensure FK constraints are active
    return conn

# --- Authentication & Authorization Decorators ---
def login_required(f):
    """Redirects to login if user is not authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role):
    """Restricts access based on user role."""
    def decorator(f):
        @wraps(f)
        @login_required # User must be logged in first
        def decorated_function(*args, **kwargs):
            user_role = session.get('role')
            allowed = False
            # Check if the user's role meets the requirement (includes inheritance)
            if user_role == required_role:
                allowed = True
            elif user_role == 'admin' and required_role in ['staff', 'client']:
                allowed = True
            elif user_role == 'staff' and required_role == 'client':
                 allowed = True

            if not allowed:
                # Show an unauthorized page if permission denied
                return render_template('unauthorized.html', required_role=required_role), 403
            # If allowed, proceed with the original function
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Helper Functions ---
def calculate_applied_price(base_price, reduction_percentage):
    """Calculates price after percentage reduction, ensuring valid inputs."""
    try:
        base = float(base_price)
        reduction = float(reduction_percentage)
        discount = max(0.0, min(100.0, reduction)) # Clamp reduction between 0 and 100
        applied = base * (1 - discount / 100.0)
        return round(applied, 2)
    except (ValueError, TypeError):
        # Return base price or raise an error if inputs are invalid
        print(f"Warning: Invalid input for price calculation: base={base_price}, reduction={reduction_percentage}")
        return base_price # Fallback to base price

def get_applicable_tariffs(db_conn, client_status=None, booking_dates=None):
     """Fetches tariffs potentially applicable (simplified logic)."""
     # This logic should be expanded based on actual business rules (season, day, etc.)
     tariffs = db_conn.execute('SELECT * FROM tarifs ORDER BY nom_tarif').fetchall()
     applicable = [t for t in tariffs if t['condition_application'] == 'None' or t['nom_tarif'] == 'Standard']
     if client_status == 'VIP':
         vip_tariffs = [t for t in tariffs if 'VIP' in t['condition_application']]
         applicable.extend(vip_tariffs)
     # Remove duplicates
     unique_tariffs = {t['id_tarif']: t for t in applicable}
     return list(unique_tariffs.values())


# --- Routes ---

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('home')) # Already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password') # WARNING: Plain text password check!
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('login.html')

        conn = get_db_connection()
        user = conn.execute('SELECT id_user, username, role FROM users WHERE username = ? AND password = ?',
                            (username, password)).fetchone()
        conn.close()

        if user:
            session.permanent = True
            session['user_id'] = user['id_user']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            next_url = request.args.get('next')
            if next_url: return redirect(next_url)
            if user['role'] == 'admin': return redirect(url_for('dashboard'))
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Core Application Routes
@app.route('/')
@login_required
def home():
    if session.get('role') == 'admin': return redirect(url_for('dashboard'))
    return render_template('home.html')

@app.route('/dashboard')
@require_role('admin')
def dashboard():
    try:
        conn = get_db_connection()
        today = datetime.now().strftime('%Y-%m-%d')
        total_rooms_res = conn.execute('SELECT COUNT(*) as total FROM chambres').fetchone()
        total_rooms = total_rooms_res['total'] if total_rooms_res else 0
        occupied_rooms_res = conn.execute('''SELECT COUNT(DISTINCT id_chambre) as occupied FROM reservations
                                            WHERE statut = 'Confirmée' AND date(date_debut) <= date(?) AND date(date_fin) > date(?)''', (today, today)).fetchone()
        occupied_rooms = occupied_rooms_res['occupied'] if occupied_rooms_res else 0
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0
        avg_rating_res = conn.execute('SELECT AVG(note) as avg_note FROM avis WHERE moderated = 1').fetchone()
        avg_rating = avg_rating_res['avg_note'] if avg_rating_res and avg_rating_res['avg_note'] is not None else 0
        upcoming_checkins = conn.execute(''' SELECT r.id_reservation, r.date_debut, c.nom, c.prenom, ch.numero_chambre
                                             FROM reservations r JOIN clients c ON r.id_client = c.id_client JOIN chambres ch ON r.id_chambre = ch.id_chambre
                                             WHERE r.statut = 'Confirmée' AND date(r.date_debut) BETWEEN date(?) AND date(?, '+7 days')
                                             ORDER BY r.date_debut ASC LIMIT 5 ''', (today, today)).fetchall()
        conn.close()
        return render_template('dashboard.html', occupancy_rate=round(occupancy_rate, 2), average_rating=round(avg_rating, 2), upcoming_checkins=upcoming_checkins)
    except Exception as e:
        flash(f'Error loading dashboard data: {str(e)}', 'danger')
        return render_template('dashboard.html', occupancy_rate=0, average_rating=0, upcoming_checkins=[], error=str(e))

# --- Chambres (Rooms) ---
@app.route('/chambres')
@login_required
def view_chambres():
    # Renders the list of rooms. Accessible by logged-in users.
    try:
        conn = get_db_connection()
        chambres = conn.execute('SELECT * FROM chambres ORDER BY numero_chambre').fetchall()
        conn.close()
        # Renders templates/chambres.html
        return render_template('chambres.html', chambres=chambres)
    except Exception as e:
        flash(f'Error fetching rooms: {str(e)}', 'danger')
        return render_template('chambres.html', chambres=[])

@app.route('/chambres/add', methods=['POST'])
@require_role('admin')
def add_chambre():
    # Handles the form submission for adding a new room. Admin only.
    numero = request.form.get('numero_chambre')
    type_chambre = request.form.get('type_chambre')
    prix_base = request.form.get('prix_nuit_base')
    statut = request.form.get('statut')
    if not all([numero, type_chambre, prix_base, statut]):
        flash('All room fields are required.', 'warning')
        return redirect(url_for('view_chambres'))
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO chambres (numero_chambre, type_chambre, prix_nuit_base, statut) VALUES (?, ?, ?, ?)',
                     (numero, type_chambre, float(prix_base), statut))
        conn.commit()
        conn.close()
        flash(f'Room {numero} added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Room number {numero} already exists or invalid type/status.', 'danger')
    except ValueError:
        flash('Invalid base price format. Please enter a number.', 'danger')
    except Exception as e:
        flash(f'Error adding room: {str(e)}', 'danger')
    return redirect(url_for('view_chambres'))

@app.route('/chambres/<int:id>/edit', methods=['GET', 'POST'])
@require_role('admin')
def edit_chambre(id):
    # Shows the edit form (GET) or processes the update (POST). Admin only.
    conn = get_db_connection()
    # Fetch the room first for both GET and potential POST failure
    chambre = conn.execute('SELECT * FROM chambres WHERE id_chambre = ?', (id,)).fetchone()
    if not chambre:
        conn.close()
        abort(404) # Room not found

    if request.method == 'POST':
        numero = request.form.get('numero_chambre')
        type_chambre = request.form.get('type_chambre')
        prix_base = request.form.get('prix_nuit_base')
        statut = request.form.get('statut')
        if not all([numero, type_chambre, prix_base, statut]):
            flash('All fields are required.', 'warning')
            conn.close()
            # Renders templates/chambre_edit.html on validation failure
            return render_template('chambre_edit.html', chambre=chambre)
        try:
            conn.execute('''UPDATE chambres SET numero_chambre = ?, type_chambre = ?,
                            prix_nuit_base = ?, statut = ? WHERE id_chambre = ?''',
                         (numero, type_chambre, float(prix_base), statut, id))
            conn.commit()
            flash(f'Room {numero} updated successfully!', 'success')
            conn.close()
            return redirect(url_for('view_chambres'))
        except sqlite3.IntegrityError:
            conn.rollback()
            flash(f'Update failed. Room number {numero} might already exist or invalid type/status.', 'danger')
        except ValueError:
            conn.rollback()
            flash('Invalid base price format.', 'danger')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating room: {str(e)}', 'danger')
        # If POST fails after DB attempts, close connection and render form again
        conn.close()
        # Renders templates/chambre_edit.html on DB error
        return render_template('chambre_edit.html', chambre=chambre)
    else: # GET Request
        conn.close()
        # Renders templates/chambre_edit.html for viewing/editing
        return render_template('chambre_edit.html', chambre=chambre)

@app.route('/chambres/<int:id>/delete', methods=['POST'])
@require_role('admin')
def delete_chambre(id):
    # Handles the deletion of a room. Admin only.
    try:
        conn = get_db_connection()
        # Attempt deletion - FOREIGN KEY constraint should prevent if reserved
        result = conn.execute('DELETE FROM chambres WHERE id_chambre = ?', (id,))
        conn.commit()
        conn.close()
        if result.rowcount > 0:
            flash(f'Room {id} deleted successfully.', 'success')
        else:
            flash(f'Room {id} not found.', 'warning')
    except sqlite3.IntegrityError as e:
         # Catches the RESTRICT constraint from reservations table
         flash(f'Cannot delete room {id}: It has existing reservations linked.', 'danger')
    except Exception as e:
        flash(f'Error deleting room {id}: {str(e)}', 'danger')
    return redirect(url_for('view_chambres'))

# --- Clients ---
@app.route('/clients')
@require_role('staff')
def view_clients():
    # Renders the list of clients. Staff/Admin access.
    try:
        conn = get_db_connection()
        clients = conn.execute('SELECT * FROM clients ORDER BY nom, prenom').fetchall()
        conn.close()
        # Renders templates/clients.html
        return render_template('clients.html', clients=clients)
    except Exception as e:
        flash(f'Error fetching clients: {str(e)}', 'danger')
        return render_template('clients.html', clients=[])

@app.route('/clients/add', methods=['POST'])
@require_role('staff')
def add_client():
    # Handles form submission for adding a client. Staff/Admin access.
    nom = request.form.get('nom')
    prenom = request.form.get('prenom')
    email = request.form.get('email')
    telephone = request.form.get('telephone')
    adresse = request.form.get('adresse')
    statut_fidelite = request.form.get('statut_fidelite', 'Standard')
    if not nom or not prenom or not email:
        flash('First name, last name, and email are required.', 'warning')
        return redirect(url_for('view_clients'))
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO clients (nom, prenom, telephone, email, adresse, statut_fidelite) VALUES (?, ?, ?, ?, ?, ?)',
                     (nom, prenom, telephone, email, adresse, statut_fidelite))
        conn.commit()
        conn.close()
        flash(f'Client {prenom} {nom} added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Client with email {email} already exists or invalid loyalty status.', 'danger')
    except Exception as e:
        flash(f'Error adding client: {str(e)}', 'danger')
    return redirect(url_for('view_clients'))

@app.route('/clients/<int:id>/edit', methods=['GET', 'POST'])
@require_role('staff')
def edit_client(id):
    # Shows edit form (GET) or processes update (POST). Staff/Admin access.
    conn = get_db_connection()
    client = conn.execute('SELECT * FROM clients WHERE id_client = ?', (id,)).fetchone()
    if not client:
        conn.close()
        abort(404)

    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        email = request.form.get('email')
        telephone = request.form.get('telephone')
        adresse = request.form.get('adresse')
        statut_fidelite = request.form.get('statut_fidelite')
        if not nom or not prenom or not email or not statut_fidelite:
            flash('First name, last name, email, and loyalty status are required.', 'warning')
            conn.close()
            # Renders templates/client_edit.html on validation failure
            return render_template('client_edit.html', client=client)
        try:
            conn.execute('''UPDATE clients SET nom = ?, prenom = ?, telephone = ?, email = ?,
                            adresse = ?, statut_fidelite = ? WHERE id_client = ?''',
                         (nom, prenom, telephone, email, adresse, statut_fidelite, id))
            conn.commit()
            flash(f'Client {prenom} {nom} updated successfully!', 'success')
            conn.close()
            return redirect(url_for('view_clients'))
        except sqlite3.IntegrityError:
            conn.rollback()
            flash(f'Update failed. Email {email} might already exist or invalid loyalty status.', 'danger')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating client: {str(e)}', 'danger')
        conn.close()
        # Renders templates/client_edit.html on DB error
        return render_template('client_edit.html', client=client)
    else: # GET
        conn.close()
        # Renders templates/client_edit.html for viewing/editing
        return render_template('client_edit.html', client=client)

@app.route('/clients/<int:id>/delete', methods=['POST'])
@require_role('admin')
def delete_client(id):
    # Handles deletion. Admin only. FK constraints will prevent deletion if related data exists.
    try:
        conn = get_db_connection()
        result = conn.execute('DELETE FROM clients WHERE id_client = ?', (id,))
        conn.commit()
        conn.close()
        if result.rowcount > 0:
            flash(f'Client {id} deleted successfully.', 'success')
        else:
            flash(f'Client {id} not found.', 'warning')
    except sqlite3.IntegrityError as e:
         # This catches FK violations (ON DELETE CASCADE for avis might succeed, but RESTRICT on reservations might fail)
         flash(f'Cannot delete client {id}: They have existing related data (like reservations). Error: {e}', 'danger')
    except Exception as e:
        flash(f'Error deleting client {id}: {str(e)}', 'danger')
    return redirect(url_for('view_clients'))

# --- Tarifs (Pricing Tiers) ---
@app.route('/tarifs')
@require_role('staff')
def view_tarifs():
    # Renders the list of tariffs. Staff/Admin access.
    try:
        conn = get_db_connection()
        tarifs = conn.execute('SELECT * FROM tarifs ORDER BY nom_tarif').fetchall()
        conn.close()
        # Renders templates/tarifs.html
        return render_template('tarifs.html', tarifs=tarifs)
    except Exception as e:
        flash(f'Error fetching tariffs: {str(e)}', 'danger')
        return render_template('tarifs.html', tarifs=[])

@app.route('/tarifs/add', methods=['POST'])
@require_role('admin')
def add_tarif():
    # Handles form submission for adding a tariff. Admin only.
    nom = request.form.get('nom_tarif')
    description = request.form.get('description')
    reduction = request.form.get('reduction_pourcentage', 0.0)
    condition = request.form.get('condition_application')
    if not nom:
        flash('Tariff name is required.', 'warning')
        return redirect(url_for('view_tarifs'))
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO tarifs (nom_tarif, description, reduction_pourcentage, condition_application) VALUES (?, ?, ?, ?)',
                     (nom, description, float(reduction), condition))
        conn.commit()
        conn.close()
        flash(f'Tariff "{nom}" added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Tariff name "{nom}" already exists.', 'danger')
    except ValueError:
        flash('Invalid reduction percentage format. Must be a number.', 'danger')
    except Exception as e:
        flash(f'Error adding tariff: {str(e)}', 'danger')
    return redirect(url_for('view_tarifs'))

@app.route('/tarifs/<int:id>/edit', methods=['GET', 'POST'])
@require_role('admin')
def edit_tarif(id):
    # Shows edit form (GET) or processes update (POST). Admin only.
    conn = get_db_connection()
    tarif = conn.execute('SELECT * FROM tarifs WHERE id_tarif = ?', (id,)).fetchone()
    if not tarif:
        conn.close()
        abort(404)

    if request.method == 'POST':
        nom = request.form.get('nom_tarif')
        description = request.form.get('description')
        reduction = request.form.get('reduction_pourcentage', 0.0)
        condition = request.form.get('condition_application')
        if not nom:
             flash('Tariff name is required.', 'warning')
             conn.close()
             # Renders templates/tarif_edit.html on validation failure
             return render_template('tarif_edit.html', tarif=tarif)
        try:
             conn.execute('''UPDATE tarifs SET nom_tarif = ?, description = ?,
                             reduction_pourcentage = ?, condition_application = ?
                             WHERE id_tarif = ?''',
                          (nom, description, float(reduction), condition, id))
             conn.commit()
             flash(f'Tariff "{nom}" updated successfully!', 'success')
             conn.close()
             return redirect(url_for('view_tarifs'))
        except sqlite3.IntegrityError:
             conn.rollback()
             flash(f'Update failed. Tariff name "{nom}" might already exist.', 'danger')
        except ValueError:
             conn.rollback()
             flash('Invalid reduction percentage format.', 'danger')
        except Exception as e:
             conn.rollback()
             flash(f'Error updating tariff: {str(e)}', 'danger')
        conn.close()
        # Renders templates/tarif_edit.html on DB error
        return render_template('tarif_edit.html', tarif=tarif)
    else: # GET
        conn.close()
        # Renders templates/tarif_edit.html for viewing/editing
        return render_template('tarif_edit.html', tarif=tarif)

@app.route('/tarifs/<int:id>/delete', methods=['POST'])
@require_role('admin')
def delete_tarif(id):
    # Handles deletion. Admin only. FK constraints prevent if used in reservations.
    try:
        conn = get_db_connection()
        result = conn.execute('DELETE FROM tarifs WHERE id_tarif = ?', (id,))
        conn.commit()
        conn.close()
        if result.rowcount > 0:
            flash(f'Tariff {id} deleted successfully.', 'success')
        else:
            flash(f'Tariff {id} not found.', 'warning')
    except sqlite3.IntegrityError as e:
         flash(f'Cannot delete tariff {id}: It is used in existing reservations.', 'danger')
    except Exception as e:
        flash(f'Error deleting tariff {id}: {str(e)}', 'danger')
    return redirect(url_for('view_tarifs'))

# --- Services ---
# **** THIS IS THE FUNCTION THAT WAS MISSING OR CAUSING THE ERROR ****
@app.route('/services')
@login_required
def view_services():
    # Renders the list of services. Accessible by logged-in users.
    try:
        conn = get_db_connection()
        services = conn.execute('SELECT * FROM services ORDER BY nom_service').fetchall()
        conn.close()
        # Renders templates/services.html
        return render_template('services.html', services=services)
    except Exception as e:
        flash(f'Error fetching services: {str(e)}', 'danger')
        return render_template('services.html', services=[])
# **** END OF view_services FUNCTION ****

@app.route('/services/add', methods=['POST'])
@require_role('admin')
def add_service():
    # Handles form submission for adding a service. Admin only.
    nom = request.form.get('nom_service')
    desc = request.form.get('description')
    prix = request.form.get('prix')
    disp = request.form.get('disponibilite')
    if not all([nom, prix, disp]):
        flash('Service Name, Price, and Availability are required.', 'warning')
        return redirect(url_for('view_services'))
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO services (nom_service, description, prix, disponibilite) VALUES (?, ?, ?, ?)',
                     (nom, desc, float(prix), disp))
        conn.commit()
        conn.close()
        flash(f'Service "{nom}" added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Service "{nom}" already exists or invalid availability.', 'danger')
    except ValueError:
        flash('Invalid price format. Please enter a number.', 'danger')
    except Exception as e:
        flash(f'Error adding service: {str(e)}', 'danger')
    return redirect(url_for('view_services'))

# Add Edit/Delete routes for Services similar to Tarifs/Chambres if required by cahier des charges

# --- Reservations ---
@app.route('/reservations')
@require_role('staff')
def view_reservations():
    # Renders the list of reservations. Staff/Admin access.
    try:
        conn = get_db_connection()
        today = datetime.now().strftime('%Y-%m-%d')
        # Auto-update completed reservations
        conn.execute("UPDATE reservations SET statut = 'Terminée' WHERE statut = 'Confirmée' AND date(date_fin) < date(?)", (today,))
        conn.commit()

        reservations = conn.execute('''
            SELECT r.*, c.nom, c.prenom, c.email, c.statut_fidelite,
                   ch.numero_chambre, ch.type_chambre, t.nom_tarif
            FROM reservations r
            JOIN clients c ON r.id_client = c.id_client
            JOIN chambres ch ON r.id_chambre = ch.id_chambre
            JOIN tarifs t ON r.id_tarif = t.id_tarif
            ORDER BY r.date_debut DESC, r.id_reservation DESC
        ''').fetchall()

        clients = conn.execute('SELECT id_client, nom, prenom, email, statut_fidelite FROM clients ORDER BY nom, prenom').fetchall()
        # Fetch rooms available (not Occupé today)
        chambres = conn.execute("SELECT id_chambre, numero_chambre, type_chambre, prix_nuit_base FROM chambres WHERE statut != 'Occupé' ORDER BY numero_chambre").fetchall()
        # Fetch all tariffs for the dropdown
        tarifs = conn.execute('SELECT * FROM tarifs ORDER BY nom_tarif').fetchall()

        conn.close()
        # Renders templates/reservations.html
        return render_template('reservations.html', reservations=reservations, clients=clients, chambres=chambres, tarifs=tarifs)
    except Exception as e:
        flash(f'Error fetching reservations: {str(e)}', 'danger')
        return render_template('reservations.html', reservations=[], clients=[], chambres=[], tarifs=[])

@app.route('/reservations/add', methods=['POST'])
@require_role('staff')
def add_reservation():
    # Handles form submission for adding a reservation. Staff/Admin access.
    id_client = request.form.get('id_client')
    id_chambre = request.form.get('id_chambre')
    id_tarif = request.form.get('id_tarif')
    date_debut_str = request.form.get('date_debut')
    date_fin_str = request.form.get('date_fin')

    if not all([id_client, id_chambre, id_tarif, date_debut_str, date_fin_str]):
        flash('Client, Room, Tariff, Start Date, and End Date are required.', 'warning')
        return redirect(url_for('view_reservations'))

    try:
        date_debut = date.fromisoformat(date_debut_str)
        date_fin = date.fromisoformat(date_fin_str)
        today = date.today()
        if date_debut < today:
             flash('Check-in date cannot be in the past.', 'warning')
             return redirect(url_for('view_reservations'))
        if date_debut >= date_fin:
            flash('Check-out date must be after check-in date.', 'warning')
            return redirect(url_for('view_reservations'))

        conn = get_db_connection()
        # Check for booking conflicts for the chosen room
        conflict = conn.execute('''
            SELECT 1 FROM reservations WHERE id_chambre = ? AND statut = 'Confirmée'
            AND date(date_debut) < date(?) AND date(date_fin) > date(?) LIMIT 1
        ''', (id_chambre, date_fin_str, date_debut_str)).fetchone()
        if conflict:
            conn.close()
            flash(f'Room conflict: This room is already booked for the selected dates.', 'danger')
            return redirect(url_for('view_reservations'))

        # Fetch data needed for price calculation
        chambre = conn.execute('SELECT prix_nuit_base FROM chambres WHERE id_chambre = ?', (id_chambre,)).fetchone()
        tarif = conn.execute('SELECT reduction_pourcentage FROM tarifs WHERE id_tarif = ?', (id_tarif,)).fetchone()

        if not chambre or not tarif:
            conn.close()
            flash('Invalid room or tariff selected.', 'danger')
            return redirect(url_for('view_reservations'))

        # --- Apply Tariff Logic ---
        # Add checks here later if tariff application has conditions (e.g., VIP status)
        prix_applique = calculate_applied_price(chambre['prix_nuit_base'], tarif['reduction_pourcentage'])

        # Insert the reservation
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO reservations
                          (id_client, id_chambre, id_tarif, date_debut, date_fin, prix_nuit_applique, statut)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (id_client, id_chambre, id_tarif, date_debut_str, date_fin_str, prix_applique, 'Confirmée'))

        # Update room status if reservation starts today
        if date_debut == today:
             cursor.execute('UPDATE chambres SET statut = ? WHERE id_chambre = ?', ('Occupé', id_chambre))

        conn.commit()
        conn.close()
        flash(f'Reservation added successfully! Applied price/night: {prix_applique:.2f} €', 'success')

    except ValueError:
        flash('Invalid date format or numeric value.', 'danger')
    except sqlite3.IntegrityError as e:
        flash(f'Database integrity error: {e}. Ensure valid IDs.', 'danger')
    except Exception as e:
        flash(f'Error adding reservation: {str(e)}', 'danger')

    return redirect(url_for('view_reservations'))

@app.route('/reservations/<int:id>/cancel', methods=['POST'])
@require_role('staff')
def cancel_reservation(id):
    # Handles reservation cancellation. Staff/Admin access.
    try:
        conn = get_db_connection()
        reservation = conn.execute('SELECT id_chambre, statut, date_debut FROM reservations WHERE id_reservation = ?', (id,)).fetchone()
        if not reservation:
            conn.close(); flash('Reservation not found.', 'warning'); return redirect(url_for('view_reservations'))
        if reservation['statut'] != 'Confirmée':
             conn.close(); flash(f'Reservation {id} is already {reservation["statut"]} and cannot be cancelled.', 'warning'); return redirect(url_for('view_reservations'))
        # Check if cancellation is allowed (before check-in date)
        # if date.fromisoformat(reservation['date_debut']) <= date.today():
        #      conn.close(); flash('Cannot cancel reservation on or after check-in date.', 'warning'); return redirect(url_for('view_reservations'))

        id_chambre = reservation['id_chambre']
        conn.execute('UPDATE reservations SET statut = ? WHERE id_reservation = ?', ('Annulée', id))

        # Check if room should become 'Libre' (no other *current* confirmed bookings)
        today_str = datetime.now().strftime('%Y-%m-%d')
        other_booking = conn.execute('''SELECT 1 FROM reservations WHERE id_chambre = ? AND id_reservation != ? AND statut = 'Confirmée'
                                        AND date(date_debut) <= date(?) AND date(date_fin) > date(?) LIMIT 1''',
                                     (id_chambre, id, today_str, today_str)).fetchone()
        if not other_booking:
             # Only set to Libre if not currently 'En nettoyage'
             conn.execute("UPDATE chambres SET statut = 'Libre' WHERE id_chambre = ? AND statut != 'En nettoyage'", (id_chambre,))

        conn.commit()
        conn.close()
        flash(f'Reservation {id} cancelled successfully.', 'success')
    except Exception as e:
        flash(f'Error cancelling reservation {id}: {str(e)}', 'danger')
    return redirect(url_for('view_reservations'))

# Add route for adding services to reservation if needed
# @app.route('/reservations/<int:id>/add_service', methods=['POST']) ...

# --- Consommations (Utilities) ---
@app.route('/consommations')
@require_role('staff')
def view_consommations():
    # Renders the list of consumptions. Staff/Admin access.
    try:
        conn = get_db_connection()
        consommations = conn.execute('''
            SELECT co.*, ch.numero_chambre
            FROM consommations co
            JOIN chambres ch ON co.id_chambre = ch.id_chambre
            ORDER BY co.date_releve DESC, co.id_consommation DESC
        ''').fetchall()
        chambres = conn.execute('SELECT id_chambre, numero_chambre FROM chambres ORDER BY numero_chambre').fetchall()
        conn.close()
        # Renders templates/consommations.html
        return render_template('consommations.html', consommations=consommations, chambres=chambres)
    except Exception as e:
        flash(f'Error fetching consumptions: {str(e)}', 'danger')
        return render_template('consommations.html', consommations=[], chambres=[])

@app.route('/consommations/add', methods=['POST'])
@require_role('staff')
def add_consommation():
    # Handles form submission for adding consumption. Staff/Admin access.
    id_chambre = request.form.get('id_chambre')
    type_conso = request.form.get('type_consommation')
    date_releve = request.form.get('date_releve')
    valeur = request.form.get('valeur')
    unite = request.form.get('unite')
    cout_unitaire = request.form.get('cout_unitaire')
    if not all([id_chambre, type_conso, date_releve, valeur, unite, cout_unitaire]):
        flash('All consumption fields are required.', 'warning')
        return redirect(url_for('view_consommations'))

    # Try to find active reservation for linking
    id_reservation = None
    try:
        conn = get_db_connection()
        res = conn.execute('''SELECT id_reservation FROM reservations WHERE id_chambre = ? AND statut = 'Confirmée'
                              AND date(?) BETWEEN date(date_debut) AND date(date_fin, '-1 day')
                              ORDER BY id_reservation DESC LIMIT 1''', (id_chambre, date_releve)).fetchone()
        if res: id_reservation = res['id_reservation']

        conn.execute('''INSERT INTO consommations
                        (id_chambre, id_reservation, type_consommation, date_releve, valeur, unite, cout_unitaire)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (id_chambre, id_reservation, type_conso, date_releve, float(valeur), unite, float(cout_unitaire)))
        conn.commit()
        flash('Consumption record added successfully!', 'success')
    except ValueError:
        flash('Invalid numeric value for consumption or cost.', 'danger')
    except sqlite3.IntegrityError as e:
        flash(f'Database error: {e}. Check types/constraints.', 'danger')
    except Exception as e:
        flash(f'Error adding consumption: {str(e)}', 'danger')
    finally:
        if conn: conn.close() # Ensure connection is closed
    return redirect(url_for('view_consommations'))

# Add Edit/Delete routes for Consommations if needed

# --- Factures (Invoices) ---
@app.route('/factures')
@require_role('staff')
def view_factures():
    # Renders the list of invoices. Staff/Admin access.
    try:
        conn = get_db_connection()
        factures = conn.execute('''
            SELECT f.*, r.date_debut, r.date_fin,
                   c.nom || ' ' || c.prenom AS client_name, c.email,
                   ch.numero_chambre
            FROM factures f
            JOIN reservations r ON f.id_reservation = r.id_reservation
            JOIN clients c ON r.id_client = c.id_client
            JOIN chambres ch ON r.id_chambre = ch.id_chambre
            ORDER BY f.date_emission DESC, f.id_facture DESC
        ''').fetchall()
        reservations_needing_invoice = conn.execute('''
            SELECT r.id_reservation, r.date_debut, r.date_fin, c.nom || ' ' || c.prenom AS client_name, ch.numero_chambre
            FROM reservations r JOIN clients c ON r.id_client = c.id_client JOIN chambres ch ON r.id_chambre = ch.id_chambre
            WHERE r.statut IN ('Confirmée', 'Terminée')
            AND r.id_reservation NOT IN (SELECT id_reservation FROM factures)
            ORDER BY r.date_fin DESC, r.id_reservation DESC
        ''').fetchall()
        conn.close()
        # Renders templates/factures.html
        return render_template('factures.html', factures=factures, reservations_needing_invoice=reservations_needing_invoice)
    except Exception as e:
        flash(f'Error fetching invoices: {str(e)}', 'danger')
        return render_template('factures.html', factures=[], reservations_needing_invoice=[])

@app.route('/factures/generate', methods=['POST'])
@require_role('staff')
def generate_facture():
    # Handles invoice generation for a selected reservation. Staff/Admin access.
    id_reservation = request.form.get('id_reservation')
    if not id_reservation:
        flash('Please select a reservation to generate an invoice.', 'warning')
        return redirect(url_for('view_factures'))
    try:
        conn = get_db_connection()
        # Check if invoice already exists for this reservation
        existing = conn.execute('SELECT 1 FROM factures WHERE id_reservation = ?', (id_reservation,)).fetchone()
        if existing:
             conn.close(); flash(f'Invoice already exists for reservation {id_reservation}.', 'warning'); return redirect(url_for('view_factures'))

        # Get reservation details needed for calculation
        reservation = conn.execute('''SELECT id_chambre, date_debut, date_fin, prix_nuit_applique, statut
                                     FROM reservations WHERE id_reservation = ?''', (id_reservation,)).fetchone()
        if not reservation or reservation['statut'] == 'Annulée':
            conn.close(); flash('Cannot generate invoice: Reservation not found or is cancelled.', 'warning'); return redirect(url_for('view_factures'))

        # --- Calculate Invoice Components ---
        date_debut = date.fromisoformat(reservation['date_debut'])
        date_fin = date.fromisoformat(reservation['date_fin'])
        nights = max(1, (date_fin - date_debut).days)
        montant_chambre = nights * reservation['prix_nuit_applique']

        # Calculate total cost of services linked to this reservation
        services_res = conn.execute('SELECT SUM(s.prix * rs.quantite) as total FROM reservation_services rs JOIN services s ON rs.id_service = s.id_service WHERE rs.id_reservation = ?', (id_reservation,)).fetchone()
        montant_services = services_res['total'] if services_res and services_res['total'] is not None else 0

        # Calculate total cost of consumptions during the reservation period
        consommations_res = conn.execute('''SELECT SUM(co.valeur * co.cout_unitaire) as total FROM consommations co
                                           WHERE co.id_chambre = ? AND date(co.date_releve) >= date(?) AND date(co.date_releve) < date(?)''',
                                        (reservation['id_chambre'], reservation['date_debut'], reservation['date_fin'])).fetchone()
        montant_consommations = consommations_res['total'] if consommations_res and consommations_res['total'] is not None else 0

        montant_total = round(montant_chambre + montant_services + montant_consommations, 2)
        today_str = datetime.now().strftime('%Y-%m-%d')

        # Insert the new invoice record
        conn.execute('''INSERT INTO factures (id_reservation, montant_chambre, montant_services, montant_consommations, montant_total, date_emission, statut)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (id_reservation, montant_chambre, montant_services, montant_consommations, montant_total, today_str, 'Non payée'))
        conn.commit()
        flash(f'Invoice generated for reservation {id_reservation}. Total: {montant_total:.2f} €', 'success')

    except ValueError:
        flash('Invalid date or number format during calculation.', 'danger')
    except sqlite3.Error as e:
         flash(f'Database error generating invoice: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Error generating invoice: {str(e)}', 'danger')
    finally:
        if conn: conn.close()
    return redirect(url_for('view_factures'))

@app.route('/factures/<int:id>/update', methods=['POST'])
@require_role('staff')
def update_facture(id):
    # Handles updating invoice status and payment method. Staff/Admin access.
    new_status = request.form.get('statut')
    mode_paiement = request.form.get('mode_paiement')
    valid_statuses = ['Non payée', 'Payée', 'Partiellement payée']
    valid_payments = ['Carte', 'Espèces', 'Virement', 'Chèque', ''] # Allow empty

    if new_status not in valid_statuses: flash('Invalid status selected.', 'warning'); return redirect(url_for('view_factures'))
    if mode_paiement not in valid_payments: flash('Invalid payment method selected.', 'warning'); return redirect(url_for('view_factures'))
    if new_status == 'Payée' and not mode_paiement: flash('Payment method required when marking invoice as Paid.', 'warning'); return redirect(url_for('view_factures'))
    if new_status == 'Non payée': mode_paiement = None # Clear payment method if unpaid

    try:
        conn = get_db_connection()
        result = conn.execute('UPDATE factures SET statut = ?, mode_paiement = ? WHERE id_facture = ?',
                              (new_status, mode_paiement if mode_paiement else None, id))
        conn.commit()
        conn.close()
        if result.rowcount > 0: flash(f'Invoice #{id} status updated to {new_status}.', 'success')
        else: flash(f'Invoice #{id} not found or no change made.', 'warning')
    except Exception as e:
        flash(f'Error updating invoice #{id}: {str(e)}', 'danger')
    return redirect(url_for('view_factures'))


# --- Avis (Reviews) ---
@app.route('/avis')
@login_required
def view_avis():
    # Renders approved reviews, pending reviews (for admin), and review form (for clients).
    conn = get_db_connection()
    try:
        approved_avis = conn.execute('SELECT a.*, c.nom || " " || c.prenom AS client_name FROM avis a JOIN clients c ON a.id_client = c.id_client WHERE a.moderated = 1 ORDER BY a.date_avis DESC, a.id_avis DESC').fetchall()
        pending_avis = []
        client_reservations_for_review = []

        if session.get('role') == 'admin':
            pending_avis = conn.execute('SELECT a.*, c.nom || " " || c.prenom AS client_name, a.id_reservation FROM avis a JOIN clients c ON a.id_client = c.id_client WHERE a.moderated = 0 ORDER BY a.date_avis DESC, a.id_avis DESC').fetchall()

        # Fetch potential reservations the client can review
        if session.get('role') == 'client':
             client_id = session.get('user_id') # Assumes user_id = client_id
             if client_id:
                 client_reservations_for_review = conn.execute('''
                     SELECT r.id_reservation, r.date_fin, ch.numero_chambre
                     FROM reservations r JOIN chambres ch ON r.id_chambre = ch.id_chambre
                     WHERE r.id_client = ? AND r.statut = 'Terminée'
                     AND r.id_reservation NOT IN (SELECT id_reservation FROM avis WHERE id_client = ?)
                     ORDER BY r.date_fin DESC
                 ''', (client_id, client_id)).fetchall()
    except Exception as e:
        flash(f'Error fetching reviews: {str(e)}', 'danger')
        approved_avis, pending_avis, client_reservations_for_review = [], [], []
    finally:
        if conn: conn.close()

    # Renders templates/avis.html
    return render_template('avis.html', approved_avis=approved_avis, pending_avis=pending_avis, client_reservations=client_reservations_for_review)

@app.route('/avis/add', methods=['POST'])
@require_role('client') # Or adjust role as needed
def add_avis():
    # Handles review submission form. Client role access (example).
    client_id = session.get('user_id')
    id_reservation = request.form.get('id_reservation')
    note = request.form.get('note')
    commentaire = request.form.get('commentaire')

    if not all([client_id, id_reservation, note, commentaire]):
        flash('Reservation, rating, and comment are required.', 'warning'); return redirect(url_for('view_avis'))

    try:
        note_int = int(note)
        if not 1 <= note_int <= 5:
            flash('Rating must be between 1 and 5.', 'warning'); return redirect(url_for('view_avis'))

        conn = get_db_connection()
        # Verify client owns this completed reservation and hasn't reviewed it yet
        check = conn.execute("SELECT 1 FROM reservations WHERE id_reservation = ? AND id_client = ? AND statut = 'Terminée'", (id_reservation, client_id)).fetchone()
        if not check:
            conn.close(); flash('Cannot review: Reservation not found, not completed, or does not belong to you.', 'warning'); return redirect(url_for('view_avis'))

        today = datetime.now().strftime('%Y-%m-%d')
        conn.execute('INSERT INTO avis (id_client, id_reservation, note, commentaire, date_avis, moderated) VALUES (?, ?, ?, ?, ?, 0)',
                     (client_id, id_reservation, note_int, commentaire, today))
        conn.commit()
        conn.close()
        flash('Review submitted for moderation. Thank you!', 'success')
    except ValueError:
        flash('Invalid rating value.', 'danger')
    except sqlite3.IntegrityError: # Catches UNIQUE constraint on id_reservation
        flash('A review has already been submitted for this reservation.', 'danger')
    except Exception as e:
        flash(f'Error submitting review: {str(e)}', 'danger')
    finally:
        if conn and not conn.closed: conn.close() # Ensure connection is closed

    return redirect(url_for('view_avis'))

@app.route('/avis/<int:id>/approve', methods=['POST'])
@require_role('admin')
def approve_avis(id):
    # Approves a pending review. Admin only.
    try:
        conn = get_db_connection()
        result = conn.execute('UPDATE avis SET moderated = 1 WHERE id_avis = ? AND moderated = 0', (id,))
        conn.commit(); conn.close()
        if result.rowcount > 0: flash(f'Review {id} approved.', 'success')
        else: flash(f'Review {id} not found or already moderated.', 'warning')
    except Exception as e: flash(f'Error approving review: {str(e)}', 'danger')
    return redirect(url_for('view_avis'))

@app.route('/avis/<int:id>/delete', methods=['POST'])
@require_role('admin')
def delete_avis(id):
    # Deletes any review. Admin only.
    try:
        conn = get_db_connection()
        result = conn.execute('DELETE FROM avis WHERE id_avis = ?', (id,))
        conn.commit(); conn.close()
        if result.rowcount > 0: flash(f'Review {id} deleted.', 'success')
        else: flash(f'Review {id} not found.', 'warning')
    except Exception as e: flash(f'Error deleting review: {str(e)}', 'danger')
    return redirect(url_for('view_avis'))

# --- Error Handlers ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
@app.errorhandler(403)
def forbidden(e):
    # Usually handled by require_role, but acts as fallback
    return render_template('unauthorized.html', required_role='unknown'), 403
@app.errorhandler(500)
def internal_server_error(e):
    # Log the actual error for debugging
    print(f"!!! Internal Server Error: {e}")
    # import traceback; traceback.print_exc() # Uncomment for full traceback in console
    flash('An unexpected server error occurred. Please contact support if the problem persists.', 'danger')
    return render_template('500.html'), 500
@app.errorhandler(405) # Method Not Allowed
def method_not_allowed(e):
    flash(f'Action not allowed for this URL ({request.method}).', 'warning')
    return redirect(request.referrer or url_for('home'))

# --- Main Execution ---
if __name__ == '__main__':
    db_file = 'gesthotel.db'
    if not os.path.exists(db_file):
         print(f"FATAL ERROR: Database file '{db_file}' not found.")
         print("Please run 'python database.py' first to create and populate the database.")
         exit(1)

    port = int(os.environ.get('PORT', 5000))
    print(f"--- Starting Gest'Hôtel Flask Server ---")
    print(f"   Mode: {'DEBUG' if app.debug else 'PRODUCTION'}")
    print(f"   URL: http://127.0.0.1:{port}")
    print(f"-----------------------------------------")
    try:
        # Use debug=True for development ONLY. Turn off for production.
        app.run(debug=True, host='127.0.0.1', port=port)
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"\nFATAL ERROR: Port {port} is already in use.")
            print("Please close the other application using this port or choose a different one.")
        else:
            print(f"\nFATAL ERROR: Failed to start server: {e}")
        exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR: An unexpected error occurred on startup: {e}")
        exit(1)