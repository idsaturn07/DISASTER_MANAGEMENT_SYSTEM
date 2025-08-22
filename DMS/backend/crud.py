from sqlalchemy.orm import Session
import models, schemas
from utils.geo import geocode_address, distance_km
from utils.alerts import send_sms
import auth.utils_auth as auth_utils
from typing import List, Tuple

def create_user(db: Session, user: schemas.UserCreate):
    exists = db.query(models.User).filter(
        (models.User.phone == user.phone) | (models.User.email == user.email)
    ).first()
    if exists:
        raise ValueError("User with this phone/email already exists")
    
    full_address = f"{user.address}, {user.city}, {user.state}, {user.pincode}"
    coords = geocode_address(full_address)
    lat = lon = None
    if coords:
        lat, lon = coords

    db_user = models.User(
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        address=user.address,
        city=user.city,
        state=user.state,
        pincode=user.pincode,
        password_hash=auth_utils.hash_password(user.password),
        lat=lat,
        lon=lon
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_users_in_radius(db: Session, center_lat: float, center_lon: float, km_radius: float):
    users = db.query(models.User).filter(models.User.lat.isnot(None), models.User.lon.isnot(None)).all()
    nearby = []
    center = (center_lat, center_lon)
    for u in users:
        d = distance_km(center, (u.lat, u.lon))
        if d <= km_radius:
            nearby.append((u, d))
    return nearby

def create_disaster(db: Session, data: schemas.DisasterCreate):
    full_address = f"{data.address}, {data.city}, {data.state}, {data.pincode}"
    coords = geocode_address(full_address)
    if not coords:
        raise ValueError("Could not geocode address")
    lat, lon = coords
    dr = models.DisasterReport(
        reporter_id=data.reporter_id,
        type=data.type,
        description=data.description,
        address=data.address,
        city=data.city,
        state=data.state,
        pincode=data.pincode,
        lat=lat,
        lon=lon
    )
    db.add(dr)
    db.commit()
    db.refresh(dr)
    return dr

def send_alerts_for_disaster(db: Session, disaster: models.DisasterReport, radius_km: float=10.0, message_extra: str=""):
    nearby = get_users_in_radius(db, disaster.lat, disaster.lon, radius_km)
    count = 0
    for user, dist in nearby:
        msg = f"🚨 DISASTER ALERT: {disaster.type} reported at {disaster.address}, {disaster.city}. {message_extra}"
        send_sms(user.phone, msg)
        count += 1
    return count

def find_nearest_available_team(db: Session, lat: float, lon: float):
    teams = db.query(models.RescueTeam).filter(
        models.RescueTeam.available == True, 
        models.RescueTeam.lat.isnot(None), 
        models.RescueTeam.lon.isnot(None)
    ).all()
    if not teams:
        return None
    best = None
    best_d = float('inf')
    for t in teams:
        d = distance_km((lat, lon), (t.lat, t.lon))
        if d < best_d:
            best_d = d
            best = t
    return best

def assign_team_to_disaster(db: Session, disaster_id: int):
    dr = db.query(models.DisasterReport).filter(models.DisasterReport.id==disaster_id).first()
    if not dr:
        return None
    team = find_nearest_available_team(db, dr.lat, dr.lon)
    if not team:
        return None
    team.available = False
    dr.assigned_team_id = team.id
    db.commit()
    db.refresh(dr)
    db.refresh(team)
    return team

def get_nearby_safe_locations(db: Session, lat: float, lon: float, radius_km: float = 10.0):
    sl = db.query(models.SafeLocation).all()
    center = (lat, lon)
    res = []
    for s in sl:
        d = distance_km(center, (s.lat, s.lon))
        if d <= radius_km:
            res.append((s, d))
    res.sort(key=lambda x: x[1])
    return res

def get_user_by_phone_or_email(db: Session, identifier: str):
    return db.query(models.User).filter(
        (models.User.phone == identifier) | (models.User.email == identifier)
    ).first()