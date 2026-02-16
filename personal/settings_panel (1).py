"""
설정 패널 — 타이밍/오타/고급 옵션을 탭뷰로 구성.

모든 슬라이더/토글 변경 시 on_config_changed 콜백을 호출하여
ControlPanel → Engine에 즉시 반영.
"""

import customtkinter as ctk
from dataclasses import dataclass
from typing import Callable

from core.timing_model import TimingConfig
from core.typo_model import TypoConfig
from core.text_preprocessor import PreprocessConfig


# ============================================================
# 슬라이더 + 라벨 위젯 (재사용)
# ============================================================

class LabeledSlider(ctk.CTkFrame):
    """슬라이더 + 이름 라벨 + 현재 값 라벨."""

    def __init__(
        self, master,
        label: str,
        from_: float, to: float,
        default: float,
        step: float = 1,
        suffix: str = "",
        fmt: str = ".0f",
        on_change: Callable | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._step = step
        self._suffix = suffix
        self._fmt = fmt
        self._on_change = on_change

        # 라벨
        self._label = ctk.CTkLabel(
            self, text=label,
            font=ctk.CTkFont(size=11),
            anchor="w", width=140,
        )
        self._label.pack(side="left", padx=(0, 4))

        # 값 표시
        self._value_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="e", width=60,
        )
        self._value_label.pack(side="right", padx=(4, 0))

        # 슬라이더
        self._slider = ctk.CTkSlider(
            self,
            from_=from_, to=to,
            number_of_steps=int((to - from_) / step) if step > 0 else 100,
            command=self._on_slider,
        )
        self._slider.set(default)
        self._slider.pack(side="left", fill="x", expand=True, padx=4)

        self._update_label(default)

    def _on_slider(self, value):
        self._update_label(value)
        if self._on_change:
            self._on_change()

    def _update_label(self, value):
        txt = f"{value:{self._fmt}}{self._suffix}"
        self._value_label.configure(text=txt)

    def get(self) -> float:
        return self._slider.get()

    def set(self, value: float):
        self._slider.set(value)
        self._update_label(value)

    def configure_state(self, state: str):
        self._slider.configure(state=state)


class LabeledSwitch(ctk.CTkFrame):
    """스위치 토글 + 라벨."""

    def __init__(
        self, master,
        label: str,
        default: bool = False,
        on_change: Callable | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_change = on_change

        self._var = ctk.BooleanVar(value=default)
        self._switch = ctk.CTkSwitch(
            self, text=label,
            variable=self._var,
            font=ctk.CTkFont(size=11),
            command=self._on_toggle,
            onvalue=True, offvalue=False,
        )
        self._switch.pack(side="left", padx=0)

    def _on_toggle(self):
        if self._on_change:
            self._on_change()

    def get(self) -> bool:
        return self._var.get()

    def set(self, value: bool):
        self._var.set(value)

    def configure_state(self, state: str):
        self._switch.configure(state=state)


# ============================================================
# 설정 패널
# ============================================================

class SettingsPanel(ctk.CTkFrame):
    """설정 패널. 타이밍/오타/고급 탭."""

    def __init__(self, master, on_config_changed: Callable | None = None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_config_changed = on_config_changed

        self._build_ui()

    def _notify(self):
        """설정 변경 시 콜백 호출."""
        if self._on_config_changed:
            self._on_config_changed()

    def _build_ui(self):
        # 섹션 라벨
        ctk.CTkLabel(
            self, text="⚙️ 설정",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        # 탭뷰
        self._tabview = ctk.CTkTabview(self, height=250)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._tabview.add("타이밍")
        self._tabview.add("오타")
        self._tabview.add("고급")

        self._build_timing_tab(self._tabview.tab("타이밍"))
        self._build_typo_tab(self._tabview.tab("오타"))
        self._build_advanced_tab(self._tabview.tab("고급"))

    # ── 타이밍 탭 ──

    def _build_timing_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        self._s_base_delay = LabeledSlider(
            scroll, "기본 딜레이", 20, 200, 70, step=5, suffix="ms",
            on_change=self._notify,
        )
        self._s_base_delay.pack(fill="x", pady=2)

        self._s_variance = LabeledSlider(
            scroll, "딜레이 분산", 0, 80, 30, step=5, suffix="ms",
            on_change=self._notify,
        )
        self._s_variance.pack(fill="x", pady=2)

        # 단어 경계
        self._sw_word = LabeledSwitch(
            scroll, "단어 경계 딜레이", default=True, on_change=self._notify,
        )
        self._sw_word.pack(fill="x", pady=2)

        self._s_inter_word = LabeledSlider(
            scroll, "  단어 간 pause", 30, 300, 120, step=10, suffix="ms",
            on_change=self._notify,
        )
        self._s_inter_word.pack(fill="x", pady=2)

        self._s_intra_word = LabeledSlider(
            scroll, "  단어 내 가속", 0.5, 1.0, 0.8, step=0.05, suffix="×",
            fmt=".2f", on_change=self._notify,
        )
        self._s_intra_word.pack(fill="x", pady=2)

        # 구두점
        self._sw_punct = LabeledSwitch(
            scroll, "구두점 pause", default=True, on_change=self._notify,
        )
        self._sw_punct.pack(fill="x", pady=2)

        self._s_punct_pause = LabeledSlider(
            scroll, "  구두점 pause", 50, 500, 200, step=10, suffix="ms",
            on_change=self._notify,
        )
        self._s_punct_pause.pack(fill="x", pady=2)

        # 개행
        self._sw_newline = LabeledSwitch(
            scroll, "개행 pause", default=True, on_change=self._notify,
        )
        self._sw_newline.pack(fill="x", pady=2)

        self._s_newline_pause = LabeledSlider(
            scroll, "  개행 pause", 0, 2000, 400, step=50, suffix="ms",
            on_change=self._notify,
        )
        self._s_newline_pause.pack(fill="x", pady=2)

        # Shift
        self._sw_shift = LabeledSwitch(
            scroll, "Shift 패널티", default=True, on_change=self._notify,
        )
        self._sw_shift.pack(fill="x", pady=2)

        self._s_shift_penalty = LabeledSlider(
            scroll, "  Shift 추가", 0, 80, 25, step=5, suffix="ms",
            on_change=self._notify,
        )
        self._s_shift_penalty.pack(fill="x", pady=2)

        # 동일 글자
        self._sw_double = LabeledSwitch(
            scroll, "동일 글자 가속", default=True, on_change=self._notify,
        )
        self._sw_double.pack(fill="x", pady=2)

        self._s_double_factor = LabeledSlider(
            scroll, "  가속 계수", 0.3, 1.0, 0.6, step=0.05, suffix="×",
            fmt=".2f", on_change=self._notify,
        )
        self._s_double_factor.pack(fill="x", pady=2)

        # 버스트
        self._sw_burst = LabeledSwitch(
            scroll, "버스트 타이핑", default=False, on_change=self._notify,
        )
        self._sw_burst.pack(fill="x", pady=2)

        self._s_burst_pause = LabeledSlider(
            scroll, "  버스트 pause", 10, 100, 40, step=5, suffix="ms",
            on_change=self._notify,
        )
        self._s_burst_pause.pack(fill="x", pady=2)

        # 피로
        self._sw_fatigue = LabeledSwitch(
            scroll, "타이핑 피로", default=True, on_change=self._notify,
        )
        self._sw_fatigue.pack(fill="x", pady=2)

        self._s_fatigue_factor = LabeledSlider(
            scroll, "  피로 계수", 0.0, 0.20, 0.05, step=0.01, suffix="",
            fmt=".2f", on_change=self._notify,
        )
        self._s_fatigue_factor.pack(fill="x", pady=2)

    # ── 오타 탭 ──

    def _build_typo_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # 오타 확률
        self._s_typo_prob = LabeledSlider(
            scroll, "오타 확률", 0, 500, 30, step=5, suffix=" (만분율)",
            fmt=".0f", on_change=self._notify,
        )
        self._s_typo_prob.pack(fill="x", pady=2)

        # 확률 설명 라벨
        self._typo_prob_desc = ctk.CTkLabel(
            scroll,
            text="  → 0.30% (1000자당 약 3개 오타)",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            anchor="w",
        )
        self._typo_prob_desc.pack(fill="x", padx=(148, 0), pady=(0, 4))

        # 슬라이더 변경 시 설명 업데이트
        orig_notify = self._notify
        def _notify_with_desc():
            prob = self._s_typo_prob.get()
            pct = prob / 100
            per1000 = prob / 10
            self._typo_prob_desc.configure(
                text=f"  → {pct:.2f}% (1000자당 약 {per1000:.0f}개 오타)"
            )
            orig_notify()
        self._s_typo_prob._on_change = _notify_with_desc

        # 수정 확률
        self._s_revision_prob = LabeledSlider(
            scroll, "오타 수정 확률", 0, 100, 85, step=5, suffix="%",
            on_change=self._notify,
        )
        self._s_revision_prob.pack(fill="x", pady=2)

        # 오타 유형 토글
        ctk.CTkLabel(
            scroll, text="오타 유형:",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x", padx=4, pady=(8, 2))

        self._sw_adjacent = LabeledSwitch(
            scroll, "인접 키 오타 (가장 흔함)", default=True, on_change=self._notify,
        )
        self._sw_adjacent.pack(fill="x", pady=2)

        self._sw_transposition = LabeledSwitch(
            scroll, "글자 전치 오타 (두 글자 순서 뒤바뀜)", default=False, on_change=self._notify,
        )
        self._sw_transposition.pack(fill="x", pady=2)

        self._sw_double_strike = LabeledSwitch(
            scroll, "이중 입력 오타 (같은 키 두 번)", default=False, on_change=self._notify,
        )
        self._sw_double_strike.pack(fill="x", pady=2)

    # ── 고급 탭 ──

    def _build_advanced_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # 입력 모드
        ctk.CTkLabel(
            scroll, text="키 입력 모드:",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x", padx=4, pady=(4, 2))

        self._input_mode_var = ctk.StringVar(value="simple")
        mode_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        mode_frame.pack(fill="x", padx=4, pady=2)

        ctk.CTkRadioButton(
            mode_frame, text="간편 모드 (type() 자동 처리)",
            variable=self._input_mode_var, value="simple",
            font=ctk.CTkFont(size=11),
            command=self._notify,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkRadioButton(
            mode_frame, text="정교 모드 (Shift 명시적 press/release)",
            variable=self._input_mode_var, value="precise",
            font=ctk.CTkFont(size=11),
            command=self._notify,
        ).pack(side="left")

        # 구분선
        ctk.CTkLabel(
            scroll, text="텍스트 전처리:",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x", padx=4, pady=(12, 2))

        self._sw_normalize_spaces = LabeledSwitch(
            scroll, "연속 공백 정규화 (2개 이상 → 1개)",
            default=False, on_change=self._notify,
        )
        self._sw_normalize_spaces.pack(fill="x", pady=2)

        # 개행 처리 모드
        newline_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        newline_frame.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(
            newline_frame, text="개행 처리:",
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).pack(side="left", padx=(0, 8))

        self._newline_mode_var = ctk.StringVar(value="enter")
        for text, value in [("Enter 유지", "enter"), ("Space 치환", "space"), ("제거", "remove")]:
            ctk.CTkRadioButton(
                newline_frame, text=text,
                variable=self._newline_mode_var, value=value,
                font=ctk.CTkFont(size=11),
                command=self._notify,
            ).pack(side="left", padx=(0, 8))

        # 최대 길이
        self._sw_max_length = LabeledSwitch(
            scroll, "최대 길이 제한", default=False, on_change=self._notify,
        )
        self._sw_max_length.pack(fill="x", pady=2)

        self._s_max_length = LabeledSlider(
            scroll, "  최대 글자 수", 100, 50000, 10000, step=100, suffix="자",
            on_change=self._notify,
        )
        self._s_max_length.pack(fill="x", pady=2)

    # ============================================================
    # Config 빌더 (패널 → dataclass)
    # ============================================================

    def get_timing_config(self) -> TimingConfig:
        """현재 슬라이더/토글 값으로 TimingConfig 생성."""
        return TimingConfig(
            base_delay_ms=int(self._s_base_delay.get()),
            delay_variance_ms=int(self._s_variance.get()),
            word_boundary_enabled=self._sw_word.get(),
            intra_word_speed_factor=round(self._s_intra_word.get(), 2),
            inter_word_pause_ms=int(self._s_inter_word.get()),
            punctuation_pause_enabled=self._sw_punct.get(),
            punctuation_pause_ms=int(self._s_punct_pause.get()),
            newline_pause_enabled=self._sw_newline.get(),
            newline_pause_ms=int(self._s_newline_pause.get()),
            shift_penalty_enabled=self._sw_shift.get(),
            shift_penalty_ms=int(self._s_shift_penalty.get()),
            double_letter_enabled=self._sw_double.get(),
            double_letter_speed_factor=round(self._s_double_factor.get(), 2),
            burst_enabled=self._sw_burst.get(),
            burst_pause_ms=int(self._s_burst_pause.get()),
            fatigue_enabled=self._sw_fatigue.get(),
            fatigue_factor=round(self._s_fatigue_factor.get(), 2),
        )

    def get_typo_config(self) -> TypoConfig:
        """현재 슬라이더/토글 값으로 TypoConfig 생성."""
        return TypoConfig(
            typo_prob=int(self._s_typo_prob.get()),
            typo_revision_prob=int(self._s_revision_prob.get()),
            adjacent_key_enabled=self._sw_adjacent.get(),
            transposition_enabled=self._sw_transposition.get(),
            double_strike_enabled=self._sw_double_strike.get(),
        )

    def get_preprocess_config(self) -> PreprocessConfig:
        """현재 토글 값으로 PreprocessConfig 생성."""
        return PreprocessConfig(
            normalize_spaces=self._sw_normalize_spaces.get(),
            newline_mode=self._newline_mode_var.get(),
            max_length_enabled=self._sw_max_length.get(),
            max_length=int(self._s_max_length.get()),
        )

    def is_precise_mode(self) -> bool:
        """정교 모드 여부."""
        return self._input_mode_var.get() == "precise"

    # ============================================================
    # Config 로더 (dataclass → 패널)
    # ============================================================

    def set_timing_config(self, cfg: TimingConfig):
        """TimingConfig를 슬라이더/토글에 반영."""
        self._s_base_delay.set(cfg.base_delay_ms)
        self._s_variance.set(cfg.delay_variance_ms)
        self._sw_word.set(cfg.word_boundary_enabled)
        self._s_inter_word.set(cfg.inter_word_pause_ms)
        self._s_intra_word.set(cfg.intra_word_speed_factor)
        self._sw_punct.set(cfg.punctuation_pause_enabled)
        self._s_punct_pause.set(cfg.punctuation_pause_ms)
        self._sw_newline.set(cfg.newline_pause_enabled)
        self._s_newline_pause.set(cfg.newline_pause_ms)
        self._sw_shift.set(cfg.shift_penalty_enabled)
        self._s_shift_penalty.set(cfg.shift_penalty_ms)
        self._sw_double.set(cfg.double_letter_enabled)
        self._s_double_factor.set(cfg.double_letter_speed_factor)
        self._sw_burst.set(cfg.burst_enabled)
        self._s_burst_pause.set(cfg.burst_pause_ms)
        self._sw_fatigue.set(cfg.fatigue_enabled)
        self._s_fatigue_factor.set(cfg.fatigue_factor)

    def set_typo_config(self, cfg: TypoConfig):
        """TypoConfig를 슬라이더/토글에 반영."""
        self._s_typo_prob.set(cfg.typo_prob)
        self._s_revision_prob.set(cfg.typo_revision_prob)
        self._sw_adjacent.set(cfg.adjacent_key_enabled)
        self._sw_transposition.set(cfg.transposition_enabled)
        self._sw_double_strike.set(cfg.double_strike_enabled)
