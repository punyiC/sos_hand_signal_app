from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from bson import ObjectId
from pydantic import BaseModel
from app.database import collection
from fastapi import Response 
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["sos-app"]
formatted_collection = db["formatted_ai_data"]

router = APIRouter()

# -- เก็บการเชื่อมต่อ WebSocket
active_connections = []

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print("✅ WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_text()
            print("📥 Received:", data)

            # ✅ broadcast ไปยัง client อื่น
            for conn in active_connections:
                if conn != websocket:
                    await conn.send_text(data)
    except WebSocketDisconnect:
        print("❌ WebSocket client disconnected")
        active_connections.remove(websocket)

# -------- SOS API --------

class SOSPayload(BaseModel):
    prediction: str
    confidence: float
    timestamp: str = None
    location: str = None
    image_url: str = None
    latitude: float = None
    longitude: float = None
    
    

@router.post("/api/sos")
async def receive_sos(payload: SOSPayload):
    data = payload.dict()

    if not data.get("timestamp"):
        data["timestamp"] = datetime.utcnow().isoformat()

    data["source"] = "user"    

    try:
        result = await collection.insert_one(data)
        return {"status": "received", "id": str(result.inserted_id)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    

@router.get("/api/history")
async def get_sos_all():
    sos_list = []
    async for doc in collection.find().sort("timestamp", -1):
        doc["_id"] = str(doc["_id"])

        for key in list(doc.keys()):
            if isinstance(doc[key], bytes):
                print(f"⚠️ Removed binary field: {key}")
                del doc[key]

        sos_list.append(doc)
    return sos_list

@router.delete("/api/history/{id}")
async def delete_history(id: str):
    try:
        result = await collection.delete_one({"_id": ObjectId(id)})
        if result.deleted_count:
            return {"status": "deleted"}
        return JSONResponse(status_code=404, content={"status": "not found"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/api/area-data")
async def get_area_data():
    result = []
    ai_collection = db["sos_alerts"]
    user_collection = db["sos"] 
    observer_collection = db["observer"]


    valid_sources = {
        "theta": "camera",
        "mail": "camera",
        "theta2": "camera",
        "user": "user",
        "observer": "observer"
    }

    async for doc in ai_collection.find().sort("timestamp", -1):
        try:
            for key in list(doc.keys()):
                if isinstance(doc[key], bytes):
                    del doc[key]

            source = doc.get("source") or doc.get("name") or "user"
            mapped_type = valid_sources.get(source, "unknown")

            lat = doc.get("latitude")
            lng = doc.get("longitude")

            # ✅ fallback จาก location array
            if not lat or not lng:
                loc = doc.get("location")
                if isinstance(loc, list) and len(loc) == 2:
                    lat, lng = loc[0], loc[1]

            print(f"🧪 source={source}, type={mapped_type}, lat={lat}, lng={lng}")

            if lat and lng and mapped_type != "unknown":
                result.append({
                    "_id": str(doc.get("_id")),
                    "name": source,
                    "type": mapped_type,
                    "latitude": lat,
                    "longitude": lng,
                    "location": doc.get("location", "-"),
                    "timestamp": doc.get("timestamp", "-")
                })
            else:
                print("❌ Skipped: ไม่ผ่านเงื่อนไข")

        except Exception as e:
            print("❌ Error in /api/area-data:", e)
    
    async for doc in user_collection.find().sort("timestamp", -1):
        try:
            for key in list(doc.keys()):
                if isinstance(doc[key], bytes):
                    del doc[key]

            source = doc.get("source") or doc.get("name") or "user"
            mapped_type = valid_sources.get(source, "unknown")

            lat = doc.get("latitude")
            lng = doc.get("longitude")
            if not lat or not lng:
                loc = doc.get("location")
                if isinstance(loc, list) and len(loc) == 2:
                    lat, lng = loc[0], loc[1]

            print(f"🧪 [user] source={source}, type={mapped_type}, lat={lat}, lng={lng}")

            if lat and lng and mapped_type != "unknown":
                result.append({
                    "_id": str(doc.get("_id")),
                    "name": source,
                    "type": mapped_type,
                    "latitude": lat,
                    "longitude": lng,
                    "location": doc.get("location", "-"),
                    "timestamp": doc.get("timestamp", "-")
                })

        except Exception as e:
            print("❌ Error in /api/area-data (user):", e)

    async for doc in observer_collection.find().sort("timestamp", -1):
        try:
            for key in list(doc.keys()):
                if isinstance(doc[key], bytes):
                    del doc[key]

            source = doc.get("source") or doc.get("name") or "observer"
            mapped_type = valid_sources.get(source, "unknown")

            lat = doc.get("latitude")
            lng = doc.get("longitude")
            if not lat or not lng:
                loc = doc.get("location")
                if isinstance(loc, list) and len(loc) == 2:
                    lat, lng = loc[0], loc[1]

            print(f"🧪 [observer] source={source}, type={mapped_type}, lat={lat}, lng={lng}")

            if lat and lng and mapped_type != "unknown":
                result.append({
                    "_id": str(doc.get("_id")),
                    "name": source,
                    "type": mapped_type,
                    "latitude": lat,
                    "longitude": lng,
                    "location": doc.get("location", "-"),
                    "timestamp": doc.get("timestamp", "-")
                })

        except Exception as e:
            print("❌ Error in /api/area-data (observer):", e)        

    print(f"📦 Total result count: {len(result)}")
    return result



@router.get("/image/{image_id}")
async def get_image(image_id: str):

    try:
        oid = ObjectId(image_id)
    except:
        oid = None

    for col in [collection, formatted_collection]:
        # ตรวจ _id และ raw_id
        if oid:
            doc = await col.find_one({"_id": oid})
            if doc and "image_data" in doc:
                return Response(content=doc["image_data"], media_type="image/jpeg")

        doc = await col.find_one({"raw_id": image_id})
        if doc and "image_data" in doc:
            return Response(content=doc["image_data"], media_type="image/jpeg")

    return Response(content=b"", media_type="image/jpeg", status_code=404)

