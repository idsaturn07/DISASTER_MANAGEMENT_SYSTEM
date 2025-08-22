import random, time, threading
import config

_otp_store = {}  # phone -> (otp, expire_timestamp)

def _clean_expired_otps():
    current_time = time.time()
    expired_phones = [phone for phone, (_, exp) in _otp_store.items() if current_time > exp]
    for phone in expired_phones:
        del _otp_store[phone]

def start_otp_cleanup():
    def cleanup_task():
        while True:
            time.sleep(300)  # 5 minutes
            _clean_expired_otps()
    
    thread = threading.Thread(target=cleanup_task, daemon=True)
    thread.start()

start_otp_cleanup()

def send_otp(phone: str, sender_func):
    otp = random.randint(100000, 999999)
    expire = time.time() + config.OTP_TTL
    _otp_store[phone] = (str(otp), expire)
    sender_func(phone, f"Your OTP for Disaster Management Portal is {otp}")
    return otp

def verify_otp(phone: str, otp: str) -> bool:
    entry = _otp_store.get(phone)
    if not entry:
        return False
    stored, exp = entry
    if time.time() > exp:
        del _otp_store[phone]
        return False
    if stored == otp:
        del _otp_store[phone]
        return True
    return False