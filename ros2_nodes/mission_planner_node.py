import json
import logging
import sys
import time
from enum import Enum

logger = logging.getLogger(__name__)

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    _ROS2_AVAILABLE = True
except ImportError:
    _ROS2_AVAILABLE = False
    logger.warning("rclpy not available — MissionPlannerNode running in stub mode")


class MissionState(Enum):
    STANDBY = "STANDBY"
    EXECUTING = "EXECUTING"
    COMPLETE = "COMPLETE"


if _ROS2_AVAILABLE:
    class MissionPlannerNode(Node):
        def __init__(self) -> None:
            super().__init__("mission_planner")
            self._state = MissionState.STANDBY
            self._active_mission: dict | None = None
            self._mission_start: float = 0.0
            self._mission_timeout: float = 60.0

            self._sub = self.create_subscription(
                String, "/yfl/telemetry", self._telemetry_cb, 10
            )
            self._pub = self.create_publisher(String, "/yfl/mission/command", 10)
            self._timer = self.create_timer(1.0, self._state_machine_tick)
            self.get_logger().info("MissionPlannerNode started — state: STANDBY")

        def _telemetry_cb(self, msg: "String") -> None:
            try:
                data = json.loads(msg.data)
                self._on_telemetry(data)
            except json.JSONDecodeError:
                pass

        def _on_telemetry(self, data: dict) -> None:
            if self._state == MissionState.STANDBY:
                devices = data.get("devices", {})
                drone = devices.get("drone", {})
                if drone.get("battery", 100) > 20:
                    self._start_mission("drone_patrol", device="drone")

        def _start_mission(self, mission_name: str, device: str) -> None:
            self._active_mission = {"name": mission_name, "device": device}
            self._mission_start = time.time()
            self._state = MissionState.EXECUTING
            self._publish_command("START", mission_name, device)
            self.get_logger().info(
                "Mission %s started for %s", mission_name, device
            )

        def _state_machine_tick(self) -> None:
            if self._state == MissionState.EXECUTING:
                elapsed = time.time() - self._mission_start
                if elapsed >= self._mission_timeout:
                    self._complete_mission()
            elif self._state == MissionState.COMPLETE:
                self._state = MissionState.STANDBY
                self._active_mission = None
                self.get_logger().info("Mission complete — returning to STANDBY")

        def _complete_mission(self) -> None:
            if self._active_mission:
                self._publish_command(
                    "COMPLETE",
                    self._active_mission["name"],
                    self._active_mission["device"],
                )
            self._state = MissionState.COMPLETE
            self.get_logger().info("Mission execution complete")

        def _publish_command(self, action: str, mission: str, device: str) -> None:
            cmd = String()
            cmd.data = json.dumps(
                {
                    "action": action,
                    "mission": mission,
                    "device": device,
                    "timestamp": time.time(),
                }
            )
            self._pub.publish(cmd)


    def main() -> None:
        rclpy.init()
        node = MissionPlannerNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            rclpy.shutdown()

else:
    class MissionPlannerNode:  # type: ignore[no-redef]
        """Stub used when rclpy is not installed."""
        def __init__(self) -> None:
            logger.info("MissionPlannerNode stub initialised (rclpy not available)")

    def main() -> None:
        logger.error("Cannot start MissionPlannerNode: rclpy is not installed")
        sys.exit(1)


if __name__ == "__main__":
    main()
