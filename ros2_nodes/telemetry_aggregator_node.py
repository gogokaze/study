import json
import logging
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String, Float32
    from sensor_msgs.msg import Imu, NavSatFix, JointState
    _ROS2_AVAILABLE = True
except ImportError:
    _ROS2_AVAILABLE = False
    logger.warning("rclpy not available — TelemetryAggregatorNode running in stub mode")

if _ROS2_AVAILABLE:
    class TelemetryAggregatorNode(Node):
        def __init__(self) -> None:
            super().__init__("telemetry_aggregator")
            self._state: dict[str, Any] = {}

            # Drone subscriptions
            self.create_subscription(String,  "/drone/telemetry", self._drone_telemetry_cb, 10)
            self.create_subscription(Float32, "/drone/battery",   self._drone_battery_cb,   10)
            self.create_subscription(NavSatFix, "/drone/gps",     self._drone_gps_cb,        10)
            self.create_subscription(Imu,      "/drone/imu",      self._drone_imu_cb,        10)

            # Go2 subscriptions
            self.create_subscription(Imu,       "/go2/imu",       self._go2_imu_cb,    10)
            self.create_subscription(JointState, "/go2/joint",    self._go2_joint_cb,  10)
            self.create_subscription(String,    "/go2/camera",    self._go2_camera_cb, 10)
            self.create_subscription(String,    "/go2/lidar",     self._go2_lidar_cb,  10)

            # Robot arm subscriptions
            self.create_subscription(JointState, "/robot_arm/joint_state", self._arm_joint_cb, 10)
            self.create_subscription(String,     "/robot_arm/task",        self._arm_task_cb,  10)

            # Unified publisher
            self._pub = self.create_publisher(String, "/yfl/telemetry", 10)
            self._timer = self.create_timer(0.1, self._publish_unified)
            self.get_logger().info("TelemetryAggregatorNode started")

        # ---- Drone callbacks ----
        def _drone_telemetry_cb(self, msg: "String") -> None:
            try:
                self._state.setdefault("drone", {}).update(json.loads(msg.data))
            except json.JSONDecodeError:
                pass

        def _drone_battery_cb(self, msg: "Float32") -> None:
            self._state.setdefault("drone", {})["battery"] = msg.data

        def _drone_gps_cb(self, msg: "NavSatFix") -> None:
            self._state.setdefault("drone", {})["gps"] = {
                "lat": msg.latitude,
                "lon": msg.longitude,
                "alt": msg.altitude,
            }

        def _drone_imu_cb(self, msg: "Imu") -> None:
            self._state.setdefault("drone", {})["imu"] = {
                "ax": msg.linear_acceleration.x,
                "ay": msg.linear_acceleration.y,
                "az": msg.linear_acceleration.z,
            }

        # ---- Go2 callbacks ----
        def _go2_imu_cb(self, msg: "Imu") -> None:
            self._state.setdefault("go2", {})["imu"] = {
                "ax": msg.linear_acceleration.x,
                "ay": msg.linear_acceleration.y,
                "az": msg.linear_acceleration.z,
            }

        def _go2_joint_cb(self, msg: "JointState") -> None:
            self._state.setdefault("go2", {})["joints"] = dict(
                zip(msg.name, msg.position)
            )

        def _go2_camera_cb(self, msg: "String") -> None:
            self._state.setdefault("go2", {})["camera"] = msg.data

        def _go2_lidar_cb(self, msg: "String") -> None:
            try:
                self._state.setdefault("go2", {})["lidar"] = json.loads(msg.data)
            except json.JSONDecodeError:
                pass

        # ---- Robot arm callbacks ----
        def _arm_joint_cb(self, msg: "JointState") -> None:
            self._state.setdefault("robot_arm", {})["joints"] = dict(
                zip(msg.name, msg.position)
            )

        def _arm_task_cb(self, msg: "String") -> None:
            self._state.setdefault("robot_arm", {})["task"] = msg.data

        # ---- Publish unified ----
        def _publish_unified(self) -> None:
            payload = {
                "timestamp": time.time(),
                "devices": self._state,
            }
            out = String()
            out.data = json.dumps(payload)
            self._pub.publish(out)


    def main() -> None:
        rclpy.init()
        node = TelemetryAggregatorNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            rclpy.shutdown()

else:
    class TelemetryAggregatorNode:  # type: ignore[no-redef]
        """Stub used when rclpy is not installed."""
        def __init__(self) -> None:
            logger.info("TelemetryAggregatorNode stub initialised (rclpy not available)")

    def main() -> None:
        logger.error("Cannot start TelemetryAggregatorNode: rclpy is not installed")
        sys.exit(1)


if __name__ == "__main__":
    main()
