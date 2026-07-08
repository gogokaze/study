import asyncio
import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from telemetry_hub.hub import TelemetryHub
from telemetry_hub.database import TelemetryDatabase
from telemetry_hub.schema import TelemetryPacket, DeviceType, DeviceStatus
from devices.gt3_drone import GT3Drone
from devices.z908_fpv import Z908FPV
from devices.go2_dog import Go2Dog
from devices.robot_arm import RobotArm
from devices.cnc_machine import CNCMachine
from devices.submarine import LegoSubmarine
from web_dashboard.ws_handler import WebSocketManager
from web_dashboard.pcb_routes import router as pcb_router

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "yfl_telemetry.db")
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="YFL Robotics Dashboard", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(pcb_router)

hub = TelemetryHub(db_path=DB_PATH)
ws_manager = WebSocketManager()

_DEVICES = [
    GT3Drone("GT3-001"),
    Z908FPV("Z908-001"),
    Go2Dog("Go2-001"),
    RobotArm("ARM-001"),
    CNCMachine("CNC-001"),
    LegoSubmarine("SUB-001"),
]

for _dev in _DEVICES:
    hub.register_device(_dev.device_id, _dev.device_type)


async def _broadcast_cb(packet: TelemetryPacket) -> None:
    await ws_manager.broadcast(packet.to_json())


for _dt in DeviceType:
    hub.subscribe(_dt.value, _broadcast_cb)


@app.on_event("startup")
async def _startup() -> None:
    await hub.start()
    asyncio.create_task(_simulate_loop())
    logger.info("YFL Dashboard started")


@app.on_event("shutdown")
async def _shutdown() -> None:
    await hub.stop()


async def _simulate_loop() -> None:
    while True:
        for dev in _DEVICES:
            packet = dev.simulate()
            await hub.publish(packet)
        await asyncio.sleep(1.0)


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = STATIC_DIR / "dashboard.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/pcb", response_class=HTMLResponse)
async def pcb_editor() -> HTMLResponse:
    html_path = STATIC_DIR / "pcb_editor.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "connections": ws_manager.connection_count})


@app.get("/api/devices")
async def list_devices() -> JSONResponse:
    return JSONResponse(hub.get_status_all())


@app.get("/api/telemetry/{device_id}")
async def get_telemetry(device_id: str) -> JSONResponse:
    db = TelemetryDatabase(DB_PATH)
    rows = db.get_history(device_id, limit=100)
    db.close()
    if not rows:
        device_info = hub.get_status_all().get(device_id)
        if device_info is None:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    return JSONResponse(rows)


@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
