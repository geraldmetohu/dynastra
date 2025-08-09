import os
import firebase_admin
from firebase_admin import credentials, auth

# Load service account path from .env
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not cred_path or not os.path.exists(cred_path):
    raise RuntimeError(f"Firebase credentials file not found at {cred_path}")

# Initialize Firebase Admin SDK only once
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

firebase_auth = auth  # Export to use in other files
