import pytest
from telemetry_hub.schema import TelemetryPacket, DeviceStatus
from devices.gt3_drone import GT3Drone
from devices.z908_fpv import Z908FPV
from devices.go2_dog import Go2Dog
from devices.robot_arm import RobotArm
from devices.cnc_machine import CNCMachine
from devices.submarine import LegoSubmarine


def _assert_valid_packet(pkt: TelemetryPacket, expected_type: str) -> None:
    assert isinstance(pkt, TelemetryPacket)
    assert pkt.device_type == expected_type
    assert isinstance(pkt.device, str) and len(pkt.device) > 0
    assert isinstance(pkt.timestamp, float) and pkt.timestamp > 0
    assert pkt.status in {s.value for s in DeviceStatus}
    assert isinstance(pkt.extra, dict)


class TestGT3DroneSimulate:
    def test_returns_packet(self) -> None:
        drone = GT3Drone("GT3-test")
        pkt = drone.simulate()
        _assert_valid_packet(pkt, "GT3")

    def test_has_imu(self) -> None:
        pkt = GT3Drone().simulate()
        assert pkt.imu is not None

    def test_has_gps(self) -> None:
        pkt = GT3Drone().simulate()
        assert pkt.gps is not None
        assert pkt.gps.fix is True

    def test_battery_decreases_over_time(self) -> None:
        drone = GT3Drone()
        first = drone.simulate().battery
        for _ in range(20):
            drone.simulate()
        last = drone.simulate().battery
        assert last < first

    def test_extra_has_motor_pwm(self) -> None:
        pkt = GT3Drone().simulate()
        assert "motor_pwm" in pkt.extra
        assert len(pkt.extra["motor_pwm"]) == 4


class TestZ908FPVSimulate:
    def test_returns_packet(self) -> None:
        fpv = Z908FPV("Z908-test")
        pkt = fpv.simulate()
        _assert_valid_packet(pkt, "Z908")

    def test_has_battery(self) -> None:
        pkt = Z908FPV().simulate()
        assert pkt.battery is not None
        assert 0.0 <= pkt.battery <= 100.0

    def test_extra_has_rssi(self) -> None:
        pkt = Z908FPV().simulate()
        assert "rssi" in pkt.extra

    def test_video_stream_in_extra(self) -> None:
        fpv = Z908FPV(video_stream_url="rtsp://192.168.1.10/live")
        pkt = fpv.simulate()
        assert pkt.extra.get("video_stream") == "rtsp://192.168.1.10/live"


class TestGo2DogSimulate:
    def test_returns_packet(self) -> None:
        dog = Go2Dog("Go2-test")
        pkt = dog.simulate()
        _assert_valid_packet(pkt, "Go2")

    def test_has_imu(self) -> None:
        pkt = Go2Dog().simulate()
        assert pkt.imu is not None
        assert pkt.imu.az == pytest.approx(9.81, abs=0.5)

    def test_extra_has_joints(self) -> None:
        pkt = Go2Dog().simulate()
        assert "joint_positions" in pkt.extra
        assert len(pkt.extra["joint_positions"]) == 12


class TestRobotArmSimulate:
    def test_returns_packet(self) -> None:
        arm = RobotArm("ARM-test")
        pkt = arm.simulate()
        _assert_valid_packet(pkt, "RobotArm")

    def test_extra_has_joint_angles(self) -> None:
        pkt = RobotArm().simulate()
        assert "joint_angles" in pkt.extra
        assert len(pkt.extra["joint_angles"]) == 6

    def test_extra_has_end_effector(self) -> None:
        pkt = RobotArm().simulate()
        ee = pkt.extra.get("end_effector", {})
        assert "x" in ee and "y" in ee and "z" in ee

    def test_extra_has_temperatures(self) -> None:
        pkt = RobotArm().simulate()
        temps = pkt.extra.get("temperatures", [])
        assert len(temps) == 6
        assert all(t >= 20.0 for t in temps)


class TestCNCMachineSimulate:
    def test_returns_packet(self) -> None:
        cnc = CNCMachine("CNC-test")
        pkt = cnc.simulate()
        _assert_valid_packet(pkt, "CNC")

    def test_extra_has_spindle_rpm(self) -> None:
        pkt = CNCMachine().simulate()
        assert "spindle_rpm" in pkt.extra
        assert pkt.extra["spindle_rpm"] > 0

    def test_extra_has_axis(self) -> None:
        pkt = CNCMachine().simulate()
        assert "axis" in pkt.extra
        for ax in ("x", "y", "z"):
            assert ax in pkt.extra["axis"]


class TestLegoSubmarineSimulate:
    def test_returns_packet(self) -> None:
        sub = LegoSubmarine("SUB-test")
        pkt = sub.simulate()
        _assert_valid_packet(pkt, "Submarine")

    def test_has_battery(self) -> None:
        pkt = LegoSubmarine().simulate()
        assert pkt.battery is not None and 0.0 <= pkt.battery <= 100.0

    def test_extra_has_depth(self) -> None:
        pkt = LegoSubmarine().simulate()
        assert "depth" in pkt.extra
        assert pkt.extra["depth"] >= 0.0

    def test_leak_triggers_error_status(self) -> None:
        sub = LegoSubmarine()
        sub._leak_detected = True
        sub._battery = 90.0
        pkt = sub.simulate()
        assert pkt.status == DeviceStatus.ERROR.value
