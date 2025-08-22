from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
import config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_admin_token(admin_id: int, admin_name: str):
    payload = {
        "sub": admin_id,
        "name": admin_name,
        "type": "admin",
        "exp": datetime.utcnow() + timedelta(minutes=config.JWT_EXP_MINUTES)
    }
    token = jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return token

def decode_token(token: str):
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload
    except Exception:
        return None