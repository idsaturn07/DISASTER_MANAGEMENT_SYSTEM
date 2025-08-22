from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    address = Column(String(255))
    city = Column(String(50))
    state = Column(String(50))
    pincode = Column(String(10))
    password_hash = Column(String(255))
    verified = Column(Boolean, default=False)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

class RescueTeam(Base):
    __tablename__ = "rescue_teams"
    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(100))
    city = Column(String(50))
    contact = Column(String(20))
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    available = Column(Boolean, default=True)

class SafeLocation(Base):
    __tablename__ = "safe_locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150))
    address = Column(String(255))
    lat = Column(Float)
    lon = Column(Float)
    capacity = Column(Integer, default=0)

class DisasterReport(Base):
    __tablename__ = "disaster_reports"
    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    type = Column(String(100))
    description = Column(Text)
    address = Column(String(255))
    city = Column(String(50))
    state = Column(String(50))
    pincode = Column(String(10))
    lat = Column(Float)
    lon = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_team_id = Column(Integer, ForeignKey("rescue_teams.id"), nullable=True)

    reporter = relationship("User", foreign_keys=[reporter_id])
    assigned_team = relationship("RescueTeam", foreign_keys=[assigned_team_id])