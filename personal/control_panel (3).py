"""
컨트롤 패널 — 트리거 키 설정, 시작/정지/일시정지/드라이런 버튼,
상태 표시, 진행률 바, 실시간 로그.

핫키 리스너(pynput)를 별도 데몬 스레드로 운영.
엔진 콜백을 GUI 메인 스레드로 위임(root.after).
"""

import threading
import customtkinter as ctk
from typing import Callable

from pynput import keyboard as kb

from core.typer_engine import (
    TyperEngine, EngineConfig, EngineCallbacks, EngineState,
    TimingConfig, TypoConfig,
)
from core.focus_monitor import FocusMonitor


# ============================================================
# 상태 색상 매핑
# ============================================================

STATE_COLORS: dict[EngineState, tuple[str, str]] = {
    # (원(●) 색상, 텍스트)
    EngineState.IDLE:      ("#888888", "대기중"),
    EngineState.COUNTDOWN: ("#FFD700", "카운트다운..."),
    EngineState.TYPING:    ("#00CC66", "타이핑 중"),
    EngineState.PAUSED:    ("#FF8C00", "일시정지"),
    EngineState.DONE:      ("#4499FF", "완료"),
}

# F1~F12 키 매핑
FKEY_MAP: dict[str, kb.Key] = {
    f"F{i}": getattr(kb.Key, f"f{i}") for i in range(1, 13)
}


class ControlPanel(ctk.CTkFrame):
    """컨트롤 패널. 엔진 제어 + 상태 모니터링 + 실시간 로그."""

    def __init__(self, master, get_target_text: Callable[[], str],
                 get_settings: Callable[[], tuple] | None = None, **kwargs):
        super().__init__(master, **kwargs)

        self._get_target_text = get_target_text
        self._get_settings = get_settings  # () -> (TimingConfig, TypoConfig, precise_mode)
        self._app = master  # after() 호출용

        # 엔진
        self._engine: TyperEngine | None = None
        self._trigger_key_name = "F6"
        self._trigger_key = FKEY_MAP["F6"]
        self._countdown_seconds = 3

        # 핫키 리스너
        self._hotkey_listener: kb.Listener | None = None

        self._build_ui()
        self._start_hotkey_listener()

    def _build_ui(self):
        # 섹션 라벨
        ctk.CTkLabel(
            self, text="🎮 컨트롤",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        # ── 트리거 키 + 카운트다운 행 ──
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row1, text="트리거 키:", font=ctk.CTkFont(size=12)).pack(side="left")

        self._trigger_dropdown = ctk.CTkOptionMenu(
            row1, values=[f"F{i}" for i in range(1, 13)],
            width=80, height=28,
            font=ctk.CTkFont(size=11),
            command=self._on_trigger_change,
        )
        self._trigger_dropdown.set("F6")
        self._trigger_dropdown.pack(side="left", padx=(4, 12))

        ctk.CTkLabel(row1, text="긴급 정지: ESC", font=ctk.CTkFont(size=11),
                      text_color="gray").pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row1, text="카운트다운:", font=ctk.CTkFont(size=12)).pack(side="left")

        self._countdown_var = ctk.IntVar(value=3)
        self._countdown_spin = ctk.CTkOptionMenu(
            row1, values=[str(i) for i in range(0, 11)],
            width=60, height=28,
            font=ctk.CTkFont(size=11),
            command=lambda v: self._countdown_var.set(int(v)),
        )
        self._countdown_spin.set("3")
        self._countdown_spin.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="초", font=ctk.CTkFont(size=12)).pack(side="left")

        # 포커스 모니터 토글
        self._focus_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            row1, text="🔍 포커스 감시",
            variable=self._focus_var,
            font=ctk.CTkFont(size=11),
            width=30,
        ).pack(side="right", padx=(4, 0))

        # ── 버튼 행 ──
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(4, 2))

        self._btn_start = ctk.CTkButton(
            row2, text="▶ 시작", width=90, height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2B7A3E", hover_color="#236B33",
            command=self._on_start,
        )
        self._btn_start.pack(side="left", padx=(0, 4))

        self._btn_pause = ctk.CTkButton(
            row2, text="⏸ 일시정지", width=100, height=32,
            font=ctk.CTkFont(size=12),
            state="disabled",
            command=self._on_pause,
        )
        self._btn_pause.pack(side="left", padx=4)

        self._btn_stop = ctk.CTkButton(
            row2, text="⏹ 정지", width=80, height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#AA3333", hover_color="#882222",
            state="disabled",
            command=self._on_stop,
        )
        self._btn_stop.pack(side="left", padx=4)

        self._btn_dryrun = ctk.CTkButton(
            row2, text="🧪 드라이 런", width=100, height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#555555", hover_color="#444444",
            command=self._on_dryrun,
        )
        self._btn_dryrun.pack(side="left", padx=4)

        # ── 상태 표시 행 ──
        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=2)

        self._status_dot = ctk.CTkLabel(
            row3, text="●", font=ctk.CTkFont(size=16),
            text_color="#888888", width=20,
        )
        self._status_dot.pack(side="left")

        self._status_text = ctk.CTkLabel(
            row3, text="대기중",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self._status_text.pack(side="left", padx=(4, 12))

        self._target_preview = ctk.CTkLabel(
            row3, text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self._target_preview.pack(side="left", fill="x", expand=True)

        # ── 진행률 바 ──
        row4 = ctk.CTkFrame(self, fg_color="transparent")
        row4.pack(fill="x", padx=10, pady=2)

        self._progress_bar = ctk.CTkProgressBar(row4, height=16)
        self._progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._progress_bar.set(0)

        self._progress_label = ctk.CTkLabel(
            row4, text="0%", width=80,
            font=ctk.CTkFont(size=11),
            anchor="e",
        )
        self._progress_label.pack(side="right")

        # ── 실시간 로그 ──
        log_header = ctk.CTkFrame(self, fg_color="transparent")
        log_header.pack(fill="x", padx=10, pady=(4, 0))

        ctk.CTkLabel(
            log_header, text="📜 실시간 로그",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left")

        ctk.CTkButton(
            log_header, text="지우기", width=60, height=24,
            font=ctk.CTkFont(size=10),
            fg_color="transparent", hover_color="#444444",
            border_width=1,
            command=self._clear_log,
        ).pack(side="right")

        self._log_textbox = ctk.CTkTextbox(
            self, height=150,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
            wrap="word",
        )
        self._log_textbox.pack(fill="both", expand=True, padx=10, pady=(2, 8))

    # ── 트리거 키 변경 ──

    def _on_trigger_change(self, value: str):
        self._trigger_key_name = value
        self._trigger_key = FKEY_MAP[value]

    # ── 핫키 리스너 ──

    def _start_hotkey_listener(self):
        """핫키 리스너를 데몬 스레드로 시작."""
        def on_press(key):
            try:
                if key == kb.Key.esc:
                    self._app.after(0, self._on_hard_stop)
                elif key == self._trigger_key:
                    self._app.after(0, self._on_trigger_pressed)
            except Exception:
                pass

        self._hotkey_listener = kb.Listener(on_press=on_press)
        self._hotkey_listener.daemon = True
        self._hotkey_listener.start()

    def _on_trigger_pressed(self):
        """트리거 키가 눌렸을 때: 상태에 따라 시작/일시정지/재개."""
        if self._engine is None or self._engine.state == EngineState.IDLE:
            self._on_start()
        elif self._engine.state == EngineState.TYPING:
            self._on_pause()
        elif self._engine.state == EngineState.PAUSED:
            self._on_resume()
        elif self._engine.state == EngineState.DONE:
            self._on_start()

    def _on_hard_stop(self):
        """ESC: 즉시 정지."""
        if self._engine and self._engine.state in (
            EngineState.TYPING, EngineState.PAUSED, EngineState.COUNTDOWN
        ):
            self._on_stop()

    # ── 버튼 핸들러 ──

    def _on_start(self, dry_run: bool = False):
        """시작 버튼: 엔진 생성 + 타이핑 시작."""
        text = self._get_target_text()
        if not text:
            self._append_log("[경고] 대상 텍스트가 없습니다. 먼저 '이 텍스트 사용'을 클릭하세요.")
            return

        # 설정 패널에서 값 읽기 (없으면 기본값)
        if self._get_settings:
            timing_cfg, typo_cfg, precise = self._get_settings()
        else:
            timing_cfg = TimingConfig()
            typo_cfg = TypoConfig()
            precise = False

        config = EngineConfig(
            timing=timing_cfg,
            typo=typo_cfg,
            countdown_seconds=self._countdown_var.get(),
            precise_mode=precise,
            dry_run=dry_run,
            focus_monitor_enabled=self._focus_var.get(),
        )

        # 콜백 (GUI 메인 스레드에서 실행되도록 after 사용)
        callbacks = EngineCallbacks(
            on_log=lambda msg: self._app.after(0, self._append_log, msg),
            on_state_change=lambda s: self._app.after(0, self._update_state, s),
            on_progress=lambda c, t: self._app.after(0, self._update_progress, c, t),
            on_countdown=lambda s: self._app.after(0, self._update_countdown, s),
            on_complete=lambda st: self._app.after(0, self._on_complete, st),
        )

        self._engine = TyperEngine(config, callbacks)
        self._progress_bar.set(0)
        self._progress_label.configure(text="0%")

        preview = text[:40].replace('\n', '↵')
        suffix = "..." if len(text) > 40 else ""
        self._target_preview.configure(text=f"\"{preview}{suffix}\" ({len(text)}자)")

        mode_label = "드라이 런" if dry_run else "실제 타이핑"
        self._append_log(f"[시작] {mode_label} — {len(text)}자")

        self._engine.start(text)

    def _on_dryrun(self):
        """드라이 런 버튼."""
        self._on_start(dry_run=True)

    def _on_pause(self):
        """일시정지 버튼 / Soft stop."""
        if self._engine:
            self._engine.pause()

    def _on_resume(self):
        """재개."""
        if self._engine:
            self._engine.resume()

    def _on_stop(self):
        """정지 버튼 / Hard stop (ESC)."""
        if self._engine:
            self._engine.stop()
            self._append_log("[정지] Hard stop")

    # ── GUI 업데이트 (콜백에서 호출) ──

    def _update_state(self, state: EngineState):
        """상태 변경 시 UI 업데이트."""
        color, text = STATE_COLORS.get(state, ("#888888", "알 수 없음"))
        self._status_dot.configure(text_color=color)
        self._status_text.configure(text=text)

        # 버튼 상태 업데이트
        is_idle = state in (EngineState.IDLE, EngineState.DONE)
        is_typing = state == EngineState.TYPING
        is_paused = state == EngineState.PAUSED
        is_running = state in (EngineState.TYPING, EngineState.PAUSED, EngineState.COUNTDOWN)

        self._btn_start.configure(state="normal" if is_idle else "disabled")
        self._btn_dryrun.configure(state="normal" if is_idle else "disabled")
        self._btn_pause.configure(
            state="normal" if is_typing else "disabled",
            text="▶ 재개" if is_paused else "⏸ 일시정지",
        )
        if is_paused:
            self._btn_pause.configure(state="normal")
            self._btn_pause.configure(command=self._on_resume)
        else:
            self._btn_pause.configure(command=self._on_pause)

        self._btn_stop.configure(state="normal" if is_running else "disabled")

        # 드롭다운/설정 잠금
        dropdown_state = "normal" if is_idle else "disabled"
        self._trigger_dropdown.configure(state=dropdown_state)
        self._countdown_spin.configure(state=dropdown_state)

    def _update_progress(self, current: int, total: int):
        """진행률 업데이트."""
        if total > 0:
            pct = current / total
            self._progress_bar.set(pct)
            self._progress_label.configure(text=f"{pct * 100:.0f}% ({current}/{total})")

    def _update_countdown(self, seconds: int):
        """카운트다운 표시."""
        self._status_text.configure(text=f"카운트다운 {seconds}...")

    def _on_complete(self, stats: dict):
        """타이핑 완료 시 통계 표시."""
        self._append_log(f"{'=' * 40}")
        self._append_log(f"총 소요 시간: {stats['total_time_sec']}초")
        self._append_log(f"평균 속도: {stats['avg_cpm']} CPM ({stats['avg_wpm']} WPM)")
        self._append_log(f"평균 딜레이: {stats['avg_delay_ms']}ms "
                         f"(최소 {stats['min_delay_ms']} / 최대 {stats['max_delay_ms']})")
        ts = stats.get('typo_stats', {})
        self._append_log(f"오타: {ts.get('typos', 0)}회 "
                         f"(수정 {ts.get('revised', 0)}, 미수정 {ts.get('unrevised', 0)})")
        self._append_log(f"{'=' * 40}")

    # ── 로그 ──

    def _append_log(self, msg: str):
        """로그 텍스트박스에 한 줄 추가 + 자동 스크롤."""
        self._log_textbox.configure(state="normal")
        self._log_textbox.insert("end", msg + "\n")
        self._log_textbox.see("end")
        self._log_textbox.configure(state="disabled")

    def _clear_log(self):
        """로그 초기화."""
        self._log_textbox.configure(state="normal")
        self._log_textbox.delete("1.0", "end")
        self._log_textbox.configure(state="disabled")

    # ── 외부 인터페이스 (프리셋 연동) ──

    def get_countdown(self) -> int:
        return self._countdown_var.get()

    def set_countdown(self, seconds: int):
        self._countdown_var.set(seconds)
        self._countdown_spin.set(str(seconds))

    def get_focus_monitor(self) -> bool:
        return self._focus_var.get()

    def set_focus_monitor(self, enabled: bool):
        self._focus_var.set(enabled)

    # ── 정리 ──

    def destroy(self):
        """패널 파괴 시 리스너 정리."""
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        if self._engine:
            self._engine.stop()
        super().destroy()
