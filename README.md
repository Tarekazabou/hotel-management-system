# hotel-management-system
# Gest'Hôtel - Simple Hotel Management Web App

Gest'Hôtel is a web application built with Python and Flask designed for basic hotel management tasks. It allows users with different roles (admin, staff) to manage rooms, clients, reservations, services, invoices, and guest reviews through a user-friendly web interface.

This project started as a simple API and has been converted into a server-rendered web application using Flask and Jinja2 templates.

## ✨ Features

*   **User Authentication:** Secure login/logout system.
*   **Role-Based Access Control:**
    *   **Admin:** Full access, including user management (if implemented), service/room additions, review moderation, and dashboard view.
    *   **Staff:** Access to manage clients, reservations, and invoices.
    *   *(Client role exists in the database but UI features for clients like self-booking or review submission might require further development).*
*   **Room Management:**
    *   View list of all rooms with details (number, type, price, status).
    *   Add new rooms (Admin only).
    *   Room status automatically updated based on reservations (e.g., `Occupé`, `Terminée` leads to `En nettoyage` via trigger).
*   **Client Management:**
    *   View list of clients.
    *   Add new clients (Staff/Admin).
*   **Reservation Management:**
    *   View list of reservations with client and room details.
    *   Create new reservations, checking for availability and conflicts (Staff/Admin).
    *   Cancel existing 'Confirmed' reservations (Staff/Admin).
    *   Reservation status automatically updated to 'Terminée' past the check-out date.
*   **Service Management:**
    *   View list of hotel services (e.g., Breakfast, Spa).
    *   Add new services (Admin only).
    *   (Functionality to add services *to* specific reservations exists in the backend but might need UI integration).
*   **Invoice (Facture) Management:**
    *   View list of generated invoices.
    *   Generate invoices automatically for completed or confirmed reservations (calculates room cost + added services).
    *   Mark invoices as 'Payée' (Staff/Admin).
*   **Review (Avis) Management:**
    *   View approved guest reviews.
    *   Admins can view, approve, or delete pending reviews.
*   **Admin Dashboard:**
    *   View key metrics: Current Occupancy Rate, Average Guest Rating.
    *   See upcoming check-ins.
*   **Web Interface:** User-friendly interface built with HTML, Bootstrap, and Jinja2 templates.
*   **Database:** Uses SQLite for simple data storage.

## 🛠️ Technologies Used

*   **Backend:** Python 3
*   **Framework:** Flask
*   **Templating:** Jinja2
*   **Database:** SQLite 3
*   **Frontend:** HTML, CSS (Bootstrap 5 used in templates)
*   **WSGI Server (Development):** Werkzeug (Flask's built-in)

## 📋 Prerequisites

*   Python 3.7 or higher
*   `pip` (Python package installer)

## 🚀 Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd gesthotel
    ```
    *(Replace `<your-repository-url>` with the actual URL if you host it on GitHub/GitLab etc.)*

2.  **Create a virtual environment (Recommended):**
    *   On macOS/Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   On Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install dependencies:**
    ```bash
    pip install Flask
    ```
    *(Add any other dependencies if you include more libraries later, e.g., `pip install Flask-WTF` for forms)*

4.  **Set up the database:**
    Run the `database.py` script to create the `gesthotel.db` file and populate it with tables and sample data.
    ```bash
    python database.py
    ```
    You should see a confirmation message like "Database and tables created successfully."

## ▶️ Running the Application

1.  **Ensure your virtual environment is active.** (See step 2 in Installation)
2.  **Run the Flask application:**
    ```bash
    python app.py
    ```
3.  The application will start, typically on `http://127.0.0.1:5000`. Open this URL in your web browser.

## 🧑‍💻 Usage

1.  Navigate to `http://127.0.0.1:5000` in your browser.
2.  You will be redirected to the login page (`/login`).
3.  Use the following default credentials (created by `database.py`):
    *   **Admin:**
        *   Username: `admin`
        *   Password: `admin123`
    *   **Staff:**
        *   Username: `staff`
        *   Password: `staff123`
    *   *(Client: `client` / `client123` - Limited UI functionality)*
4.  Once logged in, you can navigate using the top navigation bar to access different management sections based on your role.

## 🗄️ Database

*   The application uses an SQLite database file named `gesthotel.db`.
*   The schema (table structure, relationships, triggers) and initial sample data are defined in `database.py`.

## 🔐 Roles and Permissions Summary

*   **Admin:** Can do everything Staff can do, PLUS:
    *   Access the Dashboard.
    *   Add/Edit Rooms.
    *   Add/Edit Services.
    *   Moderate (Approve/Delete) Reviews.
*   **Staff:** Can:
    *   View Rooms.
    *   Add/View Clients.
    *   Add/View/Cancel Reservations.
    *   View Services.
    *   Generate/View/Mark Invoices as Paid.
    *   View Approved Reviews.
*   **Anyone Logged In:** Can view approved reviews and basic room/service lists.
*   **Not Logged In:** Can only access the Login page.

## ⚠️ Security Warning

This application is intended for educational or demonstration purposes. **It is NOT production-ready.** Key security considerations are missing:

*   **Password Storage:** Passwords are stored in plain text in the database. **Never do this in production!** Use password hashing libraries like `Werkzeug`'s security helpers or `passlib`.
*   **CSRF Protection:** Forms are potentially vulnerable to Cross-Site Request Forgery. Implement CSRF tokens (e.g., using Flask-WTF).
*   **Input Validation:** While basic checks exist, more robust server-side validation is needed.
*   **Secret Key:** The Flask `app.secret_key` should be a strong, random value and ideally loaded from environment variables or a configuration file, not hardcoded (especially the fallback default).
*   **HTTPS:** The development server runs on HTTP. Production deployments require HTTPS.
*   **Error Handling:** Detailed error messages might leak information in production; configure logging appropriately.

## 📝 To-Do / Potential Improvements

*   Implement password hashing and user registration/management.
*   Add CSRF protection to all forms.
*   Implement Edit and Delete functionality for Rooms, Clients, Services.
*   Refine the UI/UX, potentially add more interactive elements with JavaScript.
*   Integrate the "Add Service to Reservation" feature into the web UI (e.g., on a reservation detail page).
*   Develop client-facing features (e.g., room browsing, booking requests, review submission form integrated into user flow).
*   Add more comprehensive input validation.
*   Implement pagination for long lists (Clients, Reservations, etc.).
*   Add unit and integration tests.
*   Improve database queries for efficiency, especially conflict checking.
*   Deploy using a production-ready WSGI server (like Gunicorn or uWSGI) behind a reverse proxy (like Nginx).

## Contributing

Contributions are welcome! Please feel free to fork the repository, make changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

*(tarekAZABOU)*

This project is licensed under the tarekAZABOU License .
