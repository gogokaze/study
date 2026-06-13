"""SQLite persistence layer for YFL telemetry data."""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional

from telemetry_hub.schema import TelemetryPacket

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS devices (
    device_id   TEXT PRIMARY KEY,
    device_type TEXT NOT NULL,
    first_seen  REAL NOT NULL,
    last_seen   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT    NOT NULL,
    device_type TEXT    NOT NULL,
    timestamp   REAL    NOT NULL,
    battery     REAL,
    status      TEXT,
    imu_roll    REAL,
    imu_pitch   REAL,
    imu_yaw     REAL,
    imu_ax      REAL,
    imu_ay      REAL,
    imu_az      REAL,
    gps_lat     REAL,
    gps_lon     REAL,
    gps_alt     REAL,
    gps_fix     INTEGER,
    extra_json  TEXT,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_ts
    ON telemetry_log (device_id, timestamp DESC);
"""


class TelemetryDatabase:
    """Thread-safe SQLite wrapper for telemetry storage."""

    def __init__(self, db_path: str = "yfl_telemetry.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        self._conn = sqlite3.connect(
            str(self._db_path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()
        logger.info("Database opened at %s", self._db_path)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def insert_packet(self, packet: TelemetryPacket) -> None:
        """Insert a telemetry packet and upsert the device record."""
        assert self._conn is not None

        imu = packet.imu
        gps = packet.gps

        with self._conn:
            # Upsert device row
            self._conn.execute(
                """
                INSERT INTO devices (device_id, device_type, first_seen, last_seen)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    last_seen = excluded.last_seen
                """,
                (packet.device, packet.device_type, packet.timestamp, packet.timestamp),
            )

            # Insert telemetry log row
            self._conn.execute(
                """
                INSERT INTO telemetry_log (
                    device_id, device_type, timestamp, battery, status,
                    imu_roll, imu_pitch, imu_yaw, imu_ax, imu_ay, imu_az,
                    gps_lat, gps_lon, gps_alt, gps_fix,
                    extra_json
                ) VALUES (?,?,?,?,?, ?,?,?,?,?,?, ?,?,?,?, ?)
                """,
                (
                    packet.device,
                    packet.device_type,
                    packet.timestamp,
                    packet.battery,
                    packet.status,
                    imu.roll if imu else None,
                    imu.pitch if imu else None,
                    imu.yaw if imu else None,
                    imu.ax if imu else None,
                    imu.ay if imu else None,
                    imu.az if imu else None,
                    gps.lat if gps else None,
                    gps.lon if gps else None,
                    gps.alt if gps else None,
                    int(gps.fix) if gps else None,
                    json.dumps(packet.extra) if packet.extra else "{}",
                ),
            )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_latest(self, device_id: str) -> Optional[dict]:
        """Return the most recent telemetry row for *device_id* as a dict."""
        assert self._conn is not None
        row = self._conn.execute(
            """
            SELECT * FROM telemetry_log
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (device_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_history(self, device_id: str, limit: int = 100) -> list[dict]:
        """Return the last *limit* telemetry rows for *device_id* newest-first."""
        assert self._conn is not None
        rows = self._conn.execute(
            """
            SELECT * FROM telemetry_log
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (device_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_devices(self) -> list[dict]:
        """Return all known devices."""
        assert self._conn is not None
        rows = self._conn.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
        return [dict(r) for r in rows]

    def get_device(self, device_id: str) -> Optional[dict]:
        """Return the devices row for *device_id* or None."""
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        return dict(row) if row else None
