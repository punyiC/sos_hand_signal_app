from fastapi import APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from routes.ws import broadcast_formatted_data
import httpx
from datetime import datetime
from bson.binary import Binary
from bson import ObjectId

router = APIRouter()


load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["sos-app"]
raw_collection = db["sos_alerts"]
formatted_collection = db["formatted_ai_data"]


async def transform_single_doc(doc):
    lat, lon = 0.0, 0.0
    if isinstance(doc.get("location"), list) and len(doc["location"]) == 2:
        lat, lon = doc["location"]

    # reverse geocode
    location_str = await reverse_geocode(lat, lon)
    timestamp = doc.get("timestamp") or datetime.utcnow().isoformat()
    image_data = doc.get("image_data")
    final_image = image_data if isinstance(image_data, (Binary, bytes)) else None

    formatted = {
        "name": doc.get("name", "unknown"),
        "timestamp": timestamp,
        "location": location_str,
        "latitude": lat,
        "longitude": lon,
        "confidence": doc.get("confidence", 0.9),
        "image_data": final_image,
        "raw_id": str(doc["_id"]),
    }

    await formatted_collection.insert_one(formatted)
    await broadcast_formatted_data(formatted)


async def reverse_geocode(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}&accept-language=en"
        async with httpx.AsyncClient() as client:
            res = await client.get(url, timeout=5.0)
            return res.json().get("display_name", f"{lat},{lon}")
    except:
        return f"{lat},{lon}"


@router.post("/api/ai-sos")
async def receive_from_ai(doc: dict):
    inserted = await raw_collection.insert_one(doc)
    doc["_id"] = inserted.inserted_id  
    await transform_single_doc(doc)
    return {"status": "ok", "id": str(inserted.inserted_id)}
