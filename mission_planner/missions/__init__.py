"""Built-in mission definitions."""

from mission_planner.missions.drone_patrol import DronePatrolMission
from mission_planner.missions.go2_warehouse import Go2WarehouseMission
from mission_planner.missions.arm_pick_place import ArmPickPlaceMission

__all__ = ["DronePatrolMission", "Go2WarehouseMission", "ArmPickPlaceMission"]
