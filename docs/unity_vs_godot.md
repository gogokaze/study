# Unity vs Godot 비교

## 한눈에 보기

| 항목 | Unity | Godot |
|------|-------|-------|
| 언어 | C# | GDScript (Python 유사) / C# |
| 라이선스 | 상용 (무료 티어 있음) | 완전 오픈소스 (MIT) |
| 엔진 크기 | 대형 | 경량 (~40MB) |
| 2D 지원 | 3D 기반 위에 2D | 2D 전용 렌더러 (픽셀 퍼펙트) |
| 3D 지원 | 업계 표준 | Godot 4부터 크게 개선 |
| 에디터 | 별도 설치 | 엔진 = 에디터 (일체형) |
| 빌드 타겟 | PC/모바일/콘솔/웹 | PC/모바일/웹 (콘솔 제한적) |
| 커뮤니티 | 매우 크고 오래됨 | 빠르게 성장 중 |
| 취업 시장 | 게임업계 표준 | 인디/개인 위주 |

---

## 언어 비교

### Unity — C#

```csharp
using UnityEngine;

public class Player : MonoBehaviour
{
    public float speed = 5f;
    private Rigidbody2D rb;

    void Start()
    {
        rb = GetComponent<Rigidbody2D>();
    }

    void Update()
    {
        float h = Input.GetAxis("Horizontal");
        rb.velocity = new Vector2(h * speed, rb.velocity.y);
    }
}
```

### Godot 3.x — GDScript

```gdscript
extends KinematicBody2D

export var speed = 5.0
var velocity = Vector2.ZERO

func _physics_process(delta):
    var h = Input.get_axis("ui_left", "ui_right")
    velocity.x = h * speed
    move_and_slide(velocity)
```

### Godot 4.x — GDScript (최신)

```gdscript
extends CharacterBody2D

@export var speed = 5.0

func _physics_process(delta):
    var h = Input.get_axis("ui_left", "ui_right")
    velocity.x = h * speed
    move_and_slide()
```

**주요 차이:**
- `onready` → `@onready` (4.x)
- `export` → `@export` (4.x)
- `yield` → `await` (4.x)
- `.method()` super 호출 → `super.method()` (4.x)

---

## 씬/오브젝트 구조 개념 비교

### Unity — GameObject + Component

```
GameObject "Player"
  ├── Transform          (위치/회전/크기)
  ├── SpriteRenderer     (스프라이트)
  ├── Rigidbody2D        (물리)
  ├── Collider2D         (충돌)
  └── PlayerController   (스크립트 컴포넌트)
```

- 오브젝트는 빈 컨테이너
- 기능은 **컴포넌트**를 붙여서 조합
- `GetComponent<T>()` 로 다른 컴포넌트 참조

### Godot — Node 트리

```
Node2D "Player"           ← 루트 노드 (스크립트 부착)
  ├── Sprite2D            ← 자식 노드
  ├── CollisionShape2D
  └── AnimationPlayer
```

- 오브젝트 자체가 **타입을 가진 노드**
- 기능은 **상속**으로 결정 (KinematicBody2D, RigidBody2D 등)
- `$NodeName` 또는 `get_node("NodeName")` 으로 자식 참조

---

## 물리 시스템 비교

| 항목 | Unity | Godot |
|------|-------|-------|
| 물리 바디 | Rigidbody2D | RigidBody2D |
| 캐릭터 이동 | CharacterController | CharacterBody2D (`move_and_slide`) |
| 충돌 감지 | OnCollisionEnter2D | `_integrate_forces` / `body_entered` signal |
| 레이어 | Layer/LayerMask | Layer + Mask (비트마스크 동일) |

### Unity 충돌 감지

```csharp
void OnCollisionEnter2D(Collision2D col)
{
    if (col.gameObject.CompareTag("Enemy"))
        TakeDamage();
}
```

### Godot 충돌 감지

```gdscript
func _on_body_entered(body):
    if body.is_in_group("enemy"):
        take_damage()
```

---

## 씬 전환 비교

### Unity

```csharp
using UnityEngine.SceneManagement;

SceneManager.LoadScene("GameScene");
// 파라미터 전달은 별도 방법 필요 (DontDestroyOnLoad, PlayerPrefs 등)
```

### Godot 3.x (이 프로젝트 방식)

```gdscript
# Globals 싱글톤을 통해 파라미터 포함 씬 전환
Globals.goto_scene("res://Scenes/Game.tscn", {"level": 2})
```

### Godot 4.x

```gdscript
get_tree().change_scene_to_file("res://Scenes/Game.tscn")
```

---

## 이벤트/콜백 비교

| 상황 | Unity | Godot |
|------|-------|-------|
| 초기화 | `Start()` | `_ready()` |
| 매 프레임 | `Update()` | `_process(delta)` |
| 물리 프레임 | `FixedUpdate()` | `_physics_process(delta)` |
| 입력 처리 | `Update()` 내 Input | `_input(event)` |
| 물리 내부 | - | `_integrate_forces(state)` |

---

## Signal vs UnityEvent / C# Event

### Unity — C# Event

```csharp
public event Action<int> OnScoreChanged;

// 발생
OnScoreChanged?.Invoke(score);

// 구독
player.OnScoreChanged += UpdateUI;
```

### Unity — UnityEvent (인스펙터 연결)

```csharp
public UnityEvent OnDied;

OnDied.Invoke();
```

### Godot — Signal

```gdscript
signal score_changed(value)    # 선언

emit_signal("score_changed", score)   # 발생 (3.x)
score_changed.emit(score)             # 발생 (4.x)

# 인스펙터 또는 코드로 연결
enemy.connect("destroyed", self, "_on_enemy_destroyed")   # 3.x
enemy.destroyed.connect(_on_enemy_destroyed)              # 4.x
```

---

## Tween 비교

### Unity — DOTween (인기 플러그인)

```csharp
transform.DOMove(targetPos, 0.5f).SetEase(Ease.OutExpo);
```

### Godot 3.x — Tween 노드

```gdscript
var t = Tween.new()
add_child(t)
t.interpolate_property(node, "position", from, to, 0.5,
    Tween.TRANS_EXPO, Tween.EASE_OUT)
t.start()
```

### Godot 4.x — 내장 Tween

```gdscript
var t = create_tween()
t.tween_property(node, "position", to, 0.5).set_trans(Tween.TRANS_EXPO)
```

---

## 오브젝트 풀 패턴

### Unity

```csharp
// Unity 2021+ 내장 풀
var pool = new ObjectPool<GameObject>(
    createFunc: () => Instantiate(prefab),
    actionOnGet: obj => obj.SetActive(true),
    actionOnRelease: obj => obj.SetActive(false)
);

var obj = pool.Get();
pool.Release(obj);
```

### Godot (이 프로젝트 방식)

```gdscript
# Node2DPool.gd
func get_instance():           # pool.Get()
    ...

func pool(obj):                # pool.Release(obj)
    ...
```

---

## 언제 무엇을 선택할까?

```
Unity 선택
  ├── 취업/상용 프로젝트 목표
  ├── 3D 게임 (특히 콘솔 타겟)
  ├── 대형 팀 협업
  └── C# 생태계 활용 (YFL 텔레메트리처럼)

Godot 선택
  ├── 인디/개인 프로젝트
  ├── 2D 게임 (픽셀퍼펙트, 경량)
  ├── 무료 & 오픈소스 필요
  └── 빠른 프로토타입
```

---

## GoJokaze 프로젝트와의 연관

현재 `study` 레포의 `yfl_runtime_files`는 **Unity** 기반:

```
UnityTelemetrySender.cs   →   Unity 플레이어 위치/자세 수집
WebSocketHubClient.cs     →   ws://localhost:8080 으로 전송
Base44RobotDashboard.jsx  →   React 대시보드에서 수신 표시
```

동일한 구조를 **Godot**으로 구현한다면:

```gdscript
# Godot 4.x WebSocket 텔레메트리 예시
extends Node

var ws = WebSocketPeer.new()

func _ready():
    ws.connect_to_url("ws://localhost:8080")

func _process(delta):
    ws.poll()
    var packet = {
        "type": "telemetry",
        "position": {"x": $Player.position.x, "y": $Player.position.y},
        "rotation": $Player.rotation_degrees
    }
    ws.send_text(JSON.stringify(packet))
```
