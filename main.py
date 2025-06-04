from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routes import sos, ai, history, ws
from routes import ai_submit
from routes.ws import ws_router
from watch_insert import watch_inserts
import asyncio


app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# รวม router
app.include_router(sos.router) 
app.include_router(ai.router, prefix="/api")
app.include_router(history.router)
app.include_router(ai_submit.router)
app.include_router(ws_router)



# หน้าแรก
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# หน้า history
@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(watch_inserts())