from flask import Flask, render_template, request, redirect, url_for, session, flash
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from supabase import create_client, Client
import overpy
import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Simple rate limiting for signup
signup_attempts = {}

# Supabase client setup
if not Config.is_supabase_configured():
    print("Warning: SUPABASE_URL or SUPABASE_KEY is not set. Set them in environment or .env file.")
    print("Database features will be disabled.")

supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY) if Config.is_supabase_configured() else None

# Helpers
def sb_available() -> bool:
    return supabase is not None

def require_role(required_role):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                flash("Please sign in first!", "warning")
                return redirect(url_for("signin"))
            if session.get("user_role") != required_role:
                flash("Access denied. Insufficient permissions.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

def fetch_weather_data(location):
    """Resilient weather data fetching via wttr.in using city name directly."""
    try:
        # Build a resilient session with retries once
        global _weather_session
        if '_weather_session' not in globals():
            retry = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=frozenset(["GET"]) 
            )
            _weather_session = requests.Session()
            adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
            _weather_session.mount("http://", adapter)
            _weather_session.mount("https://", adapter)
            _weather_session.headers.update({
                "User-Agent": "DisasterManagement/1.0 (+wttr fetch)",
                "Accept": "application/json"
            })

        # Query wttr.in directly by location name (avoids geocoding failures/rate limits)
        q = quote(location)
        weather_url = f"https://wttr.in/{q}?format=j1"

        response = _weather_session.get(weather_url, timeout=(3, 8))
        response.raise_for_status()
        weather_data = response.json()

        if not weather_data:
            return None

        # Extract weather information from wttr.in response
        current_condition = (weather_data.get('current_condition') or [{}])[0]
        temp_c = current_condition.get('temp_C')
        humidity = current_condition.get('humidity')
        wind_speed = current_condition.get('windspeedKmph')
        weather_desc = (current_condition.get('weatherDesc') or [{}])[0].get('value', 'Unknown')

        # Optional coordinates from nearest_area, if present
        nearest = (weather_data.get('nearest_area') or [{}])
        nearest0 = nearest[0] if nearest else {}
        lat_str = (nearest0.get('latitude') or [None])
        lon_str = (nearest0.get('longitude') or [None])
        try:
            lat = float(lat_str if isinstance(lat_str, str) else (lat_str[0] if lat_str else None)) if lat_str else None
            lon = float(lon_str if isinstance(lon_str, str) else (lon_str[0] if lon_str else None)) if lon_str else None
        except Exception:
            lat = None
            lon = None

        # Convert to numeric values
        temp = float(temp_c) if temp_c not in (None, "") else None
        humidity = int(humidity) if humidity not in (None, "") else None
        wind_speed = float(wind_speed) if wind_speed not in (None, "") else None

        # Determine if weather is extreme
        is_extreme = False
        weather_alert = None

        if temp is not None:
            if temp > 40 or temp < -10:
                is_extreme = True
                weather_alert = f"Extreme temperature: {temp}°C"
            elif temp > 35 or temp < -5:
                weather_alert = f"High temperature: {temp}°C"

        if wind_speed and wind_speed > 20:
            is_extreme = True
            weather_alert = f"High wind speed: {wind_speed} km/h"

        severe_conditions = ['thunder', 'storm', 'tornado', 'hurricane', 'cyclone']
        if isinstance(weather_desc, str) and any(condition in weather_desc.lower() for condition in severe_conditions):
            is_extreme = True
            weather_alert = f"Severe weather: {weather_desc}"

        return {
            'location': location,
            'temperature': temp,
            'humidity': humidity,
            'wind_speed': wind_speed,
            'weather_condition': weather_desc,
            'weather_description': weather_desc,
            'is_extreme': is_extreme,
            'weather_alert': weather_alert,
            'coordinates': {'lat': lat, 'lon': lon}
        }

    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None

def fetch_multiple_locations_weather():
    """Ultra-fast weather data fetching for major Indian cities using optimized parallel processing"""
    # Expanded list of major Indian cities covering all regions
    locations = [
        # Northern India
        "Delhi, India",
        "Jaipur, Rajasthan, India",
        "Lucknow, Uttar Pradesh, India",
        "Chandigarh, India",
        "Dehradun, Uttarakhand, India",
        "Amritsar, Punjab, India",
        "Jammu, Jammu and Kashmir, India",
        "Srinagar, Jammu and Kashmir, India",
        "Shimla, Himachal Pradesh, India",
        
        # Western India
        "Mumbai, Maharashtra, India",
        "Pune, Maharashtra, India",
        "Nagpur, Maharashtra, India",
        "Ahmedabad, Gujarat, India",
        "Surat, Gujarat, India",
        "Vadodara, Gujarat, India",
        "Bhopal, Madhya Pradesh, India",
        "Indore, Madhya Pradesh, India",
        "Jodhpur, Rajasthan, India",
        "Udaipur, Rajasthan, India",
        "Goa, India",
        
        # Southern India
        "Bangalore, Karnataka, India",
        "Mysore, Karnataka, India",
        "Hyderabad, Telangana, India",
        "Chennai, Tamil Nadu, India",
        "Coimbatore, Tamil Nadu, India",
        "Madurai, Tamil Nadu, India",
        "Kochi, Kerala, India",
        "Thiruvananthapuram, Kerala, India",
        "Visakhapatnam, Andhra Pradesh, India",
        "Vijayawada, Andhra Pradesh, India",
        "Pondicherry, India",
        
        # Eastern India
        "Kolkata, West Bengal, India",
        "Howrah, West Bengal, India",
        "Patna, Bihar, India",
        "Ranchi, Jharkhand, India",
        "Bhubaneswar, Odisha, India",
        "Cuttack, Odisha, India",
        "Guwahati, Assam, India",
        "Shillong, Meghalaya, India",
        "Imphal, Manipur, India",
        "Agartala, Tripura, India",
        "Kohima, Nagaland, India",
        
        # Central India
        "Raipur, Chhattisgarh, India",
        "Bilaspur, Chhattisgarh, India",
        "Jabalpur, Madhya Pradesh, India",
        "Gwalior, Madhya Pradesh, India"
    ]
    
    print(f"🚀 Starting ultra-fast parallel weather fetch for {len(locations)} major Indian cities...")
    start_time = time.time()
    
    # Use ThreadPoolExecutor for parallel processing
    extreme_weather_locations = []
    successful_fetches = 0
    
    with ThreadPoolExecutor(max_workers=10) as executor:  # Increased workers for more cities
        # Submit all weather fetch tasks
        future_to_location = {executor.submit(fetch_weather_data, location): location for location in locations}
        
        # Process completed tasks
        for future in as_completed(future_to_location):
            location = future_to_location[future]
            try:
                weather_data = future.result()
                if weather_data:
                    successful_fetches += 1
                    if weather_data['is_extreme']:
                        extreme_weather_locations.append(weather_data)
                        print(f"⚠ Extreme weather in {location}: {weather_data['weather_alert']}")
                    else:
                        print(f"✅ Normal weather in {location}")
                else:
                    print(f"❌ Failed to fetch weather for {location}")
            except Exception as e:
                print(f"Error fetching weather for {location}: {e}")
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"⚡ Weather fetch completed in {duration:.2f} seconds!")
    print(f"📊 Results: {successful_fetches}/{len(locations)} successful, {len(extreme_weather_locations)} extreme weather events found")
    
    return extreme_weather_locations

def save_weather_data(weather_data):
    """Save weather data to database"""
    if not sb_available() or not weather_data:
        return None
    
    try:
        payload = {
            'location': weather_data['location'],
            'temperature': weather_data['temperature'],
            'humidity': weather_data['humidity'],
            'wind_speed': weather_data['wind_speed'],
            'weather_condition': weather_data['weather_condition'],
            'is_extreme': weather_data['is_extreme'],
            'weather_alert': weather_data['weather_alert']
        }
        
        result = supabase.table('weather_data').insert(payload).execute()
        if result and result.data:
            weather_id = result.data[0]['id']
            
            # If extreme weather detected, automatically create an announcement
            if weather_data['is_extreme']:
                create_weather_alert_announcement(weather_data, weather_id)
            
            return weather_id
        return None
        
    except Exception as e:
        print(f"Error saving weather data: {e}")
        return None

def create_weather_alert_announcement(weather_data, weather_id):
    """Automatically create a weather alert announcement"""
    if not sb_available():
        return None
    
    try:
        # Determine severity based on weather conditions
        severity = "critical"
        if weather_data['weather_condition'] in ['Thunderstorm', 'Tornado', 'Hurricane']:
            severity = "critical"
        elif weather_data['temperature'] and (weather_data['temperature'] > 40 or weather_data['temperature'] < -10):
            severity = "critical"
        elif weather_data['wind_speed'] and weather_data['wind_speed'] > 20:
            severity = "high"
        else:
            severity = "high"
        
        # Create announcement title and description
        title = f"Extreme Weather Alert - {weather_data['location']}"
        description = f"Extreme weather conditions detected in {weather_data['location']}. "
        
        if weather_data['weather_alert']:
            description += f"Alert: {weather_data['weather_alert']}. "
        
        description += f"Current conditions: {weather_data['weather_condition']}, Temperature: {weather_data['temperature']}°C"
        if weather_data['wind_speed']:
            description += f", Wind Speed: {weather_data['wind_speed']} m/s"
        
        description += ". Please take necessary precautions and stay safe."
        
        # Get admin user ID (you might want to store this in environment or config)
        admin_resp = supabase.table("users").select("id").eq("role", "admin").limit(1).execute()
        admin_id = admin_resp.data[0]['id'] if admin_resp and admin_resp.data else None
        
        if admin_id:
            payload = {
                "admin_id": admin_id,
                "title": title,
                "description": description,
                "severity": severity,
                "is_weather_alert": True,
                "weather_data_id": weather_id
            }
            
            ann_result = supabase.table("announcements").insert(payload).execute()
            if ann_result and ann_result.data:
                print(f"Auto-created weather alert announcement for {weather_data['location']}")
                return ann_result.data[0]['id']
        
        return None
        
    except Exception as e:
        print(f"Error creating weather alert announcement: {e}")
        return None

def check_and_update_weather_alerts():
    """Check existing weather alerts and remove them if weather has returned to normal"""
    if not sb_available():
        return
    
    try:
        # Get all weather alert announcements
        ann_resp = supabase.table("announcements").select(", weather_data()").eq("is_weather_alert", True).execute()
        weather_alerts = ann_resp.data if ann_resp and ann_resp.data else []
        
        if not weather_alerts:
            return
        
        # Use ThreadPoolExecutor for parallel checking
        with ThreadPoolExecutor(max_workers=5) as executor:
            def check_single_alert(alert):
                if alert.get('weather_data_id') and alert.get('weather_data'):
                    weather_data = alert['weather_data']
                    location = weather_data.get('location')
                    
                    if location:
                        # Fetch current weather for this location
                        current_weather = fetch_weather_data(location)
                        
                        if current_weather and not current_weather['is_extreme']:
                            # Weather has returned to normal, remove the alert
                            try:
                                supabase.table("announcements").delete().eq("id", alert['id']).execute()
                                print(f"Removed weather alert for {location} - weather returned to normal")
                                return True
                            except Exception as e:
                                print(f"Error removing weather alert for {location}: {e}")
                return False
            
            # Submit all alert checking tasks
            futures = [executor.submit(check_single_alert, alert) for alert in weather_alerts]
            
            # Wait for all to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error in alert checking: {e}")
        
    except Exception as e:
        print(f"Error checking weather alerts: {e}")

def delete_announcement(announcement_id):
    """Delete an announcement by ID"""
    if not sb_available():
        return False
    
    try:
        supabase.table("announcements").delete().eq("id", announcement_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting announcement: {e}")
        return False

def delete_incident(incident_id):
    """Delete an incident by ID"""
    if not sb_available():
        return False
    
    try:
        supabase.table("incidents").delete().eq("id", incident_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting incident: {e}")
        return False

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        # Simple rate limiting check
        client_ip = request.remote_addr
        current_time = time.time()
        
        if client_ip in signup_attempts:
            last_attempt = signup_attempts[client_ip]
            if current_time - last_attempt < 60:  # 60 seconds cooldown
                remaining_time = int(60 - (current_time - last_attempt))
                flash(f"Too many signup attempts. Please wait {remaining_time} seconds before trying again.", "warning")
                return redirect(url_for("signup"))
        
        signup_attempts[client_ip] = current_time
        
        name = request.form["fullname"].strip()
        email = request.form["email"].strip().lower()
        phone = request.form["phone"].strip()
        place = request.form.get("place", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        password = request.form["password"]
        role = request.form.get("role", "user")  # Default to user role
        
        if not sb_available():
            flash("Database is not configured.", "danger")
            return redirect(url_for("signup"))

        # Create user in Supabase Auth
        try:
            auth_res = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"name": name, "phone": phone, "role": role}}
            })
            if not auth_res or not auth_res.user:
                flash("Could not create account. Please try again.", "danger")
                return redirect(url_for("signup"))
            user_id = auth_res.user.id
        except Exception as err:
            error_msg = str(err)
            if "rate limit" in error_msg.lower() or "security purposes" in error_msg.lower():
                flash("Too many signup attempts. Please wait 1 minute before trying again.", "warning")
            elif "already registered" in error_msg.lower():
                flash("This email is already registered. Please sign in instead.", "info")
            else:
                flash("Signup failed. Please try again later.", "danger")
            return redirect(url_for("signup"))

        # Upsert profile in public.users
        try:
            payload = {
                "id": user_id,
                "name": name,
                "email": email,
                "phone": phone,
                "place": place,
                "city": city,
                "state": state,
                "pincode": pincode,
                "role": role,
            }
            supabase.table("users").upsert(payload, on_conflict="id").execute()
            flash("Signup successful! Please log in.", "success")
        except Exception as err:
            flash(f"Profile save error: {err}", "warning")
        
        return redirect(url_for("signin"))

    return render_template("signup.html")

@app.route("/view_data")
def view_data():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))

    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("dashboard"))

    data_type = request.args.get("type", "incidents").lower()
    user_id = session.get("user_id")
    rows = []
    columns = []

    try:
        if data_type == "donations":
            resp = supabase.table("donations").select("id, amount, method, timestamp").eq("user_id", user_id).order("timestamp", desc=True).execute()
            rows = resp.data if resp and resp.data else []
            columns = ["id", "amount", "method", "timestamp"]
        else:
            resp = supabase.table("incidents").select("id, location, description, status, timestamp").eq("user_id", user_id).order("timestamp", desc=True).execute()
            rows = resp.data if resp and resp.data else []
            columns = ["id", "location", "description", "status", "timestamp"]
    except Exception as err:
        flash(f"Error fetching data: {err}", "danger")
        return redirect(url_for("dashboard"))

    return render_template("view_data.html", data_type=data_type, columns=columns, rows=rows)

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if "user" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email_or_phone = request.form["email_or_phone"].strip()
        password = request.form["password"]

        if not sb_available():
            flash("Database is not configured.", "danger")
            return redirect(url_for("signin"))

        # Supabase Auth supports email/password; if phone provided, we look up email by phone
        try:
            email_to_use = email_or_phone
            if "@" not in email_or_phone:
                # Lookup email by phone from profiles
                resp = supabase.table("users").select("email").eq("phone", email_or_phone).limit(1).execute()
                rows = resp.data if resp else []
                if not rows:
                    flash("User not found", "danger")
                    return redirect(url_for("signin"))
                email_to_use = rows[0]["email"].lower()

            auth_res = supabase.auth.sign_in_with_password({
                "email": email_to_use.lower(),
                "password": password
            })
            if not auth_res or not auth_res.user:
                flash("Invalid credentials", "danger")
                return redirect(url_for("signin"))
            # Load or create profile for display name and role (self-healing)
            user_id = auth_res.user.id
            prof = supabase.table("users").select("id,name,email,role").eq("id", user_id).limit(1).execute()
            if not prof or not prof.data:
                try:
                    meta = auth_res.user.user_metadata or {}
                    payload = {
                        "id": user_id,
                        "name": meta.get("name") or "User",
                        "email": auth_res.user.email,
                        "phone": meta.get("phone") or "",
                        "role": (meta.get("role") or "user").lower(),
                    }
                    supabase.table("users").upsert(payload, on_conflict="id").execute()
                    prof = supabase.table("users").select("id,name,email,role").eq("id", user_id).limit(1).execute()
                except Exception:
                    pass
            profile = prof.data[0] if prof and prof.data else {"name": auth_res.user.user_metadata.get("name", "User"), "email": auth_res.user.email, "role": (auth_res.user.user_metadata.get("role") or "user").lower()}

            first_name = (profile.get("name") or "").split()[0] or "User"
            user_role = profile.get("role", "user")
            session["user"] = first_name
            session["user_id"] = user_id
            session["user_email"] = profile.get("email")
            session["user_role"] = user_role
            flash("Signed in successfully!", "success")
            return redirect(url_for("dashboard"))
        except Exception as err:
            flash(f"Sign in error: {err}", "danger")
            return redirect(url_for("signin"))

    return render_template("signin.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    
    user_role = session.get("user_role", "user")
    
    if user_role == "admin":
        return redirect(url_for("admin_dashboard"))
    elif user_role == "government":
        return redirect(url_for("government_dashboard"))
    elif user_role == "emergency":
        return redirect(url_for("emergency_dashboard"))
    else:
        # Get recent announcements for user dashboard
        announcements = []
        weather_alerts = []
        if sb_available():
            try:
                # Check and update weather alerts (remove resolved ones)
                check_and_update_weather_alerts()
                
                # Get all recent announcements
                ann_resp = supabase.table("announcements").select(", weather_data!announcements_weather_data_id_fkey()").order("timestamp", desc=True).limit(5).execute()
                announcements = ann_resp.data if ann_resp and ann_resp.data else []
                
                # Filter weather alerts
                weather_alerts = [ann for ann in announcements if ann.get('is_weather_alert')]
            except Exception as err:
                print(f"Error loading announcements: {err}")
        
        return render_template("dashboard.html", user=session["user"], announcements=announcements, weather_alerts=weather_alerts)

@app.route("/admin_dashboard")
@require_role("admin")
def admin_dashboard():
    # Get incidents for admin to review
    incidents = []
    announcements = []
    weather_data = []
    if sb_available():
        try:
            # Check and update weather alerts (remove resolved ones)
            check_and_update_weather_alerts()
            
            inc_resp = supabase.table("incidents").select("*").order("timestamp", desc=True).limit(10).execute()
            incidents = inc_resp.data if inc_resp and inc_resp.data else []
            
            ann_resp = supabase.table("announcements").select("*").order("timestamp", desc=True).limit(5).execute()
            announcements = ann_resp.data if ann_resp and ann_resp.data else []
            
            # Get recent weather data, prioritizing extreme weather and most recent
            weather_resp = supabase.table("weather_data").select("*").order("fetched_at", desc=True).order("is_extreme", desc=True).limit(15).execute()
            weather_data = weather_resp.data if weather_resp and weather_resp.data else []
        except Exception as err:
            flash(f"Error loading data: {err}", "danger")
    
    return render_template("admin_dashboard.html", incidents=incidents, announcements=announcements, weather_data=weather_data)

@app.route("/fetch_weather", methods=["POST"])
@require_role("admin")
def fetch_weather():
    """Fetch weather data for a location"""
    location = request.form.get("location")
    
    if not location:
        flash("Location is required", "danger")
        return redirect(url_for("admin_dashboard"))
    
    weather_data = fetch_weather_data(location)
    
    if weather_data:
        # Save to database
        weather_id = save_weather_data(weather_data)
        if weather_id:
            flash(f"Weather data fetched for {location} successfully!", "success")
        else:
            flash("Weather data fetched but could not save to database", "warning")
    else:
        flash(f"Could not fetch weather data for {location}", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/fetch_extreme_weather", methods=["POST"])
@require_role("admin")
def fetch_extreme_weather():
    """Fetch weather data for multiple Indian cities and show only extreme weather"""
    flash("Fetching weather data for all monitored Indian cities...", "info")
    
    extreme_weather_locations = fetch_multiple_locations_weather()
    
    if extreme_weather_locations:
        # Save all extreme weather data to database
        saved_count = 0
        for weather_data in extreme_weather_locations:
            weather_id = save_weather_data(weather_data)
            if weather_id:
                saved_count += 1
        
        flash(f"✅ Scan completed! Found {len(extreme_weather_locations)} Indian cities with extreme weather. {saved_count} records saved.", "success")
    else:
        flash("✅ Scan completed! No extreme weather conditions detected in monitored Indian cities.", "info")
    
    # Redirect to admin dashboard with fresh data
    return redirect(url_for("admin_dashboard"))

@app.route("/check_weather_alerts", methods=["POST"])
@require_role("admin")
def check_weather_alerts():
    """Check and update weather alerts - remove alerts where weather has returned to normal"""
    flash("Checking weather alerts and removing resolved ones...", "info")
    
    check_and_update_weather_alerts()
    
    flash("Weather alert check completed!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/delete_announcement/<int:announcement_id>", methods=["POST"])
@require_role("admin")
def delete_announcement_route(announcement_id):
    """Delete an announcement"""
    if delete_announcement(announcement_id):
        flash("Announcement deleted successfully!", "success")
    else:
        flash("Failed to delete announcement.", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/delete_incident/<int:incident_id>", methods=["POST"])
@require_role("admin")
def delete_incident_route(incident_id):
    """Delete an incident"""
    if delete_incident(incident_id):
        flash("Incident deleted successfully!", "success")
    else:
        flash("Failed to delete incident.", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/government_dashboard")
@require_role("government")
def government_dashboard():
    # Get requests for government to handle
    requests = []
    team_allocations = []
    emergency_assignments = []
    emergency_heads = []
    emergency_units = []
    if sb_available():
        try:
            req_resp = supabase.table("requests").select("id, incident_id, status, timestamp, incidents(*)").order("timestamp", desc=True).limit(50).execute()
            requests = req_resp.data if req_resp and req_resp.data else []
            
            team_resp = supabase.table("team_allocations").select("*").order("assigned_at", desc=True).limit(10).execute()
            team_allocations = team_resp.data if team_resp and team_resp.data else []
            # Recent emergency assignments (single requests relation with nested incidents)
            em_resp = supabase.table("emergency_assignments").select("*, requests(id, incident_id, incidents(location))").order("assigned_at", desc=True).limit(10).execute()
            emergency_assignments = em_resp.data if em_resp and em_resp.data else []
            # Emergency heads and units (tolerate projects without is_emergency_head column)
            try:
                heads_resp = supabase.table("users").select("id, name, email, is_emergency_head").eq("role", "emergency").eq("is_emergency_head", True).execute()
                emergency_heads = heads_resp.data if heads_resp and heads_resp.data else []
            except Exception:
                # Fallback: if the column doesn't exist yet, list all emergency users as selectable heads
                heads_resp = supabase.table("users").select("id, name, email").eq("role", "emergency").execute()
                emergency_heads = heads_resp.data if heads_resp and heads_resp.data else []
            units_resp = supabase.table("emergency_units").select("*, users(name)").order("unit_name").execute()
            emergency_units = units_resp.data if units_resp and units_resp.data else []
        except Exception as err:
            flash(f"Error loading data: {err}", "danger")
    
    return render_template("government_dashboard.html", requests=requests, team_allocations=team_allocations, emergency_assignments=emergency_assignments, emergency_heads=emergency_heads, emergency_units=emergency_units)

@app.route("/report_incident", methods=["GET", "POST"])
def report_incident():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    
    if request.method == "POST":
        location = request.form["location"].strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        cause = request.form.get("cause", "").strip()
        pincode = request.form.get("pincode", "").strip()
        description = request.form["description"].strip()
        
        if not sb_available():
            flash("Database is not configured.", "danger")
            return redirect(url_for("report_incident"))

        if not pincode:
            flash("Pincode is required.", "danger")
            return redirect(url_for("report_incident"))

        try:
            payload = {
                "user_id": session["user_id"],
                "location": location,
                "address": address or None,
                "city": city or None,
                "state": state or None,
                "cause": cause or None,
                "pincode": pincode,
                "description": description,
            }
            ins = supabase.table("incidents").insert(payload).execute()
            if not ins or not ins.data:
                flash("Could not report incident.", "danger")
            else:
                flash("Incident reported successfully!", "success")
        except Exception as err:
            flash(f"Error reporting incident: {err}", "danger")
        
        return redirect(url_for("report_incident"))
    
    return render_template("report_incident.html")

@app.route("/medical", methods=["GET", "POST"])
def medical():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))

    if request.method == "POST":
        request_type = request.form.get("request_type")
        description = request.form.get("description")
        urgency = request.form.get("urgency")

        if not sb_available():
            flash("Database is not configured.", "danger")
            return redirect(url_for("medical"))

        try:
            payload = {
                "user_id": session["user_id"],
                "request_type": request_type,
                "description": description,
                "urgency": urgency,
            }
            ins = supabase.table("medical_requests").insert(payload).execute()
            if not ins or not ins.data:
                flash("Could not submit request.", "danger")
            else:
                flash("Medical request submitted!", "success")
        except Exception as err:
            flash(f"Error submitting request: {err}", "danger")
        return redirect(url_for("medical"))

    return render_template("medical.html")

@app.route("/donate", methods=["GET", "POST"])
def donate():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    
    if request.method == "POST":
        amount = request.form["amount"]
        method = request.form["payment_method"]
        
        if not sb_available():
            flash("Database is not configured.", "danger")
            return redirect(url_for("donate"))

        try:
            payload = {
                "user_id": session["user_id"],
                "amount": float(amount),
                "method": method,
            }
            ins = supabase.table("donations").insert(payload).execute()
            if not ins or not ins.data:
                flash("Error processing donation.", "danger")
            else:
                flash("Thank you for your donation!", "success")
        except Exception as err:
            flash(f"Error processing donation: {err}", "danger")
        
        return redirect(url_for("donate"))
    
    return render_template("donate.html")

@app.route("/forward_incident", methods=["POST"])
@require_role("admin")
def forward_incident():
    incident_id = request.form.get("incident_id")
    if not incident_id:
        flash("Invalid incident ID", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("admin_dashboard"))
    
    try:
        payload = {
            "admin_id": session["user_id"],
            "incident_id": int(incident_id),
        }
        ins = supabase.table("requests").insert(payload).execute()
        if not ins or not ins.data:
            flash("Could not forward incident.", "danger")
        else:
            flash("Incident forwarded to government successfully!", "success")
    except Exception as err:
        flash(f"Error forwarding incident: {err}", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/create_announcement", methods=["POST"])
@require_role("admin")
def create_announcement():
    title = request.form.get("title")
    description = request.form.get("description")
    severity = request.form.get("severity", "medium")
    weather_data_id = request.form.get("weather_data_id")
    is_weather_alert = request.form.get("is_weather_alert") == "on"
    
    if not title or not description:
        flash("Title and description are required", "danger")
        return redirect(url_for("admin_dashboard"))
    
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("admin_dashboard"))
    
    try:
        payload = {
            "admin_id": session["user_id"],
            "title": title,
            "description": description,
            "severity": severity,
            "is_weather_alert": is_weather_alert,
        }
        
        # Add weather data reference if provided
        if weather_data_id:
            payload["weather_data_id"] = int(weather_data_id)
        
        ins = supabase.table("announcements").insert(payload).execute()
        if not ins or not ins.data:
            flash("Could not create announcement.", "danger")
        else:
            flash("Announcement created successfully!", "success")
    except Exception as err:
        flash(f"Error creating announcement: {err}", "danger")
    
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/data_view")
@require_role("admin")
def admin_data_view():
    """Admin route to view all database data"""
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("admin_dashboard"))
    
    try:
        # Fetch all data from Supabase
        incidents = []
        donations = []
        users = []
        announcements = []
        medical_requests = []
        
        # Get incidents
        inc_resp = supabase.table("incidents").select("*").order("timestamp", desc=True).execute()
        incidents = inc_resp.data if inc_resp and inc_resp.data else []
        
        # Get donations
        don_resp = supabase.table("donations").select("*").order("timestamp", desc=True).execute()
        donations = don_resp.data if don_resp and don_resp.data else []
        
        # Get users (excluding sensitive info)
        usr_resp = supabase.table("users").select("id, name, email, role, created_at").order("created_at", desc=True).execute()
        users = usr_resp.data if usr_resp and usr_resp.data else []
        
        # Get announcements
        ann_resp = supabase.table("announcements").select("*").order("timestamp", desc=True).execute()
        announcements = ann_resp.data if ann_resp and ann_resp.data else []
        
        # Get medical requests
        med_resp = supabase.table("medical_requests").select("*").order("created_at", desc=True).execute()
        medical_requests = med_resp.data if med_resp and med_resp.data else []
        
        return render_template("admin_data_view.html", 
                             incidents=incidents, 
                             donations=donations, 
                             users=users, 
                             announcements=announcements,
                             medical_requests=medical_requests)
        
    except Exception as err:
        flash(f"Error fetching data: {err}", "danger")
        return redirect(url_for("admin_dashboard"))

@app.route("/allocate_team", methods=["POST"])
@require_role("government")
def allocate_team():
    request_id = request.form.get("request_id")
    team_name = request.form.get("team_name")
    
    if not request_id or not team_name:
        flash("Request ID and team name are required", "danger")
        return redirect(url_for("government_dashboard"))
    
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("government_dashboard"))
    
    try:
        payload = {
            "gov_id": session["user_id"],
            "request_id": int(request_id),
            "team_name": team_name,
        }
        ins = supabase.table("team_allocations").insert(payload).execute()
        if not ins or not ins.data:
            flash("Could not allocate team.", "danger")
        else:
            flash("Team allocated successfully!", "success")
    except Exception as err:
        flash(f"Error allocating team: {err}", "danger")
    
    return redirect(url_for("government_dashboard"))

@app.route("/notify_emergency_head", methods=["POST"])
@require_role("government")
def notify_emergency_head():
    request_id = request.form.get("request_id")
    if not request_id:
        flash("Request is required", "danger")
        return redirect(url_for("government_dashboard"))
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("government_dashboard"))
    try:
        # Determine recipients without requiring email
        # 1) Heads
        heads = []
        try:
            resp = supabase.table("users").select("id, role, is_emergency_head").execute()
            rows = resp.data or []
            # prefer explicit heads
            for r in rows:
                if r.get("is_emergency_head"):
                    heads.append({"id": r.get("id")})
            # then add any role containing 'emergency'
            if not heads:
                for r in rows:
                    role_val = (r.get("role") or "").lower()
                    if "emergency" in role_val:
                        heads.append({"id": r.get("id")})
        except Exception:
            heads = []
        if not heads:
            # 2) fallback: notify owners of units
            try:
                unit_resp = supabase.table("emergency_units").select("head_id").execute()
                hid_set = {}
                for r in (unit_resp.data or []):
                    hid = r.get("head_id")
                    if hid:
                        hid_set[hid] = True
                heads = [{"id": k} for k in hid_set.keys()]
            except Exception:
                heads = []
        if not heads:
            flash("No emergency team users found to notify.", "danger")
            return redirect(url_for("government_dashboard"))
        # Insert one notification per head
        payloads = [
            {"request_id": int(request_id), "gov_id": session.get("user_id"), "head_id": h["id"], "status": "Pending"}
            for h in heads
        ]
        supabase.table("emergency_notifications").insert(payloads).execute()
        flash("Notification sent to emergency teams.", "success")
    except Exception as err:
        flash(f"Error sending notification: {err}", "danger")
    return redirect(url_for("government_dashboard"))

@app.route("/emergency_dashboard")
@require_role("emergency")
def emergency_dashboard():
    assignments = []
    notifications = []
    my_units = []
    updates_map = {}
    if sb_available():
        try:
            # Assignments for this emergency team user
            asg_resp = supabase.table("emergency_assignments").select("*, requests(incidents(location, description))").eq("team_lead_id", session.get("user_id")).order("assigned_at", desc=True).execute()
            assignments = asg_resp.data if asg_resp and asg_resp.data else []
            # Notifications to me if I am head
            notif_resp = supabase.table("emergency_notifications").select("*, requests(incidents(location, description))").eq("head_id", session.get("user_id")).order("created_at", desc=True).execute()
            notifications = notif_resp.data if notif_resp and notif_resp.data else []
            # Units under me if I am head
            units_resp = supabase.table("emergency_units").select("*").eq("head_id", session.get("user_id")).order("unit_name").execute()
            my_units = units_resp.data if units_resp and units_resp.data else []
            # Recent updates per assignment
            for a in assignments:
                up_resp = supabase.table("emergency_updates").select("*").eq("assignment_id", a.get("id")).order("created_at", desc=True).limit(3).execute()
                updates_map[a.get("id")] = up_resp.data if up_resp and up_resp.data else []
        except Exception as err:
            flash(f"Error loading assignments: {err}", "danger")
    return render_template("emergency_dashboard.html", assignments=assignments, updates_map=updates_map, notifications=notifications, my_units=my_units)

@app.route("/create_unit", methods=["POST"])
@require_role("emergency")
def create_unit():
    unit_name = request.form.get("unit_name", "").strip()
    if not unit_name:
        flash("Team name is required.", "danger")
        return redirect(url_for("emergency_dashboard"))
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("emergency_dashboard"))
    try:
        categories = ["Rescue", "Escort", "Medical", "ResourceCollector"]
        payloads = [{
            "head_id": session.get("user_id"),
            "unit_name": unit_name,
            "unit_category": cat,
            "status": "Free",
        } for cat in categories]
        supabase.table("emergency_units").insert(payloads).execute()
        flash("Team created with Rescue, Escort, Medical, and ResourceCollector subteams.", "success")
    except Exception as err:
        flash(f"Error creating unit: {err}", "danger")
    return redirect(url_for("emergency_dashboard"))

@app.route("/head_assign_unit", methods=["POST"])
@require_role("emergency")
def head_assign_unit():
    # Only heads should use this: assign a free unit to a request → creates assignment with the unit name in notes
    request_id = request.form.get("request_id")
    unit_id = request.form.get("unit_id")
    if not all([request_id, unit_id]):
        flash("Request and unit are required", "danger")
        return redirect(url_for("emergency_dashboard"))
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("emergency_dashboard"))
    try:
        # Verify unit belongs to me and is Free
        u_resp = supabase.table("emergency_units").select("*, users(id)").eq("id", int(unit_id)).limit(1).execute()
        if not u_resp or not u_resp.data:
            flash("Unit not found", "danger")
            return redirect(url_for("emergency_dashboard"))
        unit = u_resp.data[0]
        # Mark unit Busy
        supabase.table("emergency_units").update({"status": "Busy", "last_update": None}).eq("id", int(unit_id)).execute()
        # Fetch incident location
        req_resp = supabase.table("requests").select("incident_id").eq("id", int(request_id)).limit(1).execute()
        incident_id = req_resp.data[0]["incident_id"] if req_resp and req_resp.data else None
        loc_text = None
        if incident_id:
            inc_resp = supabase.table("incidents").select("location").eq("id", incident_id).limit(1).execute()
            loc_text = inc_resp.data[0]["location"] if inc_resp and inc_resp.data else None
        # Create assignment under my user as lead
        payload = {
            "request_id": int(request_id),
            "team_name": unit["unit_name"],
            "team_type": unit["unit_category"],
            "team_lead_id": session.get("user_id"),
            "location_text": loc_text,
            "notes": f"Assigned unit #{unit['id']}",
            "status": "Assigned",
        }
        supabase.table("emergency_assignments").insert(payload).execute()
        # Mark notification acknowledged if exists
        supabase.table("emergency_notifications").update({"status": "Acknowledged"}).eq("request_id", int(request_id)).eq("head_id", session.get("user_id")).execute()
        flash("Unit assigned and government notified.", "success")
    except Exception as err:
        flash(f"Error assigning unit: {err}", "danger")
    return redirect(url_for("emergency_dashboard"))

@app.route("/emergency_update", methods=["POST"])
@require_role("emergency")
def emergency_update():
    assignment_id = request.form.get("assignment_id")
    status = request.form.get("status")
    reached = request.form.get("reached") == "on"
    rescued_count = request.form.get("rescued_count")
    need_more_support = request.form.get("need_more_support") == "on"
    severity = request.form.get("severity")
    critical_count = request.form.get("critical_count")
    need_medical = request.form.get("need_medical") == "on"
    message = request.form.get("message")
    if not assignment_id:
        flash("Invalid assignment", "danger")
        return redirect(url_for("emergency_dashboard"))
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("emergency_dashboard"))
    try:
        payload = {
            "assignment_id": int(assignment_id),
            "author_id": session.get("user_id"),
            "reached": reached,
            "rescued_count": int(rescued_count) if rescued_count else None,
            "need_more_support": need_more_support,
            "severity": severity or None,
            "critical_count": int(critical_count) if critical_count else None,
            "need_medical": need_medical,
            "message": message or None,
        }
        supabase.table("emergency_updates").insert(payload).execute()
        # Optionally, update assignment status
        if status:
            supabase.table("emergency_assignments").update({"status": status}).eq("id", int(assignment_id)).execute()
        flash("Update sent to government.", "success")
    except Exception as err:
        flash(f"Error sending update: {err}", "danger")
    return redirect(url_for("emergency_dashboard"))

@app.route("/toggle_unit_status", methods=["POST"])
@require_role("emergency")
def toggle_unit_status():
    unit_id = request.form.get("unit_id")
    if not unit_id:
        flash("Invalid unit", "danger")
        return redirect(url_for("emergency_dashboard"))
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("emergency_dashboard"))
    try:
        # Ensure unit belongs to me
        u_resp = supabase.table("emergency_units").select("id, head_id, status").eq("id", int(unit_id)).limit(1).execute()
        if not u_resp or not u_resp.data:
            flash("Unit not found", "danger")
            return redirect(url_for("emergency_dashboard"))
        unit = u_resp.data[0]
        # Toggle
        new_status = "Free" if unit.get("status") != "Free" else "Busy"
        supabase.table("emergency_units").update({"status": new_status}).eq("id", int(unit_id)).execute()
        flash("Unit status updated.", "success")
    except Exception as err:
        flash(f"Error updating unit: {err}", "danger")
    return redirect(url_for("emergency_dashboard"))

@app.route("/gov/delete_incident/<int:incident_id>", methods=["POST"])
@require_role("government")
def gov_delete_incident(incident_id: int):
    if not sb_available():
        flash("Database is not configured.", "danger")
        return redirect(url_for("government_dashboard"))
    try:
        supabase.table("incidents").delete().eq("id", int(incident_id)).execute()
        flash("Incident deleted.", "success")
    except Exception as err:
        flash(f"Error deleting incident: {err}", "danger")
    return redirect(url_for("government_dashboard"))

@app.route("/nearby_shelters", methods=["GET", "POST"])
def nearby_shelters():
    shelters = []
    user_location = ""
    
    if request.method == "POST":
        user_location = request.form.get("location")

        if not user_location:
            flash("Please enter a location", "warning")
            return redirect(url_for("nearby_shelters"))

        try:
            # Get user coordinates using geopy
            geolocator = Nominatim(user_agent="disaster_management")
            location = geolocator.geocode(user_location)
            
            if not location:
                flash("Could not find the location. Please try a different address.", "warning")
                return redirect(url_for("nearby_shelters"))
            
            user_lat, user_lon = location.latitude, location.longitude
            
            # Search for shelters using Overpass API (OpenStreetMap)
            api = overpy.Overpass()
            
            # Query for emergency shelters, community centers, schools, etc.
            query = f"""
            [out:json][timeout:25];
            (
              node["amenity"="shelter"](around:10000,{user_lat},{user_lon});
              node["building"="school"](around:10000,{user_lat},{user_lon});
              node["amenity"="community_centre"](around:10000,{user_lat},{user_lon});
              node["building"="civic"](around:10000,{user_lat},{user_lon});
              way["amenity"="shelter"](around:10000,{user_lat},{user_lon});
              way["building"="school"](around:10000,{user_lat},{user_lon});
              way["amenity"="community_centre"](around:10000,{user_lat},{user_lon});
              way["building"="civic"](around:10000,{user_lat},{user_lon});
            );
            out body;
            >;
            out skel qt;
            """
            
            result = api.query(query)
            
            # Process results
            for node in result.nodes:
                shelter_name = node.tags.get("name", "Emergency Shelter")
                shelter_type = node.tags.get("amenity", node.tags.get("building", "shelter"))
                
                # Calculate distance
                shelter_lat = float(node.lat)
                shelter_lon = float(node.lon)
                distance = geodesic((user_lat, user_lon), (shelter_lat, shelter_lon)).kilometers
                
                shelters.append({
                    "name": shelter_name,
                    "type": shelter_type,
                    "address": f"Lat: {shelter_lat:.4f}, Lon: {shelter_lon:.4f}",
                    "distance": f"{distance:.1f} km",
                    "lat": shelter_lat,
                    "lon": shelter_lon,
                    "capacity": "Contact for details"
                })
            
            # Also get shelters from database as backup
            if sb_available():
                try:
                    resp = supabase.table("shelters").select("*").execute()
                    db_shelters = resp.data if resp and resp.data else []
                    
                    for shelter in db_shelters:
                        # Calculate distance to database shelter
                        shelter_lat = 0  # You'd need to add lat/lon to your database
                        shelter_lon = 0
                        distance = geodesic((user_lat, user_lon), (shelter_lat, shelter_lon)).kilometers if shelter_lat != 0 else "N/A"
                        
                        shelters.append({
                            "name": shelter["name"],
                            "type": "Database Shelter",
                            "address": shelter["location"],
                            "capacity": f"{shelter['available']}/{shelter['capacity']}",
                            "distance": f"{distance:.1f} km" if distance != "N/A" else "N/A",
                            "lat": shelter_lat,
                            "lon": shelter_lon
                        })
                except Exception as err:
                    pass  # Continue with OSM results
            
            # Sort by distance
            shelters.sort(key=lambda x: float(x["distance"].split()[0]) if x["distance"] != "N/A" else float('inf'))
            
            if not shelters:
                flash("No shelters found nearby. Try expanding your search area.", "info")
            
        except Exception as err:
            flash(f"Error fetching shelters: {err}", "danger")
            # Fallback to database shelters
            if sb_available():
                try:
                    resp = supabase.table("shelters").select("*").execute()
                    db_shelters = resp.data if resp and resp.data else []
                    
                    for shelter in db_shelters:
                        shelters.append({
                            "name": shelter["name"],
                            "type": "Database Shelter",
                            "address": shelter["location"],
                            "capacity": f"{shelter['available']}/{shelter['capacity']}",
                            "distance": "N/A",
                            "lat": 0,
                            "lon": 0
                        })
                except Exception:
                    pass

    return render_template("nearby_shelters.html", shelters=shelters, user_location=user_location)

@app.route("/announcements")
def announcements():
    if "user" not in session:
        flash("Please sign in first!", "warning")
        return redirect(url_for("signin"))
    
    announcements = []
    if sb_available():
        try:
            # Check and update weather alerts (remove resolved ones)
            check_and_update_weather_alerts()
            
            resp = supabase.table("announcements").select(", weather_data!announcements_weather_data_id_fkey()").order("timestamp", desc=True).execute()
            announcements = resp.data if resp and resp.data else []
        except Exception as err:
            flash(f"Error fetching announcements: {err}", "danger")
    
    return render_template("announcements.html", announcements=announcements)

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    session.pop("user_email", None)
    session.pop("user_role", None)
    try:
        if sb_available():
            supabase.auth.sign_out()
    except Exception:
        pass
    flash("Logged out successfully!", "info")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)