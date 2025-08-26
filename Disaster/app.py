from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "disaster_is_the_key"

# Database connection function
def get_db_connection():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Inchurahul@2046",
            database="auth_system",
            autocommit=True
        )
        return db
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        fullname = request.form["fullname"]
        email = request.form["email"]
        phone = request.form["phone"]
        place = request.form.get("place", "")
        city = request.form.get("city", "")
        state = request.form.get("state", "")
        pincode = request.form.get("pincode", "")
        password = generate_password_hash(request.form["password"])

        db = get_db_connection()
        if db is None:
            flash("Database connection error. Please try again later.", "danger")
            return redirect(url_for("signup"))
            
        cursor = db.cursor(dictionary=True)
        
        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE email=%s OR phone=%s", (email, phone))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Email or phone already registered!", "danger")
            db.close()
            return redirect(url_for("signup"))

        # Insert new user
        try:
            cursor.execute("""
                INSERT INTO users (fullname, email, phone, place, city, state, pincode, password)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (fullname, email, phone, place, city, state, pincode, password))
            db.commit()
            flash("Signup successful! Please log in.", "success")
        except mysql.connector.Error as err:
            flash(f"Error creating account: {err}", "danger")
        finally:
            db.close()

        return redirect(url_for("signin"))

    return render_template("signup.html")

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email_or_phone = request.form["email_or_phone"].strip()
        password = request.form["password"].strip()

        db = get_db_connection()
        if db is None:
            flash("Database connection error. Please try again later.", "danger")
            return redirect(url_for("signin"))
            
        cursor = db.cursor(dictionary=True)
        
        # Find user by email or phone
        cursor.execute(
            "SELECT * FROM users WHERE email=%s OR phone=%s",
            (email_or_phone, email_or_phone),
        )
        user = cursor.fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["user"] = user["fullname"]
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            flash("Signed in successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email/phone or password", "danger")
            return redirect(url_for("signin"))

    return render_template("signin.html")

@app.route("/dashboard")
def dashboard():
    if "user" in session:
        return render_template("dashboard.html", user=session["user"])
    flash("Please sign in first!", "warning")
    return redirect(url_for("signin"))

@app.route("/report_incident", methods=["GET", "POST"])
def report_incident():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    
    if request.method == "POST":
        incident_type = request.form["incident_type"]
        location = request.form["location"]
        severity = request.form["severity"]
        description = request.form["description"]
        
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            try:
                cursor.execute("""
                    INSERT INTO incidents (user_id, incident_type, location, description, severity)
                    VALUES (%s, %s, %s, %s, %s)
                """, (session["user_id"], incident_type, location, description, severity))
                db.commit()
                flash("Incident reported successfully!", "success")
            except mysql.connector.Error as err:
                flash(f"Error reporting incident: {err}", "danger")
            finally:
                db.close()
        
        return redirect(url_for("report_incident"))
    
    return render_template("report_incident.html")

@app.route("/medical")
def medical():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    return render_template("medical.html")

@app.route("/donate", methods=["GET", "POST"])
def donate():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    
    if request.method == "POST":
        amount = request.form["amount"]
        payment_method = request.form["payment_method"]
        anonymous = "anonymous" in request.form
        
        db = get_db_connection()
        if db:
            cursor = db.cursor()
            try:
                cursor.execute("""
                    INSERT INTO donations (user_id, amount, payment_method, anonymous)
                    VALUES (%s, %s, %s, %s)
                """, (session["user_id"], amount, payment_method, anonymous))
                db.commit()
                flash("Thank you for your donation!", "success")
            except mysql.connector.Error as err:
                flash(f"Error processing donation: {err}", "danger")
            finally:
                db.close()
        
        return redirect(url_for("donate"))
    
    return render_template("donate.html")

@app.route("/nearby_shelters")
def nearby_shelters():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    
    # Sample data for demonstration
    shelters = [
        {"name": "Community Center", "address": "123 Main St", "capacity": 200, "distance": "2.5 km"},
        {"name": "School Gym", "address": "456 Oak Ave", "capacity": 150, "distance": "3.8 km"},
        {"name": "Church Hall", "address": "789 Pine Rd", "capacity": 100, "distance": "1.2 km"}
    ]
    return render_template("nearby_shelters.html", shelters=shelters)

@app.route("/announcements")
def announcements():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    
    # Sample data for demonstration
    announcements = [
        {"title": "Weather Alert", "date": "2025-08-25", "content": "Heavy rain expected in the next 24 hours."},
        {"title": "Evacuation Notice", "date": "2025-08-24", "content": "Residents in low-lying areas should prepare for possible evacuation."}
    ]
    return render_template("announcements.html", announcements=announcements)

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    session.pop("user_email", None)
    flash("Logged out successfully!", "info")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)