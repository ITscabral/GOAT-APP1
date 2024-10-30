from twilio.rest import Client
import os
from dotenv import load_dotenv

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

def send_sms(to_number, message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        sms = client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=to_number)
        print(f"SMS sent successfully. SID: {sms.sid}")
    except Exception as e:
        print(f"Error sending SMS: {e}")
