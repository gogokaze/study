# Godot 3.2 — Angry Birds 클론 프로젝트 코드 분석

## 프로젝트 구조

```
book/
├── Globals/          # 전역 싱글톤 (AutoLoad)
├── Objects/
│   ├── Slingshot/    # 새총 + 입력 + 탄도 그리기
│   ├── Projectile/   # 발사체 (RigidBody2D)
│   ├── Enemy/        # 적 (RigidBody2D)
│   ├── Obstacles/    # 장애물 (나무, 돌)
│   ├── Pool/         # 오브젝트 풀
│   ├── Score/        # 점수 UI
│   └── VFX/          # 파티클 이펙트
└── Scenes/
    ├── Main.tscn     # 씬 전환 컨테이너
    ├── MainMenu/
    ├── LevelSelection/
    └── Levels/
        └── LevelBase/  # 레벨 공통 로직
            ├── LevelBase.gd
            ├── ProjectilesLoader.gd
            ├── EnemiesHandler.gd
            └── CameraFocus.gd
```

---

## 핵심 시스템별 분석

### 1. Globals (AutoLoad 싱글톤)

```gdscript
# Globals/Globals.gd
extends Node

var main_scene: Node
var current_level_index = 1

func goto_scene(new_scene: String, params = {}):
    if main_scene == null:
        return get_tree().change_scene(new_scene)
    main_scene.load_scene(new_scene, params)
```

- Godot의 **AutoLoad** 기능으로 등록해 어디서든 `Globals.goto_scene(...)` 호출 가능
- `main_scene`을 통해 씬 전환 시 파라미터 전달 (기본 `change_scene`은 파라미터 불가)

---

### 2. Slingshot (새총)

```gdscript
# Objects/Slingshot/Slingshot.gd
enum States { IDLE, LOADING_PROJECTILE, PROJECTILE_LOADED, AIMING }

func update_launch_impulse():
    return slingshot_elastic_force * ($InputArea.global_position - elastic_pad.global_position)
```

**상태 머신 구조:**

```
IDLE
  ↓ (projectile 장전)
LOADING_PROJECTILE  → Tween으로 발사체를 RestPosition으로 이동
  ↓ (터치 드래그)
AIMING              → 탄도 미리보기 + 고무줄 시각화
  ↓ (터치 해제)
IDLE                → impulse 적용 후 발사
```

**발사 힘 계산:**
```
발사 impulse = elastic_force × (InputArea위치 - 패드위치)
```
- 당긴 거리 × 방향 = 벡터 힘 (물리적으로 훅 법칙과 동일)

---

### 3. TrajectoryDrawer (탄도 미리보기)

```gdscript
func trajectory_equation(x: float, teta: float, g: float, v0: float) -> float:
    return -(x * tan(teta) - (g * pow(x, 2)) / (2.0 * pow(v0, 2) * pow(cos(teta), 2)))
```

**포물선 운동 공식:**

```
y = x·tan(θ) - (g·x²) / (2·v₀²·cos²(θ))
```

- x축 50개 점을 계산해 `draw_circle()`로 알파 감쇠 점선 표시
- `_draw()` 오버라이드 후 `update()` 호출로 매 프레임 갱신

---

### 4. Projectile (발사체)

```gdscript
class_name Projectile
extends RigidBody2D

enum STATES { IDLE, MOVING, STOPPED }

func apply_impulse(offset: Vector2, impulse: Vector2):
    .apply_impulse(offset, impulse)   # 부모 메서드 호출 (GDScript의 super)
    state = STATES.MOVING

func _moving_process():
    if linear_velocity.length() < 20 and len(get_colliding_bodies()) > 0:
        emit_signal("almost_stopped")
        state = STATES.STOPPED
```

- `class_name`으로 타입 등록 → 다른 스크립트에서 `proj is Projectile` 타입 체크 가능
- `.메서드()` 문법 = GDScript 3.x의 super 호출 방식

---

### 5. Enemy (적)

```gdscript
class_name Enemy
extends RigidBody2D

func _integrate_forces(state):
    for collision_idx in state.get_contact_count():
        var collider = state.get_contact_collider_object(collision_idx)
        if collider is RigidBody2D:
            var impact_momentum = collider.mass * collider.linear_velocity - mass * linear_velocity
            if impact_momentum.length() >= get_destruction_threshold(collider):
                emit_signal("destroyed", self, collider, impact_momentum)
```

**충격량 기반 파괴 판정:**
```
충격량 = 충돌체질량 × 충돌체속도 - 자신질량 × 자신속도
```
- `_integrate_forces`는 물리 엔진 내부에서 호출 → 가장 정확한 충돌 감지 타이밍
- 장애물(Obstacle)과 발사체(Projectile)는 서로 다른 파괴 임계값 적용

---

### 6. Object Pool (오브젝트 풀)

```gdscript
# Objects/Pool/Node2DPool.gd
func get_instance():
    if inactive_nodes_container.get_child_count() > 0:
        obj = inactive_nodes_container.get_child(0)
        inactive_nodes_container.remove_child(obj)
    else:
        obj = _create_obj()   # 풀 소진 시 새로 생성
    return obj

func pool(obj):           # 반납
    active_objs.erase(obj)
    inactive_nodes_container.add_child(obj)

func check_unused_objs(): # 타이머로 주기적 수거
    for obj in active_objs:
        if obj.can_be_pooled:
            pool(obj)
```

**풀 동작 원리:**

```
[inactive_nodes_container]  ←→  [active_objs 리스트]
         ↑ pool()                    ↑ get_instance()
         └──────── Timer로 주기 수거 ──┘
```

- `modulate.a = 0/1`로 비활성/활성 시각 처리
- `PoolableNode2D`를 상속한 오브젝트만 사용 가능

---

### 7. ProjectilesLoader (발사체 순서 관리)

```gdscript
func load_projectile():
    var proj = get_child(0)
    if proj == null:
        yield(get_tree().create_timer(3), "timeout")
        emit_signal("level_finished")
        return
    # 애니메이션 후 슬링샷에 장전
    $AnimationPlayer.play("load_projectile")
    yield($AnimationPlayer, "animation_finished")
    slingshot.load_projectile(proj)

func _on_Slingshot_projectile_launched(projectile):
    yield(get_tree().create_timer(1), "timeout")
    load_projectile()   # 다음 발사체 자동 장전
```

- `yield(signal)` = GDScript 3.x 코루틴 (4.x에서는 `await`으로 변경)
- 자식 노드를 순서대로 꺼내는 방식으로 발사 순서 관리

---

## Godot 3.x 핵심 개념 정리

| 개념 | 설명 | 예시 |
|------|------|------|
| `onready var` | 씬 로드 완료 후 참조 | `onready var hp = $HPBar` |
| `export var` | 인스펙터 편집 가능 변수 | `export var speed = 100` |
| `yield(signal)` | 신호 대기 코루틴 | `yield($Anim, "finished")` |
| `.method()` | super 메서드 호출 | `.apply_impulse(...)` |
| `class_name` | 글로벌 타입 등록 | `class_name Projectile` |
| `emit_signal` | 신호 발생 | `emit_signal("destroyed", self)` |
| `_integrate_forces` | 물리 내부 콜백 | 충돌 감지 최적 위치 |
| `_draw()` + `update()` | 커스텀 드로우 | 탄도 점선 렌더링 |

---

## 아키텍처 패턴

```
Signal 기반 분리:
  Enemy.destroyed
      ↓
  EnemiesHandler._on_enemy_destroyed
      ↓
  Score 업데이트 + VFX 재생

씬 전환:
  Globals.goto_scene("res://Scenes/...tscn", {params})
      ↓
  Main.load_scene() → 애니메이션 후 씬 교체
```

- **Composition over Inheritance**: LevelBase는 자식 노드(EnemiesHandler, ProjectilesLoader 등)에 기능 위임
- **Signal Bus**: 직접 참조 대신 signal로 결합도 최소화
