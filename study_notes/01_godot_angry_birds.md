# Godot 3.2 앵그리버드 클론 분석

## 프로젝트 구조

```
Main.gd
├── Scenes/Levels/LevelBase/
│   ├── LevelBase.gd              ← 레벨 진입점
│   ├── CameraFocus.gd            ← 카메라 추적 (발사체 따라감)
│   ├── ProjectilesLoader.gd      ← 새 발사 순서 관리
│   ├── EnemiesHandler.gd         ← 적 생존 여부 체크
│   └── ParticlesManager.gd       ← VFX 오브젝트 풀 관리
├── Objects/Slingshot/
│   ├── Slingshot.gd              ← 핵심 입력·발사 FSM
│   ├── InputArea.gd              ← 터치/마우스 감지
│   └── TrajectoryDrawer.gd       ← 포물선 궤적 미리보기
├── Objects/Projectile/
│   └── Projectile.gd             ← RigidBody2D (새)
├── Objects/Enemy/
│   └── Enemy.gd                  ← RigidBody2D (돼지), 파괴 판정
├── Objects/Obstacles/
│   └── StoneObstacle/            ← 충돌 가능한 구조물
└── Objects/Pool/
    └── Node2DPool.gd             ← 오브젝트 재사용 풀
```

---

## Slingshot FSM (새총 상태 머신)

```
IDLE
  │ projectile 접근
  ▼
LOADING_PROJECTILE  ← Tween으로 새를 RestPosition으로 이동
  │ tween 완료
  ▼
PROJECTILE_LOADED
  │ 드래그 시작
  ▼
AIMING              ← 궤적 그리기, 고무줄 그래픽 갱신
  │ 손/마우스 놓음
  ▼
launch() 실행 → IDLE
```

### 핵심 코드 — 발사 충격량

```gdscript
# Hooke's Law 변형: F = k · x
# elastic_force = k (탄성계수), (InputArea.pos - elastic_pad.pos) = 변위
func update_launch_impulse():
    return slingshot_elastic_force * ($InputArea.global_position - elastic_pad.global_position)

func launch(launch_impulse: Vector2):
    projectile.mode = RigidBody2D.MODE_RIGID
    projectile.apply_impulse(Vector2(), launch_impulse)
    emit_signal("projectile_launched", projectile)
```

---

## Projectile (새) — RigidBody2D

```gdscript
class_name Projectile
extends RigidBody2D

enum STATES { IDLE, MOVING, STOPPED }

func _physics_process(delta):
    match state:
        STATES.MOVING:
            trail.emitting = true
            trail.direction = -linear_velocity.normalized()  # 꼬리 파티클
            _moving_process()

func _moving_process():
    # 속도 < 20 && 충돌 중이면 정지
    if linear_velocity.length() < 20 and len(get_colliding_bodies()) > 0:
        emit_signal("almost_stopped")
        state = STATES.STOPPED
```

---

## Enemy (돼지) — 파괴 판정

```gdscript
const DESTROY_THRESHOLD_BY_OBSTACLES = 400   # 구조물과 충돌
const DESTROY_THRESHOLD = 1600               # 새와 직접 충돌

func _integrate_forces(state):
    for i in state.get_contact_count():
        var collider = state.get_contact_collider_object(i)
        if collider is RigidBody2D:
            # 운동량 변화량 = 충격량
            var impact_momentum = collider.mass * collider.linear_velocity \
                                - mass * linear_velocity
            if impact_momentum.length() >= get_destruction_threshold(collider):
                emit_signal("destroyed", self, collider, impact_momentum)
```

**왜 threshold가 다른가?**
- 구조물(Obstacle)은 느리게 움직여서 충격량이 작음 → 낮은 임계값
- 새(Projectile)는 빠르게 날아옴 → 높은 임계값으로 직접 타격만 파괴

---

## TrajectoryDrawer — 포물선 미리보기

발사 전 궤적은 등가속도 운동 공식으로 계산:

```
pos(t) = initial_pos + velocity * t + 0.5 * gravity * t²
```

```gdscript
# Slingshot.gd에서 호출
trajectory_drawer.draw_trajectory(
    launch_impulse / projectile.mass,   # 초속도 (m/s)
    projectile.global_position,          # 시작점
    projectile.gravity_scale * ProjectSettings.get("physics/2d/default_gravity")
)
```

---

## 오브젝트 풀 (Node2DPool)

파티클·점수 스프라이트를 매번 인스턴스화하면 GC 스파이크 발생.  
`Node2DPool`이 비활성 노드를 재사용:

```
요청 → 풀에 비활성 노드 있음? → 재활성화 반환
                              없음? → 새로 인스턴스화
사용 완료 → 비활성화 후 풀 반환
```

---

## YFL 프로젝트 적용 포인트

| Godot 패턴 | YFL 적용 가능 영역 |
|-----------|-----------------|
| FSM (상태 머신) | 드론 임무 상태 (IDLE/TAKEOFF/PATROL/RETURN) |
| 오브젝트 풀 | 텔레메트리 파티클 VFX, UI 알림 재사용 |
| Signal 기반 이벤트 | EventBus 패턴 (이미 `world_model/events.py` 에 구현됨) |
| RigidBody 충돌 판정 | 드론 충돌 감지 시뮬레이션 |
