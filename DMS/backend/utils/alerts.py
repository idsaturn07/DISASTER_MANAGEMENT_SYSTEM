from twilio.rest import Client
import config

def send_sms(phone: str, message: str):
    if config.TWILIO_SID and config.TWILIO_AUTH and config.TWILIO_PHONE:
        client = Client(config.TWILIO_SID, config.TWILIO_AUTH)
        client.messages.create(
            to=phone,
            from_=config.TWILIO_PHONE,
            body=message
        )
    else:
        print(f"[MOCK SMS] to {phone}: {message}")