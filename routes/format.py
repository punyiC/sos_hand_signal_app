from datetime import datetime
import httpx
import base64
from bson.binary import Binary

# async def forward_geocode(location_name: str):
#    url = f"https://nominatim.openstreetmap.org/search?format=jsonv2&q={location_name}"
#    async with httpx.AsyncClient() as client:
#        try:
#            res = await client.get(url, timeout=10.0)
#            data = await res.json()
#            if data:
#                return float(data[0]["lat"]), float(data[0]["lon"])
#        except Exception as e:
#            print("❌ geocode error:", e)
#    return 0.0, 0.0

async def reverse_geocode(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lon}&accept-language=en"  
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url, timeout=10.0)
            data = await res.json()
            return data.get("display_name", f"{lat}, {lon}")
        except Exception as e:
            print("❌ geocode error:", e)
    return f"{lat}, {lon}"

async def format_doc_step1(doc):
    # timestamp
    timestamp_str = doc.get("timestamp")
    if not timestamp_str:
        try:
            timestamp = datetime.fromisoformat(f"{doc['date']}T{doc['time']}")
            timestamp_str = timestamp.isoformat()
        except:
            timestamp_str = datetime.utcnow().isoformat()

    # location 
    raw_location = doc.get("location")
    if isinstance(raw_location, list) and len(raw_location) == 2:
        lat, lon = raw_location
    else:
        lat, lon = 0.0, 0.0  
    location_str = await reverse_geocode(lat, lon)

    # image_data → คงไว้แบบ Binary
    image_data = doc.get("image_data") if isinstance(doc.get("image_data"), Binary) else None

    return {
        "name": doc.get("name", "unknown"),
        "timestamp": timestamp_str,
        "location": location_str,   
        "latitude": lat,
        "longitude": lon,
        "confidence": doc.get("confidence", 0.9),
        "image_data": image_data     
    }

