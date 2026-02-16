# Human-Like Typer v1.0 — Architecture Document

> 총 16파일, ~3,500 LOC (Python 3.11 + CustomTkinter)
> 작성 시점: Step 11 완료 후

---

## 1. 디렉토리 구조

```
human-like-typer/
├── main.py                    # 진입점 (20L)
├── preset_manager.py          # 프리셋 + config.json 관리 (189L)
│
├── core/                      # 비즈니스 로직 (GUI 무관)
│   ├── __init__.py
│   ├── keyboard_map.py        # QWERTY 키 매핑 (186L)
│   ├── timing_model.py        # 타이밍 계산 엔진 (297L)
│   ├── typo_model.py          # 오타 생성 엔진 (423L)
│   ├── typer_engine.py        # 메인 타이핑 엔진 — 상태 머신 + 스레딩 (529L)
│   ├── text_preprocessor.py   # 텍스트 전처리 (88L)
│   ├── clipboard.py           # 클립보드 읽기 (28L)
│   └── focus_monitor.py       # 활성 창 감지 (123L)
│
├── gui/                       # GUI 레이어 (CustomTkinter)
│   ├── __init__.py
│   ├── app.py                 # 메인 윈도우 — 레이아웃 + 모듈 조합 (236L)
│   ├── input_panel.py         # 입력 소스 (클립보드/직접입력) (180L)
│   ├── settings_panel.py      # 설정 탭 (타이밍/오타/고급) (394L)
│   ├── control_panel.py       # 컨트롤 (시작/정지/핫키/로그) (415L)
│   └── stats_dialog.py        # 통계 다이얼로그 + 미리보기 (359L)
│
├── presets/                   # 프리셋 JSON
│   ├── default.json
│   ├── fast_accurate.json
│   ├── slow_natural.json
│   ├── sloppy_beginner.json
│   └── custom/                # 사용자 커스텀 저장
│
├── config.json                # 앱 설정 (마지막 프리셋, AOT 등) — 자동 생성
├── requirements.txt
└── .vscode/settings.json
```

---

## 2. 모듈 책임 (단일 책임 원칙)

### core/ — 순수 로직 (GUI 의존 없음)

| 모듈 | 책임 | 핵심 API |
|------|------|----------|
| `keyboard_map` | QWERTY 물리 배열 매핑 | `get_adjacent_keys(char)`, `get_base_key(char)`, `is_shift_required(char)`, `SHIFT_CHARS`, `ADJACENT_KEYS` |
| `timing_model` | 글자별 딜레이 계산 (8-stage 파이프라인) | `TimingConfig` (dataclass), `TimingModel.calculate_delay(char, prev, idx, total) → (ms, breakdown)`, `.calculate_all(text)` |
| `typo_model` | 오타 발생 판정 + Action 시퀀스 생성 | `TypoConfig` (dataclass), `TypoModel.process_char(char, prev, next) → (actions, skip_next)`, `.process_text(text)`, `Action`, `ActionType` |
| `typer_engine` | 상태 머신 + 타이핑 실행 스레드 | `EngineConfig`, `EngineCallbacks`, `EngineState`, `TyperEngine.start(text)/.pause()/.resume()/.stop()` |
| `text_preprocessor` | 텍스트 정규화 | `PreprocessConfig`, `preprocess(text, config) → str` |
| `clipboard` | 시스템 클립보드 읽기 | `get_clipboard_text() → str` |
| `focus_monitor` | 활성 창 타이틀 감시 (Windows) | `FocusMonitor.capture()`, `.check(char_index) → bool` |

### gui/ — 프레젠테이션 레이어

| 모듈 | 책임 | 부모 위젯 |
|------|------|-----------|
| `app` | 메인 윈도우, 모듈 조합, 프리셋 연결 | `ctk.CTk` (루트) |
| `input_panel` | 클립보드 탭 + 직접 입력 탭 | `ctk.CTkFrame` |
| `settings_panel` | 타이밍/오타/고급 슬라이더·토글 | `ctk.CTkFrame` |
| `control_panel` | 시작/정지/핫키/로그/진행률 | `ctk.CTkFrame` |
| `stats_dialog` | 완료 통계 + 미리보기 시뮬레이션 | `ctk.CTkToplevel` |

### 루트

| 모듈 | 책임 |
|------|------|
| `main` | 앱 진입점. 테마 설정 + `App().mainloop()` |
| `preset_manager` | 프리셋 JSON 로드/저장/목록 + config.json R/W |

---

## 3. 의존 관계 (방향: 화살표 = "~를 import")

```
main.py
  └→ gui/app.py
       ├→ gui/input_panel.py
       │    └→ core/clipboard.py
       ├→ gui/settings_panel.py
       │    ├→ core/timing_model.py
       │    ├→ core/typo_model.py
       │    └→ core/text_preprocessor.py
       ├→ gui/control_panel.py
       │    ├→ core/typer_engine.py
       │    │    ├→ core/timing_model.py
       │    │    ├→ core/typo_model.py
       │    │    └→ core/keyboard_map.py
       │    ├→ core/focus_monitor.py
       │    └→ gui/stats_dialog.py
       │         ├→ core/timing_model.py
       │         └→ core/typo_model.py
       ├→ core/text_preprocessor.py
       └→ preset_manager.py
              ├→ core/timing_model.py
              ├→ core/typo_model.py
              └→ core/text_preprocessor.py

core 내부 의존:
  timing_model → keyboard_map (SHIFT_CHARS)
  typo_model   → keyboard_map (get_adjacent_keys)
  typer_engine → timing_model, typo_model, keyboard_map
```

**원칙**: `core/`는 `gui/`를 절대 import하지 않음. 단방향 의존.

---

## 4. 데이터 흐름 (타이핑 실행 시)

```
[사용자 텍스트 입력]
     │
     ▼
InputPanel ──"이 텍스트 사용"──→ App._on_text_selected()
     │                               │
     │                    preprocess(raw_text, PreprocessConfig)
     │                               │
     ▼                               ▼
App._target_text ←─────── 전처리된 텍스트 저장
     │
     │  F6 또는 ▶ 시작
     ▼
ControlPanel._on_start()
     │
     ├─ App._get_current_settings() 호출
     │    └→ SettingsPanel.get_timing_config() → TimingConfig
     │       SettingsPanel.get_typo_config()   → TypoConfig
     │       SettingsPanel.is_precise_mode()   → bool
     │
     ├─ EngineConfig 생성
     ├─ FocusMonitor 생성 (enabled 여부)
     ├─ EngineCallbacks 생성 (all via root.after → GUI thread)
     │
     ▼
TyperEngine.__init__(config, callbacks, focus_monitor)
TyperEngine.start(text)
     │
     ▼ (daemon thread)
TyperEngine._run(text)
     │
     ├─ 카운트다운 (N초)
     ├─ FocusMonitor.capture()
     │
     ╔═══ 메인 루프 (글자마다) ═══╗
     ║                              ║
     ║  pause_event.wait()          ║
     ║  stop_event 확인             ║
     ║  FocusMonitor.check(i)      ║
     ║       │                      ║
     ║       ▼                      ║
     ║  TimingModel.calculate_delay()║
     ║       │ → (delay_ms, breakdown)
     ║       ▼                      ║
     ║  TypoModel.process_char()    ║
     ║       │ → (actions, skip)    ║
     ║       ▼                      ║
     ║  time.sleep(delay)           ║
     ║       ▼                      ║
     ║  for action in actions:      ║
     ║    TYPE  → _simulate_key()   ║
     ║    BKSP  → _simulate_backspace()
     ║    PAUSE → time.sleep()      ║
     ║       ▼                      ║
     ║  callbacks.on_progress()     ║
     ║  callbacks.on_log()          ║
     ╚═════════════════════════════╝
     │
     ▼
callbacks.on_complete(stats)
     │
     ▼ (GUI thread via after())
ControlPanel._on_complete()
     ├→ 로그에 통계 출력
     └→ StatsDialog(stats, timing_data) 표시
```

---

## 5. 스레딩 모델

| 스레드 | 역할 | 생명 주기 |
|--------|------|-----------|
| **메인** (GUI) | tkinter mainloop, 모든 위젯 조작 | 앱 전체 |
| **타이핑** (daemon) | `TyperEngine._run()`, 실제 키 입력 | `start()` → `DONE`/`stop()` |
| **핫키 리스너** (daemon) | `pynput.keyboard.Listener`, F6/ESC 감지 | ControlPanel 생성 → destroy |

**GUI 안전**: 엔진 콜백은 모두 `root.after(0, fn)` 래핑 → 메인 스레드에서 실행.
**동기화**: `threading.Event` 2개 — `_pause_event` (일시정지), `_stop_event` (정지).

---

## 6. 상태 머신 (TyperEngine)

```
         start()           countdown done
IDLE ──────────→ COUNTDOWN ──────────→ TYPING
  ▲                  │                  │  ▲
  │            stop()/ESC          pause()│  │resume()/F6
  │                  │                  ▼  │
  │                  │               PAUSED
  │                  │                  │
  │            stop()/ESC          stop()/ESC
  │                  │                  │
  │                  ▼                  ▼
  └─────────────── IDLE ◄──────────── IDLE
                     ▲
                     │ (자연 완료)
                   DONE
```

---

## 7. Config / Dataclass 계층

```
EngineConfig
  ├── timing: TimingConfig       (16 fields)
  ├── typo: TypoConfig           (5 fields)
  ├── countdown_seconds: int
  ├── precise_mode: bool
  └── dry_run: bool

PreprocessConfig                  (6 fields, 별도)

프리셋 JSON 구조:
  {
    preset_name, preset_description,
    timing: { ...TimingConfig fields },
    typo: { ...TypoConfig fields },
    control: { precise_mode, countdown_seconds, focus_monitor_enabled },
    preprocessing: { ...PreprocessConfig fields }
  }
```

---

## 8. 콜백 / 이벤트 연결 맵

| 발신자 | 이벤트 | 수신자 | 용도 |
|--------|--------|--------|------|
| InputPanel | `on_text_selected(text)` | App | 대상 텍스트 설정 |
| SettingsPanel | `on_config_changed()` | App | 예상 시간 재계산 |
| App | `get_target_text()` | ControlPanel | 타이핑 시작 시 텍스트 가져오기 |
| App | `get_current_settings()` | ControlPanel | 엔진 설정 가져오기 |
| TyperEngine | `on_log(msg)` | ControlPanel | 실시간 로그 |
| TyperEngine | `on_state_change(state)` | ControlPanel | 상태 표시 업데이트 |
| TyperEngine | `on_progress(cur, total)` | ControlPanel | 진행률 바 |
| TyperEngine | `on_countdown(sec)` | ControlPanel | 카운트다운 표시 |
| TyperEngine | `on_complete(stats)` | ControlPanel | 통계 + StatsDialog |
| pynput.Listener | F6/ESC keypress | ControlPanel | 핫키 → 시작/일시정지/정지 |
| PresetManager | load()/save_custom() | App | 프리셋 JSON R/W |

---

## 9. 외부 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| customtkinter | latest | GUI 프레임워크 |
| pynput | latest | 키보드 이벤트 시뮬레이션 + 핫키 리스너 |
| pyperclip | latest | 클립보드 읽기 |
| matplotlib | latest | 딜레이 시각화 (StatsDialog, PreviewDialog) |

---

## 10. 파일별 수정 영향도

> "이 파일을 수정하면 어디가 영향 받는가?"

| 수정 대상 | 영향 범위 |
|-----------|-----------|
| `keyboard_map` | timing_model, typo_model, typer_engine |
| `timing_model` (TimingConfig 필드 변경) | typer_engine, settings_panel, preset_manager, stats_dialog, 모든 preset JSON |
| `typo_model` (TypoConfig 필드 변경) | typer_engine, settings_panel, preset_manager, stats_dialog, 모든 preset JSON |
| `typer_engine` (EngineConfig/Callbacks 변경) | control_panel |
| `settings_panel` (get_* 시그니처 변경) | app (get_current_settings), preset_manager |
| `control_panel` | app (생성자 인자) |
| `preset JSON` 구조 변경 | preset_manager, app._apply_preset |
| `app` | main (거의 없음) |
