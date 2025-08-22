from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from database import engine, get_db, Base
import models, schemas, crud
from sqlalchemy.orm import Session
from utils.otp import send_otp, verify_otp
from utils.alerts import send_sms
from typing import Optional
import auth.utils_auth as auth_utils
import config

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Disaster Management API (FastAPI)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = auth_utils.hash_password("adminpassword")

def admin_required(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        token = authorization.split("Bearer ")[-1]
        payload = auth_utils.decode_token(token)
        if not payload or payload.get("type") != "admin":
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

@app.post("/users/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        u = crud.create_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    send_otp(u.phone, send_sms)
    return u

@app.post("/users/verify-otp")
def verify_user_otp(otp_data: schemas.OTPVerify, db: Session = Depends(get_db)):
    ok = verify_otp(otp_data.phone, otp_data.otp)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    user = db.query(models.User).filter(models.User.phone==otp_data.phone).first()
    if user:
        user.verified = True
        db.commit()
        return {"msg": "User verified"}
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/users/login")
def user_login(payload: schemas.LoginSchema, db: Session = Depends(get_db)):
    user = crud.get_user_by_phone_or_email(db, payload.phone_or_email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not auth_utils.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not user.verified:
        raise HTTPException(status_code=403, detail="User not verified")
    return {"msg": "Login success", "user_id": user.id, "name": user.full_name}

@app.post("/disaster/report")
def report_disaster(report: schemas.DisasterCreate, db: Session = Depends(get_db)):
    try:
        dr = crud.create_disaster(db, report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    count = crud.send_alerts_for_disaster(db, dr, radius_km=10.0)
    return {"msg": "Disaster reported", "disaster_id": dr.id, "alerts_sent": count}

@app.get("/disaster/{disaster_id}/nearby_safe")
def nearby_safe(disaster_id: int, radius_km: float = 10.0, db: Session = Depends(get_db)):
    dr = db.query(models.DisasterReport).filter(models.DisasterReport.id == disaster_id).first()
    if not dr:
        raise HTTPException(status_code=404, detail="Disaster not found")
    res = crud.get_nearby_safe_locations(db, dr.lat, dr.lon, radius_km)
    out = [{"id": s.id, "name": s.name, "address": s.address, "distance_km": d} for s, d in res]
    return {"safe_locations": out}

@app.post("/admin/login")
def admin_login(username: str, password: str):
    if username != ADMIN_USERNAME or not auth_utils.verify_password(password, ADMIN_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth_utils.create_admin_token(admin_id=1, admin_name=username)
    return {"access_token": token}

@app.post("/admin/assign_team/{disaster_id}")
def admin_assign_team(disaster_id: int, payload=Depends(admin_required), db: Session = Depends(get_db)):
    team = crud.assign_team_to_disaster(db, disaster_id)
    if not team:
        raise HTTPException(status_code=404, detail="No available team to assign")
    return {"msg": "Team assigned", "team_id": team.id, "team_name": team.team_name}

@app.post("/admin/alert")
def admin_alert(alert: schemas.AlertPayload, payload=Depends(admin_required), db: Session = Depends(get_db)):
    if alert.city:
        users = db.query(models.User).filter(models.User.city==alert.city).all()
        c = 0
        for u in users:
            send_sms(u.phone, alert.message)
            c += 1
        return {"msg": f"Alert sent to {c} users in {alert.city}"}
    else:
        raise HTTPException(status_code=400, detail="Please provide city to send alerts")

@app.get("/")
def root():
    return {"message": "Disaster Management System API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)