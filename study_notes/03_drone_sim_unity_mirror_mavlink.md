# 드론 시뮬레이션 아키텍처 — Unity + Mirror + MAVLink

## 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  Unity 씬 (시각화 + 멀티플레이)                              │
│                                                             │
│  ┌─────────────────┐  Mirror   ┌─────────────────────────┐ │
│  │  GCS Client     │◄─────────►│  Sim Server             │ │
│  │  (카메라·HUD)   │  RPC/Sync │  (권위적 드론 상태)      │ │
│  └─────────────────┘           └──────────┬──────────────┘ │
└────────────────────────────────────────────┼───────────────┘
                                             │ UDP (14550)
                                  ┌──────────▼──────────────┐
                                  │  MAVLink Bridge (C#)    │
                                  │  NED ↔ Unity 좌표 변환  │
                                  └──────────┬──────────────┘
                                             │ MAVLink v2
                                  ┌──────────▼──────────────┐
                                  │  SITL Autopilot         │
                                  │  ArduPilot / PX4        │
                                  └──────────┬──────────────┘
                                             │ Gazebo Plugin
                                  ┌──────────▼──────────────┐
                                  │  Gazebo 물리 엔진        │
                                  └─────────────────────────┘
```

---

## MAVLink 브릿지 설계

### 좌표계 변환 (NED → Unity)

MAVLink는 **NED** (North-East-Down), Unity는 **Y-Up Left-Hand**:

| MAVLink NED | 의미 | Unity 축 |
|------------|------|---------|
| X (북, +) | 전방 | Z |
| Y (동, +) | 우측 | X |
| Z (하, +) | 아래 | -Y |

```csharp
Vector3 NedToUnity(float n, float e, float d) {
    return new Vector3(e, -d, n);
}

Quaternion NedAttitudeToUnity(float roll, float pitch, float yaw) {
    // NED 오일러 → Unity 쿼터니언
    return Quaternion.Euler(-pitch * Mathf.Rad2Deg,
                             yaw  * Mathf.Rad2Deg,
                            -roll * Mathf.Rad2Deg);
}
```

### MAVLink Bridge 스켈레톤 (C#)

```csharp
public class MAVLinkBridge : MonoBehaviour {
    UdpClient udpSitl;
    MavlinkParser parser = new MavlinkParser();

    [SyncVar] Vector3 dronePosition;
    [SyncVar] Quaternion droneRotation;

    void Start() {
        udpSitl = new UdpClient(14550);
    }

    void Update() {
        if (!isServer) return;

        // 1. SITL → Unity: 위치·자세 수신
        while (udpSitl.Available > 0) {
            var ep = new IPEndPoint(IPAddress.Any, 0);
            byte[] data = udpSitl.Receive(ref ep);
            var msg = parser.ReadPacket(data);

            switch ((MAVLink.MAVLINK_MSG_ID)msg.msgid) {
                case MAVLink.MAVLINK_MSG_ID.LOCAL_POSITION_NED:
                    var pos = (MAVLink.mavlink_local_position_ned_t)msg.data;
                    dronePosition = NedToUnity(pos.x, pos.y, pos.z);
                    break;

                case MAVLink.MAVLINK_MSG_ID.ATTITUDE:
                    var att = (MAVLink.mavlink_attitude_t)msg.data;
                    droneRotation = NedAttitudeToUnity(att.roll, att.pitch, att.yaw);
                    break;
            }
        }

        // 2. Unity → SITL: RC 조종 입력 전송
        if (hasAuthority)
            SendRCOverride(throttle, roll, pitch, yaw);
    }

    void SendRCOverride(float thr, float rol, float pit, float yaw) {
        var rc = new MAVLink.mavlink_rc_channels_override_t {
            chan1_raw = (ushort)(1500 + rol * 500),   // Roll
            chan2_raw = (ushort)(1500 + pit * 500),   // Pitch
            chan3_raw = (ushort)(1000 + thr * 1000),  // Throttle
            chan4_raw = (ushort)(1500 + yaw * 500),   // Yaw
        };
        byte[] pkt = parser.GenerateMAVLinkPacket20(
            MAVLink.MAVLINK_MSG_ID.RC_CHANNELS_OVERRIDE, rc);
        udpSitl.Send(pkt, pkt.Length, sitlEndpoint);
    }
}
```

---

## Mirror 역할 분배

```
GCS Client                          Sim Server
    │                                    │
    │─── [Command] CmdSetWaypoint() ────►│ 서버에서 경로 계산
    │                                    │
    │◄── [ClientRpc] RpcDroneState() ───│ 위치·배터리·상태 브로드캐스트
    │                                    │
    │    [SyncVar] position/rotation     │ NetworkTransform 보간
```

| 컴포넌트 | Mirror 어트리뷰트 | 역할 |
|---------|-----------------|------|
| 위치/자세 | `[SyncVar]` | SITL → 모든 클라이언트 동기화 |
| 배터리/상태 | `[SyncVar]` | 실시간 HUD 갱신 |
| 웨이포인트 명령 | `[Command]` | GCS → 서버 → SITL 전달 |
| 이벤트 (착륙 등) | `[ClientRpc]` | 서버 → 전체 클라이언트 알림 |

---

## 주요 MAVLink 메시지

| 메시지 | ID | 방향 | 내용 |
|-------|-----|------|------|
| `LOCAL_POSITION_NED` | 32 | SITL→Unity | 위치 (x,y,z m) |
| `ATTITUDE` | 30 | SITL→Unity | 자세 (roll,pitch,yaw rad) |
| `BATTERY_STATUS` | 147 | SITL→Unity | 배터리 % |
| `RC_CHANNELS_OVERRIDE` | 70 | Unity→SITL | 조종 입력 |
| `SET_MODE` | 11 | Unity→SITL | 비행 모드 변경 |
| `COMMAND_LONG` | 76 | Unity→SITL | 이륙/착륙/RTL |

---

## YFL 기존 코드와 연동

YFL의 `GT3Drone` 텔레메트리를 MAVLink 브릿지와 연결:

```python
# devices/gt3_drone.py 확장 예시
# SITL에서 받은 MAVLink 데이터를 기존 TelemetryPacket으로 변환

from telemetry_hub.schema import TelemetryPacket
from datetime import datetime

def mavlink_to_telemetry(mavlink_pos, mavlink_att, battery) -> TelemetryPacket:
    return TelemetryPacket(
        device_id="gt3-sitl-001",
        device_type="drone",
        timestamp=datetime.utcnow().isoformat(),
        data={
            "latitude":  mavlink_pos.x,   # NED X → 위도 근사
            "longitude": mavlink_pos.y,   # NED Y → 경도 근사
            "altitude":  -mavlink_pos.z,  # NED Z 반전
            "roll":    mavlink_att.roll  * 57.3,
            "pitch":   mavlink_att.pitch * 57.3,
            "yaw":     mavlink_att.yaw   * 57.3,
            "battery": battery,
        }
    )
```

---

## 개발 순서 (권장)

```
1단계: SITL 단독 실행
   ArduPilot SITL → MAVProxy로 메시지 확인

2단계: MAVLink Bridge 구현
   Python mavutil로 프로토타입 → C# 포팅

3단계: Unity 시각화
   DroneObject에 NetworkTransform 부착
   MAVLink 수신 → SyncVar 갱신

4단계: Mirror 멀티플레이
   다중 GCS 클라이언트 접속
   [Command]로 웨이포인트 전송

5단계: YFL 텔레메트리 허브 연동
   Unity 서버 → MQTT 발행 → TelemetryHub 수신
```
