from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from the .env file
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

def send_sms(to_number, message):
    """Send an SMS via Twilio."""
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try:
        client.messages.create(body=message, from_=TWILIO_PHONE_NUMBER, to=to_number)
        print(f"SMS sent successfully to {to_number}")
    except Exception as e:
        print(f"Failed to send SMS: {e}")
