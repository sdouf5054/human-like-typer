"""
설정 패널 — 타이밍 설정 탭 + 오타 설정 탭.

모든 슬라이더/토글은 실시간으로 TimingConfig / TypoConfig 객체를 생성하여
컨트롤 패널(엔진)에 전달할 수 있도록 get_timing_config() / get_typo_config() 제공.
"""

import customtkinter as ctk
from typing import Callable

from core.timing_model import TimingConfig
from core.typo_model import TypoConfig


class SettingsPanel(ctk.CTkFrame):
    """설정 패널. 탭뷰로 타이밍/오타 전환."""

    def __init__(self, master, on_settings_changed: Callable[[], None] | None = None,
                 **kwargs):
        super().__init__(master, **kwargs)
        self._on_settings_changed = on_settings_changed

        # 내부 변수 (슬라이더/토글 값 저장)
        self._vars: dict[str, ctk.Variable] = {}

        self._build_ui()

    # ============================================================
    # UI 빌드
    # ============================================================

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="⚙️ 설정",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        self._tabview = ctk.CTkTabview(self, height=280)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._tabview.add("타이밍")
        self._tabview.add("오타")

        self._build_timing_tab(self._tabview.tab("타이밍"))
        self._build_typo_tab(self._tabview.tab("오타"))

    # ── 타이밍 탭 ──

    def _build_timing_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True)

        # 기본 딜레이
        self._add_slider(scroll, "base_delay_ms", "Base Delay (ms)",
                         20, 500, 70, step=5)
        self._add_slider(scroll, "delay_variance_ms", "Delay Variance (ms)",
                         0, 200, 30, step=5)

        self._add_separator(scroll)

        # Word Boundary
        self._add_toggle_group(scroll, "word_boundary_enabled", "Word Boundary", True, [
            ("intra_word_speed_factor", "Intra-word Factor", 0.3, 1.0, 0.8, 0.05),
            ("inter_word_pause_ms", "Inter-word Pause (ms)", 0, 500, 120, 10),
        ])

        self._add_separator(scroll)

        # Punctuation Pause
        self._add_toggle_slider(scroll, "punctuation_pause_enabled", "Punctuation Pause",
                                True, "punctuation_pause_ms", 0, 1000, 200, 10)

        # Newline Pause
        self._add_toggle_slider(scroll, "newline_pause_enabled", "Newline Pause",
                                True, "newline_pause_ms", 0, 2000, 400, 50)

        # Shift Penalty
        self._add_toggle_slider(scroll, "shift_penalty_enabled", "Shift Penalty",
                                True, "shift_penalty_ms", 0, 100, 25, 5)

        self._add_separator(scroll)

        # Double Letter Speed
        self._add_toggle_slider(scroll, "double_letter_enabled", "Double Letter Speed",
                                True, "double_letter_speed_factor", 0.3, 1.0, 0.6, 0.05,
                                is_float=True)

        self._add_separator(scroll)

        # Burst Typing
        self._add_toggle_group(scroll, "burst_enabled", "Burst Typing", False, [
            ("burst_length_min", "Burst Min Length", 2, 10, 2, 1),
            ("burst_length_max", "Burst Max Length", 2, 10, 5, 1),
            ("burst_pause_ms", "Burst Pause (ms)", 0, 200, 40, 5),
        ])

        self._add_separator(scroll)

        # Fatigue
        self._add_toggle_slider(scroll, "fatigue_enabled", "Fatigue",
                                True, "fatigue_factor", 0.0, 0.5, 0.05, 0.01,
                                is_float=True)

        self._add_separator(scroll)

        # 입력 모드
        self._vars["precise_mode"] = ctk.BooleanVar(value=False)
        row = ctk.CTkFrame(scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text="입력 모드:", font=ctk.CTkFont(size=11)).pack(side="left")
        ctk.CTkSwitch(
            row, text="정교 모드 (Shift press/release 분리)",
            variable=self._vars["precise_mode"],
            font=ctk.CTkFont(size=11),
            command=self._notify_change,
        ).pack(side="left", padx=8)

    # ── 오타 탭 ──

    def _build_typo_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill="both", expand=True)

        # 오타 확률
        self._add_slider(scroll, "typo_prob", "오타 확률 (만분율)",
                         0, 500, 30, step=5,
                         format_fn=lambda v: f"{v:.0f} ({v/100:.2f}%)")

        # 수정 확률
        self._add_slider(scroll, "typo_revision_prob", "수정 확률 (%)",
                         0, 99, 85, step=1,
                         format_fn=lambda v: f"{v:.0f}%")

        self._add_separator(scroll)

        # 오타 유형 토글
        ctk.CTkLabel(scroll, text="오타 유형",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      anchor="w").pack(fill="x", pady=(4, 2))

        self._add_checkbox(scroll, "adjacent_key_enabled", "인접 키 오타 (Adjacent Key)", True)
        self._add_checkbox(scroll, "transposition_enabled", "글자 전치 (Transposition)", False)
        self._add_checkbox(scroll, "double_strike_enabled", "이중 입력 (Double Strike)", False)

    # ============================================================
    # 위젯 헬퍼
    # ============================================================

    def _add_slider(self, parent, key: str, label: str,
                    min_val: float, max_val: float, default: float,
                    step: float = 1, is_float: bool = False,
                    format_fn: Callable | None = None):
        """슬라이더 + 값 표시 라벨."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)

        # 라벨
        ctk.CTkLabel(
            row, text=label, font=ctk.CTkFont(size=11),
            width=180, anchor="w",
        ).pack(side="left")

        # 값 변수
        if is_float or isinstance(default, float) and step < 1:
            var = ctk.DoubleVar(value=default)
        else:
            var = ctk.DoubleVar(value=default)
        self._vars[key] = var

        # 값 표시 라벨
        if format_fn:
            val_text = format_fn(default)
        elif is_float or step < 1:
            val_text = f"{default:.2f}"
        else:
            val_text = f"{default:.0f}"

        val_label = ctk.CTkLabel(
            row, text=val_text, width=80,
            font=ctk.CTkFont(family="Consolas", size=11),
            anchor="e",
        )
        val_label.pack(side="right")

        # 슬라이더
        def on_change(value):
            if not is_float and step >= 1:
                value = round(value / step) * step
                var.set(value)
            if format_fn:
                val_label.configure(text=format_fn(value))
            elif is_float or step < 1:
                val_label.configure(text=f"{value:.2f}")
            else:
                val_label.configure(text=f"{value:.0f}")
            self._notify_change()

        slider = ctk.CTkSlider(
            row, from_=min_val, to=max_val,
            variable=var,
            width=250,
            command=on_change,
        )
        slider.pack(side="right", padx=(4, 4))

        return var, slider, val_label

    def _add_toggle_slider(self, parent, toggle_key: str, toggle_label: str,
                           toggle_default: bool,
                           slider_key: str, min_val: float, max_val: float,
                           default: float, step: float,
                           is_float: bool = False):
        """토글 + 슬라이더 조합. 토글 OFF 시 슬라이더 비활성화."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)

        toggle_var = ctk.BooleanVar(value=toggle_default)
        self._vars[toggle_key] = toggle_var

        # 값 변수
        slider_var = ctk.DoubleVar(value=default)
        self._vars[slider_key] = slider_var

        # 값 표시
        if is_float or step < 1:
            val_text = f"{default:.2f}"
        else:
            val_text = f"{default:.0f}"

        val_label = ctk.CTkLabel(
            row, text=val_text, width=80,
            font=ctk.CTkFont(family="Consolas", size=11),
            anchor="e",
        )
        val_label.pack(side="right")

        # 슬라이더
        def on_slider(value):
            if not is_float and step >= 1:
                value = round(value / step) * step
                slider_var.set(value)
            if is_float or step < 1:
                val_label.configure(text=f"{value:.2f}")
            else:
                val_label.configure(text=f"{value:.0f}")
            self._notify_change()

        slider = ctk.CTkSlider(
            row, from_=min_val, to=max_val,
            variable=slider_var,
            width=250,
            command=on_slider,
        )
        slider.pack(side="right", padx=(4, 4))

        # 토글
        def on_toggle():
            state = "normal" if toggle_var.get() else "disabled"
            slider.configure(state=state)
            self._notify_change()

        switch = ctk.CTkSwitch(
            row, text=toggle_label,
            variable=toggle_var,
            font=ctk.CTkFont(size=11),
            command=on_toggle,
            width=180,
        )
        switch.pack(side="left")

        # 초기 상태 반영
        if not toggle_default:
            slider.configure(state="disabled")

    def _add_toggle_group(self, parent, toggle_key: str, toggle_label: str,
                          toggle_default: bool,
                          sliders: list[tuple]):
        """토글 + 여러 슬라이더 그룹. 토글 OFF 시 전체 비활성화."""
        toggle_var = ctk.BooleanVar(value=toggle_default)
        self._vars[toggle_key] = toggle_var

        # 토글 행
        toggle_row = ctk.CTkFrame(parent, fg_color="transparent")
        toggle_row.pack(fill="x", pady=(4, 0))

        child_widgets = []

        for (s_key, s_label, s_min, s_max, s_default, s_step) in sliders:
            is_float = isinstance(s_default, float) and s_step < 1
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=(20, 0), pady=1)

            ctk.CTkLabel(
                row, text=f"├ {s_label}", font=ctk.CTkFont(size=11),
                width=170, anchor="w",
            ).pack(side="left")

            s_var = ctk.DoubleVar(value=s_default)
            self._vars[s_key] = s_var

            if is_float:
                val_text = f"{s_default:.2f}"
            else:
                val_text = f"{s_default:.0f}"

            val_label = ctk.CTkLabel(
                row, text=val_text, width=60,
                font=ctk.CTkFont(family="Consolas", size=11),
                anchor="e",
            )
            val_label.pack(side="right")

            def make_on_change(v, vl, fl, st):
                def on_change(value):
                    if not fl and st >= 1:
                        value = round(value / st) * st
                        v.set(value)
                    if fl:
                        vl.configure(text=f"{value:.2f}")
                    else:
                        vl.configure(text=f"{value:.0f}")
                    self._notify_change()
                return on_change

            slider = ctk.CTkSlider(
                row, from_=s_min, to=s_max,
                variable=s_var,
                width=220,
                command=make_on_change(s_var, val_label, is_float, s_step),
            )
            slider.pack(side="right", padx=(4, 4))
            child_widgets.append(slider)

            if not toggle_default:
                slider.configure(state="disabled")

        # 토글 연동
        def on_toggle():
            state = "normal" if toggle_var.get() else "disabled"
            for w in child_widgets:
                w.configure(state=state)
            self._notify_change()

        switch = ctk.CTkSwitch(
            toggle_row, text=toggle_label,
            variable=toggle_var,
            font=ctk.CTkFont(size=11),
            command=on_toggle,
        )
        switch.pack(side="left")

    def _add_checkbox(self, parent, key: str, label: str, default: bool):
        """단독 체크박스."""
        var = ctk.BooleanVar(value=default)
        self._vars[key] = var

        ctk.CTkCheckBox(
            parent, text=label,
            variable=var,
            font=ctk.CTkFont(size=11),
            command=self._notify_change,
        ).pack(fill="x", pady=2)

    def _add_separator(self, parent):
        sep = ctk.CTkFrame(parent, height=1, fg_color="gray40")
        sep.pack(fill="x", pady=6)

    # ============================================================
    # 값 읽기 인터페이스
    # ============================================================

    def _get(self, key: str, default=None):
        """변수 값 읽기."""
        var = self._vars.get(key)
        if var is None:
            return default
        return var.get()

    def get_timing_config(self) -> TimingConfig:
        """현재 슬라이더/토글 값으로 TimingConfig 생성."""
        return TimingConfig(
            base_delay_ms=int(self._get("base_delay_ms", 70)),
            delay_variance_ms=int(self._get("delay_variance_ms", 30)),
            word_boundary_enabled=bool(self._get("word_boundary_enabled", True)),
            intra_word_speed_factor=float(self._get("intra_word_speed_factor", 0.8)),
            inter_word_pause_ms=int(self._get("inter_word_pause_ms", 120)),
            punctuation_pause_enabled=bool(self._get("punctuation_pause_enabled", True)),
            punctuation_pause_ms=int(self._get("punctuation_pause_ms", 200)),
            newline_pause_enabled=bool(self._get("newline_pause_enabled", True)),
            newline_pause_ms=int(self._get("newline_pause_ms", 400)),
            shift_penalty_enabled=bool(self._get("shift_penalty_enabled", True)),
            shift_penalty_ms=int(self._get("shift_penalty_ms", 25)),
            double_letter_enabled=bool(self._get("double_letter_enabled", True)),
            double_letter_speed_factor=float(self._get("double_letter_speed_factor", 0.6)),
            burst_enabled=bool(self._get("burst_enabled", False)),
            burst_length_min=int(self._get("burst_length_min", 2)),
            burst_length_max=int(self._get("burst_length_max", 5)),
            burst_pause_ms=int(self._get("burst_pause_ms", 40)),
            fatigue_enabled=bool(self._get("fatigue_enabled", True)),
            fatigue_factor=float(self._get("fatigue_factor", 0.05)),
        )

    def get_typo_config(self) -> TypoConfig:
        """현재 슬라이더/토글 값으로 TypoConfig 생성."""
        return TypoConfig(
            typo_prob=int(self._get("typo_prob", 30)),
            typo_revision_prob=int(self._get("typo_revision_prob", 85)),
            adjacent_key_enabled=bool(self._get("adjacent_key_enabled", True)),
            transposition_enabled=bool(self._get("transposition_enabled", False)),
            double_strike_enabled=bool(self._get("double_strike_enabled", False)),
        )

    def get_precise_mode(self) -> bool:
        return bool(self._get("precise_mode", False))

    def _notify_change(self):
        """설정 변경 시 콜백 호출."""
        if self._on_settings_changed:
            self._on_settings_changed()

    # ============================================================
    # 프리셋 적용 (외부에서 호출)
    # ============================================================

    def apply_config(self, timing: TimingConfig, typo: TypoConfig, control: dict):
        """프리셋 로드 시 모든 슬라이더/토글 값을 일괄 설정."""
        from dataclasses import asdict

        # TimingConfig 필드 적용
        for key, val in asdict(timing).items():
            var = self._vars.get(key)
            if var is not None:
                var.set(val)

        # TypoConfig 필드 적용
        for key, val in asdict(typo).items():
            var = self._vars.get(key)
            if var is not None:
                var.set(val)

        # control 필드 적용
        precise_var = self._vars.get("precise_mode")
        if precise_var is not None:
            precise_var.set(control.get("precise_mode", False))

        # 콜백 트리거
        self._notify_change()
