from fastapi import APIRouter
from fastapi import APIRouter
from app.database import sos_collection, formatted_ai_collection
import datetime
import httpx
import base64

router = APIRouter()


async def reverse_geocode(lat, lng):
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}"
    headers = {"User-Agent": "sos-app"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("display_name", "Unknown location")
    except Exception as e:
        print(f"❌ Reverse geocode error: {e}")
    return "Unknown location"

@router.get("/api/history")
async def get_sos_all():
    sos_list = []

    async for doc in collection.find().sort("timestamp", -1):
        doc["_id"] = str(doc["_id"])

        if "prediction" not in doc:
            # ข้อมูลจาก AI
            doc["prediction"] = "sos"
            doc["confidence"] = 0.9
            doc["name"] = doc.get("name", "ai")

            # แปลง date + time → timestamp
            if "date" in doc and "time" in doc:
                try:
                    dt = f"{doc['date']}T{doc['time']}"
                    doc["timestamp"] = datetime.datetime.fromisoformat(dt).isoformat()
                except:
                    doc["timestamp"] = None

            # แปลงพิกัด + ทำ reverse geocode
            if isinstance(doc.get("location"), list) and len(doc["location"]) == 2:
                lat = doc["location"][0]
                lng = doc["location"][1]
                doc["latitude"] = lat
                doc["longitude"] = lng
                doc["location"] = await reverse_geocode(lat, lng)

            # ลบ field ไม่ใช้
            doc.pop("date", None)
            doc.pop("time", None)
        else:
            # จาก user
            doc["name"] = doc.get("name", "user")
            doc["confidence"] = doc.get("confidence", 1.0)

        # ลบ image_url
        doc.pop("image_url", None)

        sos_list.append(doc)

    return sos_list

@router.get("/api/all_sos")
async def get_all_combined():
    all_data = []

    # ดึงข้อมูลจาก user (collection: sos)
    async for doc in sos_collection.find({}):
        all_data.append({
            "_id": str(doc["_id"]),
            "name": "user",
            "prediction": doc.get("prediction", "sos"),
            "confidence": doc.get("confidence"),
            "timestamp": doc.get("timestamp"),
            "location": doc.get("location"),
            "latitude": doc.get("latitude"),
            "longitude": doc.get("longitude"),
            "image_data": None,
            "image_url": doc.get("image_url"),
        })

    # ดึงข้อมูลจาก AI (collection: formatted_ai_data)
    async for doc in formatted_ai_collection.find({}):
        # 🔧 แปลง binary เป็น base64 string อย่างปลอดภัย
        image_data = doc.get("image_data")
        if image_data and isinstance(image_data, bytes):
            image_data = base64.b64encode(image_data).decode("ascii")
        else:
            image_data = None

        all_data.append({
            "_id": str(doc["_id"]),
            "name": doc.get("name", "ai"),
            "prediction": "sos",
            "confidence": doc.get("confidence"),
            "timestamp": doc.get("timestamp"),
            "location": doc.get("location"),
            "latitude": doc.get("latitude"),
            "longitude": doc.get("longitude"),
            "image_data": image_data,
            "image_url": None,
        })

    return {"count": len(all_data), "data": all_data}