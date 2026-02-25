"""
컨트롤 패널 — 시작/정지/드라이런/테스트, 핫키, 상태, 진행률, 로그.

버튼 의미 정리:
- ▶ 시작: 실제 OS 키 입력 타이핑
- 🧪 드라이 런: 키 입력 없이 통계만 시뮬레이션
- 🧪 테스트: 앱 내부 패널에서 실제 타이핑 동작 확인
- 📊 통계: 완료 후 자동 팝업 (StatsDialog)
"""

import customtkinter as ctk
from typing import Callable

from pynput import keyboard as kb

from core.typer_engine import (
    TyperEngine, EngineConfig, EngineCallbacks, EngineState,
    TimingConfig, TypoConfig,
)
from core.focus_monitor import FocusMonitor
from gui.stats_dialog import StatsDialog
from gui.test_panel import TestPanel


STATE_COLORS: dict[EngineState, tuple[str, str]] = {
    EngineState.IDLE:      ("#888888", "대기중"),
    EngineState.COUNTDOWN: ("#FFD700", "카운트다운..."),
    EngineState.TYPING:    ("#00CC66", "타이핑 중"),
    EngineState.PAUSED:    ("#FF8C00", "일시정지"),
    EngineState.DONE:      ("#4499FF", "완료"),
}

FKEY_MAP = {f"F{i}": getattr(kb.Key, f"f{i}") for i in range(1, 13)}


class ControlPanel(ctk.CTkFrame):
    """컨트롤 패널."""

    def __init__(self, master, get_target_text: Callable[[], str],
                 get_settings: Callable[[], tuple] | None = None,
                 on_auto_clip_start: Callable[[], str] | None = None,
                 **kwargs):
        super().__init__(master, **kwargs)

        self._get_target_text = get_target_text
        self._get_settings = get_settings
        self._on_auto_clip_start = on_auto_clip_start
        self._app = master

        self._engine: TyperEngine | None = None
        self._focus_monitor: FocusMonitor | None = None
        self._trigger_key_name = "F6"
        self._trigger_key = FKEY_MAP["F6"]

        self._hotkey_listener: kb.Listener | None = None
        self._last_stats: dict | None = None
        self._last_timing_data: list = []

        self._build_ui()
        self._start_hotkey_listener()

    def _build_ui(self):
        ctk.CTkLabel(self, text="🎮 컨트롤",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      anchor="w").pack(fill="x", padx=10, pady=(8, 4))

        # ── Row 1: 트리거 + 카운트다운 + 포커스 ──
        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(row1, text="트리거:", font=ctk.CTkFont(size=11)).pack(side="left")
        self._trigger_dd = ctk.CTkOptionMenu(
            row1, values=[f"F{i}" for i in range(1, 13)],
            width=70, height=26, font=ctk.CTkFont(size=11),
            command=self._on_trigger_change,
        )
        self._trigger_dd.set("F6")
        self._trigger_dd.pack(side="left", padx=(4, 8))

        ctk.CTkLabel(row1, text="ESC=정지", font=ctk.CTkFont(size=10),
                      text_color="gray").pack(side="left", padx=(0, 8))

        ctk.CTkLabel(row1, text="카운트다운:", font=ctk.CTkFont(size=11)).pack(side="left")
        self._cd_var = ctk.IntVar(value=3)
        self._cd_spin = ctk.CTkOptionMenu(
            row1, values=[str(i) for i in range(0, 11)],
            width=50, height=26, font=ctk.CTkFont(size=11),
            command=lambda v: self._cd_var.set(int(v)),
        )
        self._cd_spin.set("3")
        self._cd_spin.pack(side="left", padx=4)
        ctk.CTkLabel(row1, text="초", font=ctk.CTkFont(size=11)).pack(side="left")

        self._focus_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(row1, text="🔍 포커스 감시", variable=self._focus_var,
                          font=ctk.CTkFont(size=11)).pack(side="right", padx=(8, 0))

        self._auto_clip_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(row1, text="📋 자동 클립보드", variable=self._auto_clip_var,
                          font=ctk.CTkFont(size=11)).pack(side="right", padx=(8, 0))

        # ── Row 2: 버튼 ──
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(4, 2))

        self._btn_start = ctk.CTkButton(
            row2, text="▶ 시작", width=80, height=30,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2B7A3E", hover_color="#236B33",
            command=self._on_start,
        )
        self._btn_start.pack(side="left", padx=(0, 3))

        self._btn_pause = ctk.CTkButton(
            row2, text="⏸ 일시정지", width=90, height=30,
            font=ctk.CTkFont(size=11), state="disabled",
            command=self._on_pause,
        )
        self._btn_pause.pack(side="left", padx=3)

        self._btn_stop = ctk.CTkButton(
            row2, text="⏹ 정지", width=70, height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#AA3333", hover_color="#882222", state="disabled",
            command=self._on_stop,
        )
        self._btn_stop.pack(side="left", padx=3)

        self._btn_dryrun = ctk.CTkButton(
            row2, text="🧪 드라이런", width=90, height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#555555", hover_color="#444444",
            command=self._on_dryrun,
        )
        self._btn_dryrun.pack(side="left", padx=3)

        self._btn_test = ctk.CTkButton(
            row2, text="🧪 테스트", width=80, height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#1A5276", hover_color="#154360",
            command=self._on_test,
        )
        self._btn_test.pack(side="left", padx=3)

        self._btn_stats = ctk.CTkButton(
            row2, text="📊 통계", width=70, height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#6C3483", hover_color="#5B2C6F",
            state="disabled",
            command=self._on_show_stats,
        )
        self._btn_stats.pack(side="left", padx=3)

        # ── Row 3: 상태 + 진행률 ──
        row3 = ctk.CTkFrame(self, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=2)

        self._status_dot = ctk.CTkLabel(row3, text="●", font=ctk.CTkFont(size=14),
                                         text_color="#888888", width=16)
        self._status_dot.pack(side="left")
        self._status_text = ctk.CTkLabel(row3, text="대기중", font=ctk.CTkFont(size=11),
                                          anchor="w")
        self._status_text.pack(side="left", padx=(4, 8))

        self._progress_bar = ctk.CTkProgressBar(row3, height=14)
        self._progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._progress_bar.set(0)

        self._progress_label = ctk.CTkLabel(row3, text="0%", width=70,
                                             font=ctk.CTkFont(size=10), anchor="e")
        self._progress_label.pack(side="right")

        # ── 로그 ──
        log_hdr = ctk.CTkFrame(self, fg_color="transparent")
        log_hdr.pack(fill="x", padx=10, pady=(4, 0))
        ctk.CTkLabel(log_hdr, text="📜 로그", font=ctk.CTkFont(size=12),
                      anchor="w").pack(side="left")
        ctk.CTkButton(log_hdr, text="지우기", width=50, height=22,
                       font=ctk.CTkFont(size=10), fg_color="transparent",
                       hover_color="#444", border_width=1,
                       command=self._clear_log).pack(side="right")

        self._log_box = ctk.CTkTextbox(
            self, height=200,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled", wrap="word",
        )
        self._log_box.pack(fill="both", expand=True, padx=10, pady=(2, 8))

    # ── get/set (프리셋 연동) ──

    def get_countdown(self) -> int:
        return self._cd_var.get()

    def set_countdown(self, val: int):
        self._cd_var.set(val)
        self._cd_spin.set(str(val))

    def get_focus_monitor(self) -> bool:
        return self._focus_var.get()

    def set_focus_monitor(self, val: bool):
        self._focus_var.set(val)

    def get_auto_clipboard(self) -> bool:
        return self._auto_clip_var.get()

    def set_auto_clipboard(self, val: bool):
        self._auto_clip_var.set(val)

    # ── 핫키 ──

    def _on_trigger_change(self, v):
        self._trigger_key_name = v
        self._trigger_key = FKEY_MAP[v]

    def _start_hotkey_listener(self):
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
        if self._engine is None or self._engine.state in (EngineState.IDLE, EngineState.DONE):
            self._on_start()
        elif self._engine.state == EngineState.TYPING:
            self._on_pause()
        elif self._engine.state == EngineState.PAUSED:
            self._on_resume()

    def _on_hard_stop(self):
        if self._engine and self._engine.state in (
            EngineState.TYPING, EngineState.PAUSED, EngineState.COUNTDOWN
        ):
            self._on_stop()

    # ── 설정 읽기 헬퍼 ──

    def _read_settings(self):
        """get_settings 콜백에서 설정 읽기. 4-tuple or 3-tuple 지원."""
        focus = self._focus_var.get()
        if self._get_settings:
            r = self._get_settings()
            if len(r) == 4:
                return r[0], r[1], r[2], r[3]
            return r[0], r[1], r[2], focus
        return TimingConfig(), TypoConfig(), False, focus

    # ── 자동 클립보드 헬퍼 ──

    def _resolve_target_text(self) -> str:
        """
        대상 텍스트를 결정.
        자동 클립보드가 ON이면 콜백을 통해 클립보드에서 즉시 읽어서 반환.
        OFF이면 기존 방식 (미리 설정된 _target_text).
        """
        if self._auto_clip_var.get() and self._on_auto_clip_start:
            text = self._on_auto_clip_start()
            if text:
                return text
        return self._get_target_text()

    # ── 버튼 핸들러 ──

    def _on_start(self, dry_run=False):
        text = self._resolve_target_text()
        if not text:
            self._log("[경고] 대상 텍스트 없음. '이 텍스트 사용'을 먼저 클릭하거나 '자동 클립보드'를 활성화하세요.")
            return

        timing_cfg, typo_cfg, precise, focus_en = self._read_settings()

        config = EngineConfig(
            timing=timing_cfg, typo=typo_cfg,
            countdown_seconds=self._cd_var.get(),
            precise_mode=precise, dry_run=dry_run,
        )

        self._focus_monitor = FocusMonitor(
            enabled=focus_en and not dry_run, check_interval=10,
        )

        callbacks = EngineCallbacks(
            on_log=lambda m: self._app.after(0, self._log, m),
            on_state_change=lambda s: self._app.after(0, self._update_state, s),
            on_progress=lambda c, t: self._app.after(0, self._update_progress, c, t),
            on_countdown=lambda s: self._app.after(0, self._update_countdown, s),
            on_complete=lambda st: self._app.after(0, self._on_complete, st),
        )

        self._engine = TyperEngine(config, callbacks, self._focus_monitor)
        self._progress_bar.set(0)
        self._progress_label.configure(text="0%")

        mode = "드라이런" if dry_run else "실제 타이핑"
        src = "(자동 클립보드)" if self._auto_clip_var.get() else ""
        self._log(f"[시작] {mode} {src} — {len(text)}자 "
                  f"(딜레이:{timing_cfg.base_delay_ms}ms 오타:{typo_cfg.typo_prob/100:.2f}%)")
        self._engine.start(text)

    def _on_dryrun(self):
        self._on_start(dry_run=True)

    def _on_test(self):
        """테스트 패널 열기 — 앱 내부에서 타이핑 결과 확인."""
        timing_cfg, typo_cfg, _, _ = self._read_settings()
        TestPanel(self._app, timing_cfg, typo_cfg)

    def _on_show_stats(self):
        """마지막 실행 통계를 다이얼로그로 표시."""
        if self._last_stats:
            try:
                StatsDialog(self._app, self._last_stats, self._last_timing_data)
            except Exception as e:
                self._log(f"[통계 창 오류] {e}")

    def _on_pause(self):
        if self._engine:
            self._engine.pause()

    def _on_resume(self):
        if self._engine:
            self._engine.resume()

    def _on_stop(self):
        if self._engine:
            self._engine.stop()
            self._log("[정지] Hard stop")

    # ── GUI 업데이트 ──

    def _update_state(self, state: EngineState):
        color, text = STATE_COLORS.get(state, ("#888", "?"))
        self._status_dot.configure(text_color=color)
        self._status_text.configure(text=text)

        idle = state in (EngineState.IDLE, EngineState.DONE)
        typing = state == EngineState.TYPING
        paused = state == EngineState.PAUSED
        running = state in (EngineState.TYPING, EngineState.PAUSED, EngineState.COUNTDOWN)

        self._btn_start.configure(state="normal" if idle else "disabled")
        self._btn_dryrun.configure(state="normal" if idle else "disabled")
        self._btn_test.configure(state="normal" if idle else "disabled")

        if paused:
            self._btn_pause.configure(state="normal", text="▶ 재개", command=self._on_resume)
        elif typing:
            self._btn_pause.configure(state="normal", text="⏸ 일시정지", command=self._on_pause)
        else:
            self._btn_pause.configure(state="disabled", text="⏸ 일시정지", command=self._on_pause)

        self._btn_stop.configure(state="normal" if running else "disabled")
        dd_st = "normal" if idle else "disabled"
        self._trigger_dd.configure(state=dd_st)
        self._cd_spin.configure(state=dd_st)

    def _update_progress(self, cur, total):
        if total > 0:
            p = cur / total
            self._progress_bar.set(p)
            self._progress_label.configure(text=f"{p*100:.0f}% ({cur}/{total})")

    def _update_countdown(self, sec):
        self._status_text.configure(text=f"카운트다운 {sec}...")

    def _on_complete(self, stats):
        self._log(f"{'='*40}")
        self._log(f"소요: {stats['total_time_sec']}초  │  "
                  f"속도: {stats['avg_cpm']} CPM ({stats['avg_wpm']} WPM)")
        ts = stats.get('typo_stats', {})
        self._log(f"오타: {ts.get('typos',0)}회  "
                  f"(수정 {ts.get('revised',0)} / 미수정 {ts.get('unrevised',0)})")
        self._log(f"{'='*40}")

        # 통계 데이터 저장 (📊 버튼으로 열기 위해)
        self._last_stats = stats
        self._last_timing_data = self._engine.timing_data if self._engine else []
        self._btn_stats.configure(state="normal")

    # ── 로그 ──

    def _log(self, msg):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def destroy(self):
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        if self._engine:
            self._engine.stop()
        super().destroy()
