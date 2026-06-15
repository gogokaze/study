# Unity Mirror 네트워킹 — 축구 게임 분석

## Mirror 아키텍처 개요

```
┌──────────────┐        TCP/UDP        ┌──────────────┐
│   Client A   │◄─────────────────────►│    Server    │
│ NetworkClient│                       │NetworkServer │
└──────────────┘                       └──────┬───────┘
                                              │
┌──────────────┐                       ┌──────▼───────┐
│   Client B   │◄─────────────────────►│  Authority   │
│ NetworkClient│                       │  (물리/상태) │
└──────────────┘                       └──────────────┘
```

Mirror는 **서버 권위적(Server Authoritative)** 모델:
- 서버만 게임 상태를 결정
- 클라이언트는 입력 전송 + 결과 수신

---

## NetworkClient.cs 핵심 구조

### 연결 상태 머신

```csharp
public enum ConnectState {
    None,
    Connecting,    // Connect() 호출 후 ~ OnTransportConnected() 전
    Connected,
    Disconnecting, // Disconnect() 호출 후 ~ OnTransportDisconnected() 전
    Disconnected
}

// 외부에서 상태 확인
public static bool active      => Connecting || Connected
public static bool isConnected => connectState == ConnectState.Connected
public static bool isHostClient => connection is LocalConnectionToServer
```

### 핵심 딕셔너리 3개

```csharp
// 메시지 ID → 핸들러 함수
Dictionary<ushort, NetworkMessageDelegate> handlers

// 클라이언트가 볼 수 있는 스폰된 오브젝트 (netId 기준)
Dictionary<uint, NetworkIdentity> spawned

// 스폰 가능한 프리팹 등록 (Guid = assetId)
Dictionary<Guid, GameObject> prefabs
```

---

## Host vs Remote 클라이언트 분기

```csharp
internal static void RegisterSystemHandlers(bool hostMode) {
    if (hostMode) {
        // 같은 프로세스 → 서버가 이미 상태 보유
        // SpawnMessage는 처리하되 EntityStateMessage는 무시
        RegisterHandler<SpawnMessage>(OnHostClientSpawn);
        RegisterHandler<EntityStateMessage>(_ => {});        // 무시
        RegisterHandler<ObjectSpawnFinishedMessage>(_ => {}); // 무시
    } else {
        // 원격 클라이언트 → 모든 메시지 처리
        RegisterHandler<SpawnMessage>(OnSpawn);
        RegisterHandler<EntityStateMessage>(OnEntityStateMessage);
        RegisterHandler<ObjectSpawnFinishedMessage>(OnObjectSpawnFinished);
    }

    // 공통 핸들러 (Host/Remote 동일)
    RegisterHandler<ChangeOwnerMessage>(OnChangeOwner);
    RegisterHandler<RpcMessage>(OnRPCMessage);
}
```

---

## Transport 추상화

```csharp
// Transport를 교체해도 NetworkClient 코드 변경 없음
Transport.activeTransport.OnClientConnected    = OnTransportConnected;
Transport.activeTransport.OnClientDataReceived = OnTransportData;
Transport.activeTransport.OnClientDisconnected = OnTransportDisconnected;
```

| Transport | 특징 | 용도 |
|-----------|------|------|
| KCP | 빠른 UDP, 재전송 보장 | 기본 권장 |
| WebSockets | 브라우저 지원 | WebGL 빌드 |
| Telepathy | TCP 기반 | 안정적 연결 |
| Steam | P2P, 방화벽 우회 | Steam 게임 |

---

## 축구 게임 Mirror 적용 패턴

### NetworkBehaviour 컴포넌트 분리

```csharp
// 볼 — 서버만 물리 계산, 클라이언트는 보간
public class SoccerBall : NetworkBehaviour {
    [SyncVar] Vector3 serverPosition;

    void FixedUpdate() {
        if (isServer) {
            // 물리 계산
            serverPosition = rb.position;
        } else {
            // 보간으로 부드럽게 표시
            transform.position = Vector3.Lerp(transform.position, serverPosition, 0.1f);
        }
    }
}

// 플레이어 — 입력은 클라이언트, 실행은 서버
public class SoccerPlayer : NetworkBehaviour {
    void Update() {
        if (!isLocalPlayer) return;
        if (Input.GetButtonDown("Kick"))
            CmdKickBall();  // 서버에 명령 전송
    }

    [Command]
    void CmdKickBall() {
        // 서버에서 실행
        ball.GetComponent<Rigidbody>().AddForce(transform.forward * kickForce);
    }
}
```

### 골 판정

```csharp
// 서버에서만 판정
[Server]
void OnTriggerEnter(Collider other) {
    if (other.CompareTag("Ball")) {
        RpcGoalScored(teamIndex);  // 모든 클라이언트에 알림
    }
}

[ClientRpc]
void RpcGoalScored(int team) {
    scoreUI.UpdateScore(team);
    PlayGoalAnimation();
}
```

---

## YFL 드론 시뮬레이션 적용 포인트

| Mirror 패턴 | YFL 적용 |
|------------|---------|
| `SyncVar` | 드론 위치/배터리/상태 동기화 |
| `[Command]` | GCS → 드론 명령 (이륙/착륙/웨이포인트) |
| `[ClientRpc]` | 드론 이벤트 → 모든 모니터 화면 갱신 |
| `NetworkTransform` | 드론 3D 위치 보간 |
| Host 모드 | 단일 PC에서 GCS + 시뮬 드론 동시 실행 |
