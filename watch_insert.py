import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from routes.ai_submit import transform_single_doc
from dotenv import load_dotenv
import os

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(MONGO_URI)
db = client["sos-app"]
collection = db["sos_alerts"]

async def watch_inserts():
    async with collection.watch([{"$match": {"operationType": "insert"}}]) as stream:
        async for change in stream:
            new_doc = change["fullDocument"]
            print(" New document inserted:", new_doc)
            await transform_single_doc(new_doc)