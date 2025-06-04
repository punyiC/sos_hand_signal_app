from datetime import datetime, timezone 
from bson.binary import Binary
from fastapi import APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from routes.ws import broadcast_formatted_data
from dateutil.parser import parse as parse_datetime
from bson import ObjectId
import httpx
import os
import base64
import pytz

router = APIRouter()


load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["sos-app"]  
raw_collection = db["sos_alerts"]
formatted_collection = db["formatted_ai_data"]

geocode_cache = {}

def coords_key(lat: float, lng: float) -> str:
    return f"{round(lat, 5)},{round(lng, 5)}"

async def reverse_geocode(lat, lng):
    lat = round(lat, 6)
    lng = round(lng, 6)

    key = coords_key(lat, lng)

    if key in geocode_cache:
        print(f"ใช้ค่าจาก cache สำหรับ {key}")
        return geocode_cache[key]

    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}&accept-language=en"
    headers = {"User-Agent": "sos-app"}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                location_name = data.get("display_name", "Unknown location")
                geocode_cache[key] = location_name
                return location_name
    except Exception as e:
        print(f" Reverse geocode error: {e}")

    return "Unknown location"


async def format_doc_step1(doc):
    # timestamp
    timestamp_str = doc.get("timestamp")
    if timestamp_str:
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            jst = pytz.timezone("Asia/Tokyo")
            dt_local = dt.astimezone(jst)
            timestamp_str = dt_local.strftime("%Y-%m-%d %H:%M:%S")

        except Exception as e:
            print("⚠️ timestamp format error:", e)
            timestamp_str = datetime.utcnow().isoformat() + "Z"
    else:
        print("❌ Missing timestamp in document")
        timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
    # lat/lon + location name
    raw_location = doc.get("location")
    if isinstance(raw_location, list) and len(raw_location) == 2:
        lat, lon = raw_location
    else:
        lat, lon = 0.0, 0.0
    location_str = await reverse_geocode(lat, lon)

    # image_data
    image_data = doc.get("image_data")
    
    if isinstance(image_data, (Binary, bytes)):
        final_image_data = image_data
    else:
        final_image_data = None

    return {
        "name": doc.get("name", "unknown"),
        "timestamp": timestamp_str,
        "location": location_str,
        "latitude": lat,
        "longitude": lon,
        "confidence": doc.get("confidence", 0.9),
        "image_data": final_image_data
    }

# แปลงข้อมูลจาก sos_alerts → formatted_ai_data
@router.post("/transform_ai")
async def transform_and_store_ai_data():
    count = 0
    found = False

    async for raw in raw_collection.find():
        found = True

        if await formatted_collection.find_one({"raw_id": str(raw["_id"])}):
            print("⏩ SKIP:", raw["_id"])
            continue

        print("📥 RAW FOUND:", raw)

        try:
            formatted = await format_doc_step1(raw)
            formatted["raw_id"] = str(raw["_id"])
            await formatted_collection.insert_one(formatted)
            await broadcast_formatted_data(formatted)
            
            print("✅ INSERTED:", formatted)
            count += 1
        except Exception as e:
            print("❌ FORMAT ERROR:", e)

    if not found:
        print("❌ NO DOCUMENTS FOUND in sos_alerts")

    return {"status": "ok", "inserted": count}

# ดึงข้อมูล formatted สำหรับหน้าเว็บ
@router.get("/formatted_ai")
async def get_formatted_data():
    results = []
    async for doc in formatted_collection.find().sort("timestamp", -1):
        doc["_id"] = str(doc["_id"])

        image_data = doc.get("image_data")
        if isinstance(image_data, (Binary, bytes)):
            doc["image_data"] = base64.b64encode(image_data).decode("utf-8")
        else:
            doc["image_data"] = None

        results.append(doc)
    return results

@router.get("/api/all_sos")
async def get_combined_sos():
    combined = []

    # user sos
    async for doc in db["sos_alerts"].find({}):
        doc["_id"] = str(doc["_id"])
        doc["name"] = doc.get("name", "user")
        if "timestamp" not in doc:
            doc["timestamp"] = ObjectId(doc["_id"]).generation_time.isoformat()
        combined.append(doc)

    # AI sos
    async for doc in db["formatted_ai_data"].find({}):
        doc["_id"] = str(doc["_id"])
        if "timestamp" not in doc:
            doc["timestamp"] = ObjectId(doc["_id"]).generation_time.isoformat()
        combined.append(doc)

    combined.sort(key=lambda d: d["timestamp"], reverse=True)

    return {"data": combined}

