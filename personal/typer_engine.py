"""
타이핑 엔진 — 타이밍 모델 + 오타 모델을 조합하여 실제 키 입력을 수행.

상태 머신: IDLE → COUNTDOWN → TYPING ⇄ PAUSED → DONE
스레딩: 타이핑은 별도 daemon 스레드에서 실행
입력 모드: 간편 모드 (type()) / 정교 모드 (press/release)
"""

import time
import random
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable

from core.timing_model import TimingModel, TimingConfig
from core.typo_model import TypoModel, TypoConfig, ActionType
from core.keyboard_map import SHIFT_CHARS, get_base_key, SHIFT_MAP

# pynput은 실제 키 입력 시에만 필요 (드라이런에서는 불필요)
# GUI 없는 환경(Linux 서버 등)에서 import 실패 방지를 위해 지연 로딩
_keyboard = None
_Key = None


def _ensure_pynput():
    """pynput을 필요할 때만 import. 실패 시 예외 발생."""
    global _keyboard, _Key
    if _keyboard is None:
        from pynput.keyboard import Controller, Key
        _keyboard = Controller()
        _Key = Key


# ============================================================
# 상태 정의
# ============================================================

class EngineState(Enum):
    IDLE = "IDLE"
    COUNTDOWN = "COUNTDOWN"
    TYPING = "TYPING"
    PAUSED = "PAUSED"
    DONE = "DONE"


# ============================================================
# 엔진 설정
# ============================================================

@dataclass
class EngineConfig:
    """타이핑 엔진의 설정. GUI 컨트롤과 1:1 대응."""
    timing: TimingConfig = field(default_factory=TimingConfig)
    typo: TypoConfig = field(default_factory=TypoConfig)
    countdown_seconds: int = 3
    precise_mode: bool = False   # True = 정교 모드, False = 간편 모드
    dry_run: bool = False


# ============================================================
# 콜백 인터페이스
# ============================================================

@dataclass
class EngineCallbacks:
    """엔진 → GUI 통신용 콜백."""
    on_progress: Callable[[int, int], None] | None = None        # (current, total)
    on_log: Callable[[str], None] | None = None                  # log message
    on_state_change: Callable[[EngineState], None] | None = None # state
    on_countdown: Callable[[int], None] | None = None            # seconds remaining
    on_complete: Callable[[dict], None] | None = None            # stats dict


# ============================================================
# 키 입력 시뮬레이션
# ============================================================


def _simulate_key_simple(char: str):
    """간편 모드: pynput type()으로 한 번에 입력."""
    _ensure_pynput()
    if char == '\n':
        _keyboard.press(_Key.enter)
        _keyboard.release(_Key.enter)
    elif char == '\t':
        _keyboard.press(_Key.tab)
        _keyboard.release(_Key.tab)
    elif char == ' ':
        _keyboard.press(_Key.space)
        _keyboard.release(_Key.space)
    else:
        _keyboard.type(char)


def _simulate_key_precise(char: str):
    """정교 모드: Shift 키를 명시적으로 press/release."""
    _ensure_pynput()
    if char == '\n':
        _keyboard.press(_Key.enter)
        _keyboard.release(_Key.enter)
    elif char == '\t':
        _keyboard.press(_Key.tab)
        _keyboard.release(_Key.tab)
    elif char == ' ':
        _keyboard.press(_Key.space)
        _keyboard.release(_Key.space)
    elif char in SHIFT_CHARS:
        base = get_base_key(char)
        _keyboard.press(_Key.shift)
        time.sleep(max(0.005, random.gauss(0.015, 0.005)))
        _keyboard.press(base)
        _keyboard.release(base)
        time.sleep(max(0.003, random.gauss(0.010, 0.003)))
        _keyboard.release(_Key.shift)
    else:
        _keyboard.press(char)
        _keyboard.release(char)


def _simulate_backspace(count: int = 1):
    """Backspace burst: 빠른 간격(30~50ms)으로 연타."""
    _ensure_pynput()
    for i in range(count):
        _keyboard.press(_Key.backspace)
        _keyboard.release(_Key.backspace)
        if i < count - 1:
            time.sleep(max(0.015, random.gauss(0.040, 0.008)))


# ============================================================
# 타이핑 엔진
# ============================================================

class TyperEngine:
    """메인 타이핑 엔진. 상태 머신 + 스레딩 기반."""

    def __init__(self, config: EngineConfig | None = None,
                 callbacks: EngineCallbacks | None = None):
        self.config = config or EngineConfig()
        self.callbacks = callbacks or EngineCallbacks()

        self._timing = TimingModel(self.config.timing)
        self._typo = TypoModel(self.config.typo)

        # 상태 관리
        self._state = EngineState.IDLE
        self._pause_event = threading.Event()
        self._pause_event.set()  # 초기: 일시정지 아님
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._resume_index = 0

        # 결과 데이터
        self.timing_data: list[tuple[str, float, dict]] = []  # (char, delay, breakdown)
        self.log_lines: list[str] = []

    @property
    def state(self) -> EngineState:
        return self._state

    def _set_state(self, new_state: EngineState):
        self._state = new_state
        if self.callbacks.on_state_change:
            self.callbacks.on_state_change(new_state)

    def _log(self, msg: str):
        self.log_lines.append(msg)
        if self.callbacks.on_log:
            self.callbacks.on_log(msg)

    def _emit_progress(self, current: int, total: int):
        if self.callbacks.on_progress:
            self.callbacks.on_progress(current, total)

    # ── 설정 업데이트 ──

    def update_config(self, config: EngineConfig):
        """설정을 업데이트 (IDLE 상태에서만 안전)."""
        self.config = config
        self._timing = TimingModel(config.timing)
        self._typo = TypoModel(config.typo)

    # ── 상태 제어 ──

    def start(self, text: str):
        """타이핑 시작. IDLE 상태에서만 호출 가능."""
        if self._state != EngineState.IDLE:
            return

        self._stop_event.clear()
        self._pause_event.set()
        self._resume_index = 0
        self.timing_data = []
        self.log_lines = []
        self._typo.reset_stats()
        self._timing.reset()

        self._thread = threading.Thread(
            target=self._run, args=(text,), daemon=True
        )
        self._thread.start()

    def pause(self):
        """Soft stop: 현재 글자 완료 후 일시정지."""
        if self._state == EngineState.TYPING:
            self._pause_event.clear()
            self._set_state(EngineState.PAUSED)
            self._log("[일시정지]")

    def resume(self):
        """일시정지에서 재개."""
        if self._state == EngineState.PAUSED:
            self._set_state(EngineState.TYPING)
            self._pause_event.set()
            self._log("[재개]")

    def stop(self):
        """Hard stop: 즉시 중단, IDLE로 복귀."""
        self._stop_event.set()
        self._pause_event.set()  # pause 대기 해제
        self._set_state(EngineState.IDLE)
        self._log("[정지]")

    def toggle_pause(self):
        """트리거 키 동작: 상태에 따라 시작/일시정지/재개."""
        if self._state == EngineState.TYPING:
            self.pause()
        elif self._state == EngineState.PAUSED:
            self.resume()

    # ── 메인 타이핑 루프 ──

    def _run(self, text: str):
        """타이핑 스레드의 메인 루프."""
        dry_run = self.config.dry_run
        precise = self.config.precise_mode

        # 카운트다운
        if not dry_run and self.config.countdown_seconds > 0:
            self._set_state(EngineState.COUNTDOWN)
            for remaining in range(self.config.countdown_seconds, 0, -1):
                if self._stop_event.is_set():
                    self._set_state(EngineState.IDLE)
                    return
                self._log(f"[카운트다운] {remaining}...")
                if self.callbacks.on_countdown:
                    self.callbacks.on_countdown(remaining)
                time.sleep(1)

        self._set_state(EngineState.TYPING)
        start_time = time.time()
        total = len(text)
        i = 0
        prev_char = None

        while i < total:
            # 일시정지 대기
            self._pause_event.wait()

            # 정지 확인
            if self._stop_event.is_set():
                return

            self._resume_index = i
            char = text[i]
            next_char = text[i + 1] if i < total - 1 else None

            # 딜레이 계산
            delay, breakdown = self._timing.calculate_delay(
                char, prev_char, i, total
            )

            # 오타 판정
            actions, skip_next = self._typo.process_char(char, prev_char, next_char)

            # 딜레이 대기 (첫 번째 Action 전에)
            if not dry_run:
                time.sleep(delay / 1000)

            # Action 시퀀스 실행
            elapsed = time.time() - start_time
            for action in actions:
                if self._stop_event.is_set():
                    return

                if action.action_type == ActionType.TYPE:
                    if not dry_run:
                        try:
                            if precise:
                                _simulate_key_precise(action.char)
                            else:
                                _simulate_key_simple(action.char)
                        except Exception:
                            _simulate_key_simple(action.char)

                    # 로그
                    label = action.label
                    bd_tag = _format_breakdown_tag(breakdown) if "정상" in label or "수정" in label else ""
                    self._log(
                        f"[{elapsed:07.3f}] '{_fmt(action.char)}' {label} "
                        f"({delay:.0f}ms) {bd_tag}"
                    )

                elif action.action_type == ActionType.BACKSPACE:
                    if not dry_run:
                        _simulate_backspace(action.count)
                    self._log(
                        f"[{elapsed:07.3f}] Backspace ×{action.count}"
                    )

                elif action.action_type == ActionType.PAUSE:
                    if not dry_run:
                        time.sleep(action.duration_ms / 1000)
                    self._log(
                        f"[{elapsed:07.3f}] {action.label} ({action.duration_ms:.0f}ms)"
                    )

            # 타이밍 데이터 기록
            self.timing_data.append((char, delay, breakdown))

            # 진행률
            self._emit_progress(i + 1, total)

            prev_char = char
            if skip_next:
                # 전치 오타: 다음 글자도 이미 처리됨
                if i + 1 < total:
                    next_delay, next_bd = self._timing.calculate_delay(
                        text[i + 1], char, i + 1, total
                    )
                    self.timing_data.append((text[i + 1], next_delay, next_bd))
                    prev_char = text[i + 1]
                i += 2
            else:
                i += 1

        # 완료
        total_time = time.time() - start_time
        self._set_state(EngineState.DONE)
        stats = self._build_stats(total_time, total)
        self._log(f"[완료] {total_time:.2f}초, {total}자")
        if self.callbacks.on_complete:
            self.callbacks.on_complete(stats)

    def _build_stats(self, total_time: float, total_chars: int) -> dict:
        """통계 데이터 생성."""
        delays = [d for _, d, _ in self.timing_data]
        avg_delay = sum(delays) / len(delays) if delays else 0
        cpm = (total_chars / total_time * 60) if total_time > 0 else 0
        wpm = cpm / 5

        return {
            "total_time_sec": round(total_time, 2),
            "total_chars": total_chars,
            "avg_cpm": round(cpm, 1),
            "avg_wpm": round(wpm, 1),
            "avg_delay_ms": round(avg_delay, 1),
            "min_delay_ms": round(min(delays), 1) if delays else 0,
            "max_delay_ms": round(max(delays), 1) if delays else 0,
            "typo_stats": dict(self._typo.stats),
        }


# ============================================================
# 포맷 유틸
# ============================================================

def _fmt(c: str) -> str:
    if c == ' ':   return '␣'
    if c == '\n':  return '↵'
    if c == '\t':  return '⇥'
    return c


def _format_breakdown_tag(bd: dict) -> str:
    parts = []
    for key, val in bd.items():
        if key == 'final':
            continue
        if key.endswith('_factor') or key.endswith('_multiplier'):
            parts.append(f"{key}:×{val}")
        elif key == 'base':
            parts.append(f"base:{val}")
        else:
            parts.append(f"{key}:+{val}")
    return f"[{' '.join(parts)}]" if parts else ""


# ============================================================
# CLI 테스트
# ============================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("타이핑 엔진 CLI 테스트")
    print("=" * 60)

    # 테스트 텍스트
    test_text = "Hello, world! This is a test."

    # 모드 선택
    print("\n모드를 선택하세요:")
    print("  1) 드라이 런 (실제 키 입력 없음, 즉시 완료)")
    print("  2) 실제 타이핑 (메모장을 열고 3초 카운트다운 후 입력)")
    print("  3) 클립보드 텍스트로 실제 타이핑")

    try:
        choice = input("\n선택 (1/2/3): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    if choice == "3":
        from core.clipboard import get_clipboard_text
        clip = get_clipboard_text()
        if clip:
            test_text = clip
            print(f"\n클립보드 텍스트 ({len(test_text)}자): {test_text[:80]}...")
        else:
            print("클립보드가 비어있습니다. 기본 텍스트를 사용합니다.")

    # 전처리
    from core.text_preprocessor import preprocess, PreprocessConfig
    test_text = preprocess(test_text, PreprocessConfig())

    print(f"\n타이핑할 텍스트 ({len(test_text)}자): {repr(test_text[:80])}")

    # 설정
    is_dry = (choice == "1")
    config = EngineConfig(
        timing=TimingConfig(
            base_delay_ms=70,
            delay_variance_ms=30,
            word_boundary_enabled=True,
            punctuation_pause_enabled=True,
            newline_pause_enabled=True,
            shift_penalty_enabled=True,
            double_letter_enabled=True,
            burst_enabled=False,
            fatigue_enabled=True,
        ),
        typo=TypoConfig(
            typo_prob=200,           # 2% (테스트용으로 약간 높게)
            typo_revision_prob=85,
            adjacent_key_enabled=True,
            transposition_enabled=False,  # 실제 테스트에선 인접 키만
            double_strike_enabled=False,
        ),
        countdown_seconds=3 if not is_dry else 0,
        precise_mode=False,
        dry_run=is_dry,
    )

    # 콜백
    def on_log(msg):
        print(msg)

    def on_state(state):
        print(f"  [상태 변경] → {state.value}")

    def on_progress(current, total):
        pct = current / total * 100
        bar = '█' * int(pct // 5) + '░' * (20 - int(pct // 5))
        print(f"\r  [{bar}] {pct:.0f}% ({current}/{total})", end="", flush=True)

    def on_complete(stats):
        print(f"\n\n{'=' * 60}")
        print("타이핑 완료 — 통계")
        print(f"{'=' * 60}")
        print(f"  총 소요 시간: {stats['total_time_sec']}초")
        print(f"  총 글자 수:   {stats['total_chars']}")
        print(f"  평균 속도:    {stats['avg_cpm']} CPM ({stats['avg_wpm']} WPM)")
        print(f"  평균 딜레이:  {stats['avg_delay_ms']}ms")
        print(f"  최소/최대:    {stats['min_delay_ms']}ms / {stats['max_delay_ms']}ms")
        ts = stats['typo_stats']
        print(f"  오타:         {ts['typos']}회 (수정 {ts['revised']}, 미수정 {ts['unrevised']})")

    def on_countdown(sec):
        pass  # on_log에서 이미 출력됨

    callbacks = EngineCallbacks(
        on_log=on_log,
        on_state_change=on_state,
        on_progress=on_progress,
        on_complete=on_complete,
        on_countdown=on_countdown,
    )

    # 실행
    engine = TyperEngine(config, callbacks)

    if not is_dry:
        print(f"\n⚠️  {config.countdown_seconds}초 후 타이핑이 시작됩니다!")
        print("   지금 메모장(또는 입력할 창)을 클릭하세요.")
        print("   ESC를 누르면 이 터미널에서 Ctrl+C로 중단할 수 있습니다.\n")

    engine.start(test_text)

    # 스레드 완료 대기
    if engine._thread:
        engine._thread.join()

    print("\n테스트 종료.")
