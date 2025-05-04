import sqlite3
from datetime import datetime # Make sure this is imported
from functools import wraps
from flask import (Flask, abort, flash, jsonify, redirect,
                   render_template, request, session, url_for)
import os # Good practice for generating secret keys

app = Flask(__name__, template_folder='templates')

# IMPORTANT: Set a secret key for session management!
# Replace 'your secret key' with a real, random secret key.
# Using os.urandom(24) generates a good random key.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'fallback - change this default key') # Example using environment variable or a default
# Or simply: app.secret_key = b'_5#y2L"F4Q8z\n\xec]/' # A generated key, but storing it directly isn't best practice

# --- Context Processor to Inject Variables into all Templates ---
@app.context_processor
def inject_now():
    """Injects the current UTC time into templates."""
    # Using utcnow() is often preferred for web apps to avoid timezone issues
    return {'now': datetime.utcnow}
# --- End of Context Processor ---


def get_db_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect('gesthotel.db')
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

# --- Authentication & Authorization ---

def login_required(f):
    """Decorator to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url)) # Redirect back after login
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role):
    """Decorator to require a specific user role."""
    def decorator(f):
        @wraps(f)
        @login_required # Ensure user is logged in first
        def decorated_function(*args, **kwargs):
            user_role = session.get('role')
            # Allow admin access to everything a staff member can do
            allowed_roles = [required_role]
            if required_role == 'staff' and user_role == 'admin':
                 pass # Admin implicitly has staff permissions
            elif user_role != required_role and not (required_role == 'staff' and user_role == 'admin'):
                 # Render the unauthorized page directly
                return render_template('unauthorized.html', required_role=required_role), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if 'user_id' in session: # If already logged in, redirect home
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('login.html')

        conn = get_db_connection()
        # IMPORTANT: Store hashed passwords in production! This is insecure.
        user = conn.execute('SELECT id_user, username, role FROM users WHERE username = ? AND password = ?',
                            (username, password)).fetchone()
        conn.close()

        if user:
            # Store user info in session
            session.permanent = True # Make session last longer (optional)
            session['user_id'] = user['id_user']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')

            next_url = request.args.get('next') # Get redirect URL if provided
            # Redirect based on role or next_url
            if next_url:
                return redirect(next_url)
            elif user['role'] == 'admin':
                 return redirect(url_for('dashboard'))
            else:
                 return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'danger')
            return render_template('login.html')

    # If GET request or login failed, show the login form
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handle user logout."""
    session.clear() # Clear all session data
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required # Require login for the home page
def home():
    """Home page after login."""
    # Redirect admin directly to dashboard
    if session.get('role') == 'admin':
        return redirect(url_for('dashboard'))
    # Render a generic home page for other logged-in users
    return render_template('home.html')


# --- Chambres (Rooms) ---

@app.route('/chambres', methods=['GET'])
@login_required # Anyone logged in can view rooms
def view_chambres():
    try:
        conn = get_db_connection()
        chambres = conn.execute('SELECT * FROM chambres ORDER BY numero_chambre').fetchall()
        conn.close()
        return render_template('chambres.html', chambres=chambres)
    except Exception as e:
        flash(f'Error fetching rooms: {str(e)}', 'danger')
        return render_template('chambres.html', chambres=[])

@app.route('/chambres/add', methods=['POST'])
@require_role('admin')
def add_chambre():
    # Data comes from form, not JSON
    numero = request.form.get('numero_chambre')
    type_chambre = request.form.get('type_chambre')
    prix = request.form.get('prix_nuit')
    statut = request.form.get('statut')

    if not all([numero, type_chambre, prix, statut]):
        flash('All fields are required to add a room.', 'warning')
        return redirect(url_for('view_chambres'))

    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO chambres (numero_chambre, type_chambre, prix_nuit, statut) VALUES (?, ?, ?, ?)',
                     (numero, type_chambre, float(prix), statut))
        conn.commit()
        conn.close()
        flash(f'Room {numero} added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Room number {numero} already exists.', 'danger')
    except ValueError:
        flash('Invalid price format. Please enter a number.', 'danger')
    except Exception as e:
        flash(f'Error adding room: {str(e)}', 'danger')

    return redirect(url_for('view_chambres'))

# --- Clients ---

@app.route('/clients', methods=['GET'])
@require_role('staff') # Staff and admin can view clients
def view_clients():
    try:
        conn = get_db_connection()
        clients = conn.execute('SELECT * FROM clients ORDER BY nom, prenom').fetchall()
        conn.close()
        return render_template('clients.html', clients=clients)
    except Exception as e:
        flash(f'Error fetching clients: {str(e)}', 'danger')
        return render_template('clients.html', clients=[])

@app.route('/clients/add', methods=['POST'])
@require_role('staff') # Staff and admin can add clients
def add_client():
    nom = request.form.get('nom')
    prenom = request.form.get('prenom')
    telephone = request.form.get('telephone')
    email = request.form.get('email')
    adresse = request.form.get('adresse')

    if not nom or not prenom or not email:
        flash('First name, last name, and email are required.', 'warning')
        return redirect(url_for('view_clients'))

    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO clients (nom, prenom, telephone, email, adresse) VALUES (?, ?, ?, ?, ?)',
                     (nom, prenom, telephone, email, adresse))
        conn.commit()
        conn.close()
        flash(f'Client {prenom} {nom} added successfully!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Client with email {email} already exists.', 'danger')
    except Exception as e:
        flash(f'Error adding client: {str(e)}', 'danger')

    return redirect(url_for('view_clients'))

# --- Reservations ---

@app.route('/reservations', methods=['GET'])
@require_role('staff')
def view_reservations():
    try:
        conn = get_db_connection()
        # Auto-update status of past confirmed reservations
        today = datetime.now().strftime('%Y-%m-%d')
        conn.execute('''
            UPDATE reservations SET statut = 'Terminée'
            WHERE statut = 'Confirmée' AND date(date_fin) < date(?)
        ''', (today,))
        conn.commit() # Commit the status update

        # Fetch reservations with client and room details
        reservations = conn.execute('''
            SELECT r.*, c.nom, c.prenom, c.email, ch.numero_chambre
            FROM reservations r
            JOIN clients c ON r.id_client = c.id_client
            JOIN chambres ch ON r.id_chambre = ch.id_chambre
            ORDER BY r.date_debut DESC
        ''').fetchall()

        # Fetch clients and available rooms for the add form dropdowns
        clients = conn.execute('SELECT id_client, nom, prenom, email FROM clients ORDER BY nom, prenom').fetchall()
        # Fetch rooms that are not currently occupied based on today's date
        # This check is slightly simplified; a more robust check would consider future bookings too
        chambres = conn.execute('''
            SELECT id_chambre, numero_chambre, type_chambre
            FROM chambres
            WHERE statut = 'Libre' OR statut = 'En nettoyage'
            ORDER BY numero_chambre
            ''').fetchall()
            # Consider adding a check here: AND id_chambre NOT IN (SELECT id_chambre FROM reservations WHERE statut='Confirmée' AND date(?) BETWEEN date(date_debut) AND date(date_fin))

        conn.close()
        return render_template('reservations.html', reservations=reservations, clients=clients, chambres=chambres)
    except Exception as e:
        flash(f'Error fetching reservations: {str(e)}', 'danger')
        return render_template('reservations.html', reservations=[], clients=[], chambres=[])


@app.route('/reservations/add', methods=['POST'])
@require_role('staff')
def add_reservation():
    id_client = request.form.get('id_client')
    id_chambre = request.form.get('id_chambre')
    date_debut_str = request.form.get('date_debut')
    date_fin_str = request.form.get('date_fin')

    if not all([id_client, id_chambre, date_debut_str, date_fin_str]):
        flash('Client, Room, Start Date, and End Date are required.', 'warning')
        return redirect(url_for('view_reservations'))

    try:
        # Validate dates
        date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
        date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        today = datetime.now().date()

        if date_debut < today:
             flash('Check-in date cannot be in the past.', 'warning')
             return redirect(url_for('view_reservations'))
        if date_debut >= date_fin:
            flash('Check-out date must be after check-in date.', 'warning')
            return redirect(url_for('view_reservations'))

        conn = get_db_connection()
        # Check for booking conflicts (more robust)
        # A conflict exists if another confirmed reservation overlaps with the requested period
        conflict = conn.execute('''
            SELECT 1 FROM reservations
            WHERE id_chambre = ?
            AND statut = 'Confirmée'
            AND date(date_debut) < date(?)
            AND date(date_fin) > date(?)
            LIMIT 1
        ''', (id_chambre, date_fin_str, date_debut_str)).fetchone()

        if conflict:
            conn.close()
            flash(f'Room {id_chambre} is already booked for the selected dates.', 'danger') # Use room number if available
            return redirect(url_for('view_reservations'))

        # Check room status isn't explicitly 'Occupied' (might be redundant with conflict check)
        room_status = conn.execute('SELECT statut FROM chambres WHERE id_chambre = ?', (id_chambre,)).fetchone()
        if room_status and room_status['statut'] == 'Occupé':
             # Double-check if the occupation ends before the new booking starts (handled by conflict query usually)
             pass # Let conflict query handle this

        # Insert reservation
        cursor = conn.cursor()
        cursor.execute('INSERT INTO reservations (id_client, id_chambre, date_debut, date_fin, statut) VALUES (?, ?, ?, ?, ?)',
                       (id_client, id_chambre, date_debut_str, date_fin_str, 'Confirmée'))
        # Update room status only if the reservation starts today or in the past (unlikely with validation)
        # A better approach might be a scheduled task or updating status upon actual check-in.
        # For simplicity, let's mark it occupied *if the booking includes today*.
        if date_debut <= today < date_fin:
             cursor.execute('UPDATE chambres SET statut = ? WHERE id_chambre = ?', ('Occupé', id_chambre))
        elif date_debut > today and room_status['statut'] == 'Libre':
             pass # Keep it Libre until check-in day
        # If status was 'En nettoyage', maybe keep it that way until ready? Depends on hotel workflow.

        conn.commit()
        conn.close()
        flash('Reservation added successfully!', 'success')

    except ValueError:
        flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
    except sqlite3.IntegrityError as e:
        flash(f'Invalid client or room selection. Please ensure they exist.', 'danger')
    except Exception as e:
        flash(f'Error adding reservation: {str(e)}', 'danger')

    return redirect(url_for('view_reservations'))


@app.route('/reservations/<int:id>/cancel', methods=['POST']) # Use POST for cancellation action
@require_role('staff')
def cancel_reservation(id):
    try:
        conn = get_db_connection()
        # Get reservation details, especially the room ID and status
        reservation = conn.execute('SELECT id_chambre, statut, date_debut FROM reservations WHERE id_reservation = ?', (id,)).fetchone()

        if not reservation:
            conn.close()
            flash('Reservation not found.', 'warning')
            return redirect(url_for('view_reservations'))

        if reservation['statut'] != 'Confirmée':
             conn.close()
             flash(f'Reservation {id} is already {reservation["statut"]} and cannot be cancelled.', 'warning')
             return redirect(url_for('view_reservations'))

        id_chambre = reservation['id_chambre']

        # Update reservation status
        conn.execute('UPDATE reservations SET statut = ? WHERE id_reservation = ?', ('Annulée', id))

        # Check if the room is currently occupied by *other* CONFIRMED reservations
        today = datetime.now().strftime('%Y-%m-%d')
        other_booking_active_today = conn.execute('''
            SELECT 1 FROM reservations
            WHERE id_chambre = ?
              AND id_reservation != ?
              AND statut = 'Confirmée'
              AND date(date_debut) <= date(?)
              AND date(date_fin) > date(?)
            LIMIT 1
        ''', (id_chambre, id, today, today)).fetchone()

        # If no other active confirmed bookings for today, set room to Libre
        # (Assuming it wasn't 'En nettoyage' before)
        # More complex logic might be needed if the room was 'En nettoyage'
        if not other_booking_active_today:
             conn.execute("UPDATE chambres SET statut = 'Libre' WHERE id_chambre = ? AND statut != 'En nettoyage'", (id_chambre,))

        conn.commit()
        conn.close()
        flash(f'Reservation {id} cancelled successfully.', 'success')
    except Exception as e:
        flash(f'Error cancelling reservation: {str(e)}', 'danger')

    return redirect(url_for('view_reservations'))


# --- Services ---

@app.route('/services', methods=['GET'])
@login_required # Allow viewing services
def view_services():
    try:
        conn = get_db_connection()
        services = conn.execute('SELECT * FROM services ORDER BY nom_service').fetchall()
        conn.close()
        return render_template('services.html', services=services)
    except Exception as e:
        flash(f'Error fetching services: {str(e)}', 'danger')
        return render_template('services.html', services=[])

@app.route('/services/add', methods=['POST'])
@require_role('admin')
def add_service():
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
        flash(f'Service "{nom}" already exists.', 'danger')
    except ValueError:
        flash('Invalid price format. Please enter a number.', 'danger')
    except Exception as e:
        flash(f'Error adding service: {str(e)}', 'danger')

    return redirect(url_for('view_services'))


# --- Reservation Services (Assigning services to reservations) ---
# Keeping the original API endpoint logic here, but might need adaptation for UI
# You would likely add a section in the reservation details page to manage this.
@app.route('/reservation_services', methods=['POST'])
@require_role('staff')
def add_reservation_service():
    # This endpoint currently expects JSON. Modify if using forms.
    if not request.is_json:
         return jsonify({'error': 'Request must be JSON'}), 400
    data = request.json
    id_reservation = data.get('id_reservation')
    id_service = data.get('id_service')

    if not id_reservation or not id_service:
        return jsonify({'error': 'Missing reservation_id or service_id'}), 400

    try:
        conn = get_db_connection()
        # Optional: Check if reservation and service exist and are valid
        conn.execute('INSERT INTO reservation_services (id_reservation, id_service) VALUES (?, ?)',
                     (id_reservation, id_service))
        conn.commit()
        conn.close()
        # For a web app, you'd likely redirect or flash a message instead of jsonify
        flash(f'Service added to reservation {id_reservation}.', 'success')
        # Find where to redirect - maybe back to the reservation detail page?
        return redirect(url_for('view_reservations')) # Placeholder redirect
        # return jsonify({'message': 'Service added to reservation'}), 201
    except sqlite3.IntegrityError:
        # jsonify({'error': 'Invalid reservation or service ID, or already associated'}), 400
        flash('Invalid reservation or service ID, or service already added.', 'danger')
        return redirect(url_for('view_reservations')) # Placeholder redirect
    except Exception as e:
        # jsonify({'error': str(e)}), 500
        flash(f'Error adding service to reservation: {str(e)}', 'danger')
        return redirect(url_for('view_reservations')) # Placeholder redirect


# --- Factures (Invoices) ---

@app.route('/factures', methods=['GET'])
@require_role('staff')
def view_factures():
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
        # Get reservations that might need an invoice (Confirmed or Terminee, not Annulee, no existing invoice)
        reservations_needing_invoice = conn.execute('''
            SELECT r.id_reservation, r.date_debut, r.date_fin, c.nom || ' ' || c.prenom AS client_name, ch.numero_chambre
            FROM reservations r
            JOIN clients c ON r.id_client = c.id_client
            JOIN chambres ch ON r.id_chambre = ch.id_chambre
            WHERE r.statut IN ('Confirmée', 'Terminée')
            AND r.id_reservation NOT IN (SELECT id_reservation FROM factures)
            ORDER BY r.date_fin DESC, r.id_reservation DESC
        ''').fetchall()

        conn.close()
        return render_template('factures.html', factures=factures, reservations_needing_invoice=reservations_needing_invoice)
    except Exception as e:
        flash(f'Error fetching invoices: {str(e)}', 'danger')
        return render_template('factures.html', factures=[], reservations_needing_invoice=[])

@app.route('/factures/generate', methods=['POST'])
@require_role('staff')
def generate_facture():
    id_reservation = request.form.get('id_reservation')
    if not id_reservation:
        flash('Please select a reservation to generate an invoice.', 'warning')
        return redirect(url_for('view_factures'))

    try:
        conn = get_db_connection()
        # Check if invoice already exists
        existing = conn.execute('SELECT 1 FROM factures WHERE id_reservation = ?', (id_reservation,)).fetchone()
        if existing:
             conn.close()
             flash(f'Invoice already exists for reservation {id_reservation}.', 'warning')
             return redirect(url_for('view_factures'))

        # Get reservation details for calculation
        reservation = conn.execute('''
            SELECT r.date_debut, r.date_fin, r.statut, ch.prix_nuit
            FROM reservations r
            JOIN chambres ch ON r.id_chambre = ch.id_chambre
            WHERE r.id_reservation = ?
        ''', (id_reservation,)).fetchone()

        if not reservation:
            conn.close()
            flash(f'Reservation {id_reservation} not found.', 'warning')
            return redirect(url_for('view_factures'))

        if reservation['statut'] == 'Annulée':
             conn.close()
             flash(f'Cannot generate invoice for cancelled reservation {id_reservation}.', 'warning')
             return redirect(url_for('view_factures'))

        # Calculate costs
        date_debut = datetime.strptime(reservation['date_debut'], '%Y-%m-%d').date()
        date_fin = datetime.strptime(reservation['date_fin'], '%Y-%m-%d').date()
        nights = max(1, (date_fin - date_debut).days) # Ensure at least 1 night cost if dates are same day
        room_cost = nights * reservation['prix_nuit']

        # Sum prices of associated services
        services_cost_result = conn.execute('''
            SELECT COALESCE(SUM(s.prix), 0) as total_prix
            FROM reservation_services rs
            JOIN services s ON rs.id_service = s.id_service
            WHERE rs.id_reservation = ?
        ''', (id_reservation,)).fetchone()
        services_cost = services_cost_result['total_prix'] if services_cost_result else 0

        montant_total = room_cost + services_cost
        today_str = datetime.now().strftime('%Y-%m-%d')

        # Insert invoice
        conn.execute('INSERT INTO factures (id_reservation, montant_total, date_emission, statut) VALUES (?, ?, ?, ?)',
                     (id_reservation, montant_total, today_str, 'Non payée'))
        conn.commit()
        conn.close()
        flash(f'Invoice generated successfully for reservation {id_reservation}. Total: {montant_total:.2f} €', 'success') # Added currency symbol

    except ValueError:
        flash('Invalid date format found in reservation data.', 'danger')
    except sqlite3.Error as e: # Catch specific SQLite errors
         flash(f'Database error generating invoice: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Error generating invoice: {str(e)}', 'danger')

    return redirect(url_for('view_factures'))


@app.route('/factures/<int:id>/pay', methods=['POST'])
@require_role('staff')
def mark_facture_paid(id):
    try:
        conn = get_db_connection()
        result = conn.execute('UPDATE factures SET statut = ? WHERE id_facture = ? AND statut = ?',
                              ('Payée', id, 'Non payée'))
        conn.commit()
        conn.close()
        if result.rowcount > 0:
            flash(f'Invoice #{id} marked as paid.', 'success')
        else:
            flash(f'Invoice #{id} not found or already paid.', 'warning')
    except Exception as e:
        flash(f'Error updating invoice status: {str(e)}', 'danger')

    return redirect(url_for('view_factures'))

# --- Avis (Reviews) ---

@app.route('/avis', methods=['GET'])
@login_required # All logged-in users can see approved reviews
def view_avis():
    try:
        conn = get_db_connection()
        # Approved reviews (visible to all logged-in users)
        approved_avis = conn.execute('''
            SELECT a.*, c.nom || ' ' || c.prenom AS client_name
            FROM avis a
            JOIN clients c ON a.id_client = c.id_client
            WHERE a.moderated = 1
            ORDER BY a.date_avis DESC, a.id_avis DESC
        ''').fetchall()

        # Pending reviews (visible only to admin)
        pending_avis = []
        if session.get('role') == 'admin':
            pending_avis = conn.execute('''
                SELECT a.*, c.nom || ' ' || c.prenom AS client_name, r.id_reservation
                FROM avis a
                JOIN clients c ON a.id_client = c.id_client
                JOIN reservations r ON a.id_reservation = r.id_reservation /* Added Join */
                WHERE a.moderated = 0
                ORDER BY a.date_avis DESC, a.id_avis DESC
            ''').fetchall()

        conn.close()
        return render_template('avis.html', approved_avis=approved_avis, pending_avis=pending_avis)
    except Exception as e:
        flash(f'Error fetching reviews: {str(e)}', 'danger')
        return render_template('avis.html', approved_avis=[], pending_avis=[])

# Note: Adding reviews would typically be done by clients, maybe via a separate interface
# or after their stay. The original `add_avis` POST endpoint could be adapted if needed.
# Example placeholder route for adding reviews (needs a form and likely client role check)
@app.route('/avis/add', methods=['POST'])
@login_required # Or maybe specifically @require_role('client')
def add_avis():
     # This needs a form in a template (e.g., on reservation history page)
     id_client = session.get('user_id') # Assuming client user ID matches client ID
     id_reservation = request.form.get('id_reservation')
     note = request.form.get('note')
     commentaire = request.form.get('commentaire')

     if not all([id_client, id_reservation, note, commentaire]):
         flash('Reservation, rating, and comment are required.', 'warning')
         # Redirect back to where the form was
         return redirect(request.referrer or url_for('home'))

     try:
         note_int = int(note)
         if not 1 <= note_int <= 5:
             flash('Rating must be between 1 and 5.', 'warning')
             return redirect(request.referrer or url_for('home'))

         conn = get_db_connection()
         # Add check: ensure this client actually made this reservation and it's completed?
         today = datetime.now().strftime('%Y-%m-%d')
         conn.execute('INSERT INTO avis (id_client, id_reservation, note, commentaire, date_avis, moderated) VALUES (?, ?, ?, ?, ?, 0)',
                      (id_client, id_reservation, note_int, commentaire, today))
         conn.commit()
         conn.close()
         flash('Thank you! Your review has been submitted for moderation.', 'success')
     except ValueError:
         flash('Invalid rating value.', 'danger')
     except sqlite3.IntegrityError:
         flash('Could not submit review. Invalid reservation or review already submitted for it.', 'danger')
     except Exception as e:
         flash(f'Error submitting review: {str(e)}', 'danger')

     return redirect(url_for('view_avis')) # Redirect to reviews page or user history


@app.route('/avis/<int:id>/approve', methods=['POST'])
@require_role('admin')
def approve_avis(id):
    try:
        conn = get_db_connection()
        result = conn.execute('UPDATE avis SET moderated = 1 WHERE id_avis = ? AND moderated = 0', (id,))
        conn.commit()
        conn.close()
        if result.rowcount > 0:
            flash(f'Review {id} approved.', 'success')
        else:
            flash(f'Review {id} not found or already moderated.', 'warning')
    except Exception as e:
        flash(f'Error approving review: {str(e)}', 'danger')

    return redirect(url_for('view_avis'))

@app.route('/avis/<int:id>/delete', methods=['POST']) # Admins might want to delete bad reviews
@require_role('admin')
def delete_avis(id):
    try:
        conn = get_db_connection()
        result = conn.execute('DELETE FROM avis WHERE id_avis = ?', (id,))
        conn.commit()
        conn.close()
        if result.rowcount > 0:
            flash(f'Review {id} deleted.', 'success')
        else:
            flash(f'Review {id} not found.', 'warning')
    except Exception as e:
        flash(f'Error deleting review: {str(e)}', 'danger')
    return redirect(url_for('view_avis'))

# --- Dashboard ---

@app.route('/dashboard')
@require_role('admin')
def dashboard():
    try:
        conn = get_db_connection()
        today = datetime.now().strftime('%Y-%m-%d')

        # Occupancy rate: Rooms occupied *today* / Total rooms
        total_rooms_result = conn.execute('SELECT COUNT(*) as total FROM chambres').fetchone()
        total_rooms = total_rooms_result['total'] if total_rooms_result else 0

        occupied_rooms_result = conn.execute('''
            SELECT COUNT(DISTINCT id_chambre) as occupied
            FROM reservations
            WHERE statut = 'Confirmée'
              AND date(date_debut) <= date(?)
              AND date(date_fin) > date(?)
        ''', (today, today)).fetchone()
        occupied_rooms = occupied_rooms_result['occupied'] if occupied_rooms_result else 0
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0

        # Average rating
        avg_rating_result = conn.execute('SELECT AVG(note) as avg_note FROM avis WHERE moderated = 1').fetchone()
        avg_rating = avg_rating_result['avg_note'] if avg_rating_result and avg_rating_result['avg_note'] is not None else 0

        # Upcoming check-ins (next 7 days)
        upcoming_checkins = conn.execute('''
             SELECT r.id_reservation, r.date_debut, c.nom, c.prenom, ch.numero_chambre
             FROM reservations r
             JOIN clients c ON r.id_client = c.id_client
             JOIN chambres ch ON r.id_chambre = ch.id_chambre
             WHERE r.statut = 'Confirmée'
               AND date(r.date_debut) BETWEEN date(?) AND date(?, '+7 days')
             ORDER BY r.date_debut ASC
             LIMIT 5
        ''', (today, today)).fetchall()

        conn.close()
        return render_template('dashboard.html',
                               occupancy_rate=round(occupancy_rate, 2),
                               average_rating=round(avg_rating, 2),
                               upcoming_checkins=upcoming_checkins)
    except Exception as e:
        flash(f'Error loading dashboard data: {str(e)}', 'danger')
        # Return template with default values or error message
        return render_template('dashboard.html', occupancy_rate=0, average_rating=0, upcoming_checkins=[], error=str(e))


# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
     # Rendered directly by require_role now, but keep as fallback
    return render_template('unauthorized.html', required_role='unknown'), 403

@app.errorhandler(500)
def internal_server_error(e):
    # Log the error e for debugging
    print(f"Internal Server Error: {e}")
    # You might want more sophisticated logging in production
    # import traceback
    # print(traceback.format_exc())
    flash('An unexpected server error occurred. Please try again later or contact support.', 'danger')
    return render_template('500.html'), 500

@app.errorhandler(405) # Method Not Allowed
def method_not_allowed(e):
    flash(f'Method {request.method} not allowed for {request.path}.', 'warning')
    return redirect(request.referrer or url_for('home'))


if __name__ == '__main__':
    # Make sure the database file exists before running
    db_file = 'gesthotel.db'
    if not os.path.exists(db_file):
         print(f"Database file '{db_file}' not found.")
         print("Please run 'python database.py' first to create and populate the database.")
         # Consider running the database script automatically if it doesn't exist
         # import subprocess
         # print("Attempting to create database...")
         # try:
         #    subprocess.run(['python', 'database.py'], check=True)
         #    print("Database created successfully.")
         # except Exception as db_err:
         #    print(f"Failed to create database automatically: {db_err}")
         #    exit(1) # Exit if DB creation fails
         exit(1)

    port = int(os.environ.get('PORT', 5000)) # Use environment variable for port if available
    try:
        print(f"Starting Flask server on http://127.0.0.1:{port} ...")
        # Setting host='0.0.0.0' makes it accessible on your network,
        # useful for testing on other devices. Keep as 127.0.0.1 for local only.
        app.run(debug=True, host='127.0.0.1', port=port) # Debug=True is helpful for development
    except OSError as e:
        if "address already in use" in str(e).lower():
             print(f"Port {port} is already in use. Please close the other application or try a different port.")
             # Optionally, try the next port automatically
             # try:
             #     print(f"Trying port {port + 1} instead...")
             #     app.run(debug=True, host='127.0.0.1', port=port + 1)
             # except OSError as e2:
             #      print(f"Failed to start on port {port + 1} as well: {e2}")
        else:
             print(f"Failed to start server: {e}")