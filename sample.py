# Create a file called test_env.py in the same directory as app.py
import os
from dotenv import load_dotenv

print(f"Current directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")

if os.path.exists('.env'):
    with open('.env', 'r') as f:
        content = f.read()
    print(f".env file content:\n{content}")

load_dotenv()

print(f"\nAfter loading .env:")
print(f"TWILIO_ACCOUNT_SID: {os.environ.get('TWILIO_ACCOUNT_SID', 'NOT FOUND')}")
print(f"TWILIO_AUTH_TOKEN: {os.environ.get('TWILIO_AUTH_TOKEN', 'NOT FOUND')}")
print(f"TWILIO_PHONE_NUMBER: {os.environ.get('TWILIO_PHONE_NUMBER', 'NOT FOUND')}")
