from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = AsyncIOMotorClient(MONGO_URI)
db = client["sos-app"]  
collection = db["sos"]

sos_collection = db["sos"]
formatted_ai_collection = db["formatted_ai_data"]

