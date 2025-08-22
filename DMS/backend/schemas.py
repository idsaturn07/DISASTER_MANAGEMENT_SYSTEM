from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreate(BaseModel):
    phone: str = Field(..., pattern=r'^[6-9]\d{9}$')
    email: EmailStr
    address: str
    city: str
    state: str
    pincode: str = Field(..., min_length=3, max_length=12)
    password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: int
    full_name: str
    phone: str
    email: str
    verified: bool

    class Config:
        from_attributes = True


class LoginSchema(BaseModel):
    phone_or_email: str
    password: str


class DisasterCreate(BaseModel):
    type: str
    description: Optional[str] = None
    address: str
    city: str
    state: str
    pincode: str
    reporter_id: Optional[int] = None


class AssignTeamOut(BaseModel):
    team_id: int
    team_name: str
    contact: str


class AlertPayload(BaseModel):
    message: str
    city: Optional[str] = None
    radius_km: Optional[float] = 10.0


class OTPVerify(BaseModel):
    phone: str
    otp: str