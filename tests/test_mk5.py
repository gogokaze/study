"""MK.5 architecture tests — World Model, Event Bus, Agents, Behavior Tree."""
import asyncio
import pytest
from world_model.model import SharedWorldModel, WorldObject, ObjectType, ObjectState
from world_model.events import EventBus, EventType, EventSeverity, RoboticsEvent
from behavior_tree.nodes import (
    NodeStatus, SequenceNode, SelectorNode, ConditionNode, ActionNode, InverterNode,
)
from agents.scout_agent import ScoutAgent
from agents.transport_agent import TransportAgent
from devices.gt3_drone import GT3Drone
from devices.go2_dog import Go2Dog


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# SharedWorldModel
# ---------------------------------------------------------------------------

class TestSharedWorldModel:
    def _model(self):
        return SharedWorldModel()

    def _obj(self, oid="QR_001"):
        return WorldObject(id=oid, object_type=ObjectType.QR_CODE, state=ObjectState.FOUND,
                           x=1.0, y=2.0, z=0.0, confidence=0.95, discovered_by="scout-1")

    def test_upsert_and_get(self):
        async def _():
            m = self._model()
            await m.upsert(self._obj())
            r = await m.get("QR_001")
            assert r is not None and r.id == "QR_001"
        asyncio.run(_())

    def test_get_nonexistent_returns_none(self):
        async def _():
            assert await self._model().get("NOPE") is None
        asyncio.run(_())

    def test_upsert_idempotent(self):
        async def _():
            m = self._model()
            obj = self._obj()
            await m.upsert(obj)
            await m.upsert(obj)
            assert len(await m.query(object_type=ObjectType.QR_CODE)) == 1
        asyncio.run(_())

    def test_query_by_type(self):
        async def _():
            m = self._model()
            await m.upsert(WorldObject(id="QR_A", object_type=ObjectType.QR_CODE, state=ObjectState.FOUND))
            await m.upsert(WorldObject(id="ROB_A", object_type=ObjectType.ROBOT, state=ObjectState.ACTIVE))
            qrs = await m.query(object_type=ObjectType.QR_CODE)
            assert len(qrs) == 1 and qrs[0].id == "QR_A"
        asyncio.run(_())

    def test_query_by_state(self):
        async def _():
            m = self._model()
            await m.upsert(WorldObject(id="O1", object_type=ObjectType.ITEM, state=ObjectState.FOUND))
            await m.upsert(WorldObject(id="O2", object_type=ObjectType.ITEM, state=ObjectState.COMPLETED))
            found = await m.query(state=ObjectState.FOUND)
            assert len(found) == 1 and found[0].id == "O1"
        asyncio.run(_())

    def test_assign(self):
        async def _():
            m = self._model()
            await m.upsert(self._obj())
            await m.assign("QR_001", "transport-1")
            obj = await m.get("QR_001")
            assert obj.assigned_to == "transport-1"
        asyncio.run(_())

    def test_assign_nonexistent_returns_false(self):
        async def _():
            assert await self._model().assign("GHOST", "agent-1") is False
        asyncio.run(_())

    def test_update_state(self):
        async def _():
            m = self._model()
            await m.upsert(self._obj())
            await m.update_state("QR_001", ObjectState.COMPLETED)
            obj = await m.get("QR_001")
            assert obj.state == ObjectState.COMPLETED
        asyncio.run(_())

    def test_subscribe_called_on_upsert(self):
        async def _():
            m = self._model()
            received = []
            m.subscribe(lambda o: received.append(o.id))
            await m.upsert(self._obj())
            assert "QR_001" in received
        asyncio.run(_())

    def test_snapshot_returns_dict(self):
        async def _():
            m = self._model()
            await m.upsert(self._obj())
            snap = await m.snapshot()
            assert "QR_001" in snap and snap["QR_001"]["state"] == "found"
        asyncio.run(_())


# ---------------------------------------------------------------------------
# EventBus
# ---------------------------------------------------------------------------

class TestEventBus:
    def _event(self, event_type=EventType.QR_FOUND):
        return RoboticsEvent(event_type=event_type, agent_id="scout-1",
                             severity=EventSeverity.INFO, payload={"x": 1.0})

    def test_publish_and_subscribe(self):
        async def _():
            bus = EventBus()
            received = []
            bus.subscribe(EventType.QR_FOUND, lambda e: received.append(e.event_type))
            await bus.publish(self._event())
            assert EventType.QR_FOUND in received
        asyncio.run(_())

    def test_subscriber_not_called_for_other_type(self):
        async def _():
            bus = EventBus()
            received = []
            bus.subscribe(EventType.BATTERY_LOW, lambda e: received.append(e))
            await bus.publish(self._event(EventType.QR_FOUND))
            assert len(received) == 0
        asyncio.run(_())

    def test_subscribe_all_receives_every_event(self):
        async def _():
            bus = EventBus()
            received = []
            bus.subscribe_all(lambda e: received.append(e.event_type))
            await bus.publish(self._event(EventType.QR_FOUND))
            await bus.publish(self._event(EventType.BATTERY_LOW))
            assert EventType.QR_FOUND in received and EventType.BATTERY_LOW in received
        asyncio.run(_())

    def test_history_records_events(self):
        async def _():
            bus = EventBus()
            await bus.publish(self._event(EventType.QR_FOUND))
            await bus.publish(self._event(EventType.BATTERY_LOW))
            assert len(bus.get_history()) == 2
        asyncio.run(_())

    def test_history_filter_by_type(self):
        async def _():
            bus = EventBus()
            await bus.publish(self._event(EventType.QR_FOUND))
            await bus.publish(self._event(EventType.BATTERY_LOW))
            hist = bus.get_history(event_type=EventType.QR_FOUND)
            assert len(hist) == 1 and hist[0].event_type == EventType.QR_FOUND
        asyncio.run(_())

    def test_unsubscribe(self):
        async def _():
            bus = EventBus()
            received = []
            cb = lambda e: received.append(e)
            bus.subscribe(EventType.QR_FOUND, cb)
            bus.unsubscribe(EventType.QR_FOUND, cb)
            await bus.publish(self._event())
            assert len(received) == 0
        asyncio.run(_())


# ---------------------------------------------------------------------------
# Behavior Tree Nodes
# ---------------------------------------------------------------------------

class TestBTNodes:
    def test_condition_true(self):
        async def _():
            assert await ConditionNode(lambda ctx: True).tick({}) == NodeStatus.SUCCESS
        asyncio.run(_())

    def test_condition_false(self):
        async def _():
            assert await ConditionNode(lambda ctx: False).tick({}) == NodeStatus.FAILURE
        asyncio.run(_())

    def test_action_returns_success(self):
        async def _():
            assert await ActionNode(lambda ctx: NodeStatus.SUCCESS).tick({}) == NodeStatus.SUCCESS
        asyncio.run(_())

    def test_sequence_all_success(self):
        async def _():
            s = SequenceNode([ConditionNode(lambda ctx: True), ConditionNode(lambda ctx: True)])
            assert await s.tick({}) == NodeStatus.SUCCESS
        asyncio.run(_())

    def test_sequence_fails_on_first_failure(self):
        async def _():
            executed = []
            s = SequenceNode([
                ConditionNode(lambda ctx: False),
                ActionNode(lambda ctx: executed.append(1) or NodeStatus.SUCCESS),
            ])
            assert await s.tick({}) == NodeStatus.FAILURE
            assert len(executed) == 0
        asyncio.run(_())

    def test_selector_returns_success_on_first_success(self):
        async def _():
            s = SelectorNode([ConditionNode(lambda ctx: False), ConditionNode(lambda ctx: True)])
            assert await s.tick({}) == NodeStatus.SUCCESS
        asyncio.run(_())

    def test_selector_fails_if_all_fail(self):
        async def _():
            s = SelectorNode([ConditionNode(lambda ctx: False), ConditionNode(lambda ctx: False)])
            assert await s.tick({}) == NodeStatus.FAILURE
        asyncio.run(_())

    def test_inverter_flips_success(self):
        async def _():
            assert await InverterNode(ConditionNode(lambda ctx: True)).tick({}) == NodeStatus.FAILURE
        asyncio.run(_())

    def test_inverter_flips_failure(self):
        async def _():
            assert await InverterNode(ConditionNode(lambda ctx: False)).tick({}) == NodeStatus.SUCCESS
        asyncio.run(_())


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

class TestScoutAgent:
    def _setup(self):
        wm = SharedWorldModel()
        bus = EventBus()
        agent = ScoutAgent("scout-1", wm, bus)
        agent.bind_device(GT3Drone("GT3-TEST"))
        return agent, wm, bus

    def test_run_cycle_completes(self):
        async def _():
            agent, _, _ = self._setup()
            await agent.run_cycle()
        asyncio.run(_())

    def test_perceive_does_not_raise(self):
        async def _():
            agent, _, _ = self._setup()
            await agent.perceive()
        asyncio.run(_())

    def test_battery_low_event_published_on_low_battery(self):
        async def _():
            agent, _, bus = self._setup()
            agent._device._battery = 10.0
            received = []
            bus.subscribe(EventType.BATTERY_LOW, lambda e: received.append(e))
            await agent.perceive()
            assert len(received) == 1
        asyncio.run(_())


class TestTransportAgent:
    def _setup(self):
        wm = SharedWorldModel()
        bus = EventBus()
        agent = TransportAgent("transport-1", wm, bus)
        agent.bind_device(Go2Dog("GO2-TEST"))
        return agent, wm, bus

    def test_run_cycle_completes(self):
        async def _():
            agent, _, _ = self._setup()
            await agent.run_cycle()
        asyncio.run(_())

    def test_navigates_to_found_qr(self):
        async def _():
            agent, wm, _ = self._setup()
            qr = WorldObject(id="QR_NAV", object_type=ObjectType.QR_CODE, state=ObjectState.FOUND,
                             x=5.0, y=5.0, z=0.0)
            await wm.upsert(qr)
            action = await agent.decide()
            assert action == "NAVIGATE"
        asyncio.run(_())
