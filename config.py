import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Read from environment variables
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

if not MONGO_URI or not DB_NAME:
    raise ValueError("Missing MONGO_URI or DB_NAME in environment variables")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
