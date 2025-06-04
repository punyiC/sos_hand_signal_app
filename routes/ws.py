import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from bson import ObjectId
from bson.binary import Binary 

ws_router = APIRouter()
clients = set()  


@ws_router.websocket("/ws/formatted")
async def websocket_formatted_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)  
    print("✅ WebSocket client connected:", websocket.client)
    try:
        while True:
            await websocket.receive_text() 
    except WebSocketDisconnect:
        print("❌ WebSocket client disconnected:", websocket.client)
        clients.remove(websocket)  


async def broadcast_formatted_data(data: dict):
    # แปลง _id เป็น string และดึง generation_time
    if "_id" in data:
        if isinstance(data["_id"], ObjectId):
            object_id = data["_id"]
        else:
            object_id = ObjectId(data["_id"])
        data["_id"] = str(object_id)
        data["timestamp"] = object_id.generation_time.isoformat()

    # แปลง image_data เป็น base64 string
    image_data = data.get("image_data")
    if isinstance(image_data, (Binary, bytes, bytearray)):
        data["image_data"] = base64.b64encode(bytes(image_data)).decode("utf-8")
    else:
        data["image_data"] = None

    # DEBUG LOG
    print("✅ WS SENT:", data["name"], data["timestamp"], data["_id"])

    message = json.dumps(data)
    for ws in clients:
        await ws.send_text(message)