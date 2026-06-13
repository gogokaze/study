# YFL Mission Planner MK.5

## MK.5 Architecture Upgrade

MK.5 introduces a multi-agent, shared-world-model architecture on top of the original telemetry pipeline.

### New Components

| Module | Purpose |
|---|---|
| `world_model/` | `SharedWorldModel` — asyncio-safe object registry with upsert, query, assign, update_state |
| `world_model/events.py` | `EventBus` with typed `RoboticsEvent`, fan-out publish/subscribe, 500-event history |
| `agents/` | `BaseAgent` + 5 specializations: Scout, Transport, Manipulator, Inspection, Submarine |
| `behavior_tree/nodes.py` | `SequenceNode`, `SelectorNode`, `ConditionNode`, `ActionNode`, `InverterNode` |
| `behavior_tree/global_bt.py` | `GlobalBehaviorTree` — warehouse QR-pickup mission BT |
| `behavior_tree/local_bt.py` | `LocalBehaviorTree` — per-agent perceive→decide→act loop |
| `web_dashboard/mk5_routes.py` | FastAPI router: `GET /api/mk5/world`, `/events`, `/agents` |
| `mk5_main.py` | Entry point: wires all agents, devices, and BTs; runs 10 ticks |

### MK.5 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  GlobalBehaviorTree (MK.5)                  │
│  Sequence: ScoutSearch → QRHandling → PickupPath            │
└────────────────────────┬────────────────────────────────────┘
                         │ tick()
     ┌───────────────────┼───────────────────┐
     ▼                   ▼                   ▼
 ScoutAgent        TransportAgent     ManipulatorAgent
 (LocalBT)         (LocalBT)          (LocalBT)
     │                   │                   │
     └───────────────────┴───────────────────┘
                         │
              SharedWorldModel (asyncio.Lock)
              WorldObject: QR_CODE / ROBOT / ITEM ...
                         │
                    EventBus
              RoboticsEvent fan-out (500-event deque)
```

### Running MK.5

```bash
python mk5_main.py
```

### Tests

```bash
python -m pytest tests/test_mk5.py -v
```

---

# YFL Robotics Unified Architecture

A unified telemetry, monitoring, and mission-planning platform for heterogeneous robotic devices developed by YFL Robotics. This architecture provides a single control plane for drones, quadrupeds, robotic arms, CNC machines, and aquatic vehicles.

---

## Supported Devices

| Device | Type | Protocol | Notes |
|---|---|---|---|
| GT3 Drone | Aerial | MQTT / UDP | 4-motor, GPS-guided, FPV capable |
| Z908 FPV | Aerial FPV | MQTT | Racing-style FPV drone with video stream |
| Unitree Go2 | Quadruped | ROS2 / MQTT | 12-DOF legged robot with LiDAR |
| ROS2 Robot Arm | Manipulator | ROS2 | 6-DOF arm with force-torque sensing |
| CNC Machine | Industrial | MQTT | 3-axis CNC with spindle monitoring |
| Lego Submarine | Aquatic | MQTT | Depth-controlled Lego-based submersible |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                   Web Dashboard (FastAPI)                 │
│          GET /api/devices  ·  WS /ws/telemetry           │
└───────────────────────┬──────────────────────────────────┘
                        │ HTTP / WebSocket
┌───────────────────────▼──────────────────────────────────┐
│                   Telemetry Hub (Python)                  │
│          asyncio queues · SQLite persistence              │
└──────┬─────────────────────────────────────┬─────────────┘
       │ MQTT (paho)                          │ ROS2 (rclpy)
┌──────▼──────────┐                 ┌────────▼─────────────┐
│  Mosquitto MQTT │                 │  ROS2 Nodes          │
│  Broker         │                 │  TelemetryAggregator │
└──────┬──────────┘                 │  MissionPlanner      │
       │                            └──────────────────────┘
┌──────▼──────────────────────────────────────────────────┐
│  Devices                                                 │
│  GT3Drone · Z908FPV · Go2Dog · RobotArm · CNC · Sub     │
└─────────────────────────────────────────────────────────┘
```

All telemetry is stored in SQLite (local) and optionally forwarded to InfluxDB for long-term time-series analysis.

---

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- (Optional) ROS2 Humble for ROS2 node features

---

## Setup Instructions

### 1. Clone & enter the project

```bash
git clone https://github.com/yfl-robotics/unified-arch.git
cd unified-arch
```

### 2. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Start infrastructure services

```bash
docker compose up -d
```

This starts:
- **Mosquitto** MQTT broker on port 1883
- **InfluxDB** on port 8086
- **Telemetry Hub** Python service
- **Web Dashboard** FastAPI on port 8080

### 4. Run the web dashboard standalone

```bash
uvicorn web_dashboard.app:app --host 0.0.0.0 --port 8080 --reload
```

Then open http://localhost:8080 in your browser.

### 5. Run device simulators

```python
import asyncio
from devices.gt3_drone import GT3Drone
from telemetry_hub.hub import TelemetryHub

async def main():
    hub = TelemetryHub()
    drone = GT3Drone("drone-001")
    hub.register_device(drone)
    for _ in range(20):
        packet = drone.simulate()
        await hub.publish(packet)
        await asyncio.sleep(0.5)

asyncio.run(main())
```

### 6. Run ROS2 nodes (requires ROS2 Humble)

```bash
# In separate terminals:
ros2 run yfl_robotics telemetry_aggregator
ros2 run yfl_robotics mission_planner
```

---

## Project Structure

```
.
├── telemetry_hub/          # Core telemetry processing
│   ├── schema.py           # TelemetryPacket dataclasses
│   ├── database.py         # SQLite persistence
│   ├── hub.py              # Async telemetry hub
│   └── mqtt_bridge.py      # MQTT integration
├── devices/                # Device abstraction layer
│   ├── base_device.py      # Abstract base class
│   ├── gt3_drone.py
│   ├── z908_fpv.py
│   ├── go2_dog.py
│   ├── robot_arm.py
│   ├── cnc_machine.py
│   └── submarine.py
├── ros2_nodes/             # ROS2 integration
│   ├── telemetry_aggregator_node.py
│   └── mission_planner_node.py
├── web_dashboard/          # FastAPI web interface
│   ├── app.py
│   ├── ws_handler.py
│   └── static/dashboard.html
├── mission_planner/        # High-level mission execution
│   ├── planner.py
│   └── missions/
│       ├── drone_patrol.py
│       ├── go2_warehouse.py
│       └── arm_pick_place.py
├── tests/
│   ├── test_schema.py
│   ├── test_hub.py
│   └── test_devices.py
└── docker-compose.yml
```

---

## MQTT Topic Schema

| Topic | Direction | Payload |
|---|---|---|
| `yfl/GT3/telemetry` | Device → Hub | JSON TelemetryPacket |
| `yfl/Z908/telemetry` | Device → Hub | JSON TelemetryPacket |
| `yfl/Go2/telemetry` | Device → Hub | JSON TelemetryPacket |
| `yfl/RobotArm/telemetry` | Device → Hub | JSON TelemetryPacket |
| `yfl/CNC/telemetry` | Device → Hub | JSON TelemetryPacket |
| `yfl/Submarine/telemetry` | Device → Hub | JSON TelemetryPacket |

---

## Configuration

Environment variables (set in `.env` or docker-compose):

| Variable | Default | Description |
|---|---|---|
| `MQTT_HOST` | `localhost` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `INFLUX_URL` | `http://localhost:8086` | InfluxDB URL |
| `INFLUX_TOKEN` | `` | InfluxDB auth token |
| `DB_PATH` | `yfl_telemetry.db` | SQLite database path |

---

## License

MIT License — YFL Robotics 2025
