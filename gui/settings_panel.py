"""
설정 창 — 별도 CTkToplevel 윈도우.
메인에서 ⚙ 설정 버튼으로 열림.

슬라이더: factor류 (0~1 스케일)만
숫자 입력: 나머지 전부 (ms 값, 확률 등)
"""

import customtkinter as ctk
from typing import Callable

from core.timing_model import TimingConfig
from core.typo_model import TypoConfig
from core.text_preprocessor import PreprocessConfig


# ============================================================
# 재사용 위젯
# ============================================================

class NumEntry(ctk.CTkFrame):
    """라벨 + 숫자 입력 (Entry). 범위 검증 포함."""

    def __init__(self, master, label: str, default: float,
                 min_val: float = 0, max_val: float = 99999,
                 suffix: str = "", is_int: bool = True,
                 on_change: Callable | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._min = min_val
        self._max = max_val
        self._is_int = is_int
        self._on_change = on_change

        ctk.CTkLabel(self, text=label, font=ctk.CTkFont(size=11),
                      anchor="w", width=160).pack(side="left", padx=(0, 4))

        self._var = ctk.StringVar(value=str(int(default) if is_int else f"{default:.2f}"))
        self._entry = ctk.CTkEntry(
            self, textvariable=self._var, width=70, height=26,
            font=ctk.CTkFont(size=11), justify="right",
        )
        self._entry.pack(side="left", padx=2)
        self._entry.bind("<FocusOut>", self._validate)
        self._entry.bind("<Return>", self._validate)

        if suffix:
            ctk.CTkLabel(self, text=suffix, font=ctk.CTkFont(size=10),
                          text_color="gray").pack(side="left", padx=(2, 0))

    def _validate(self, event=None):
        try:
            val = float(self._var.get())
            val = max(self._min, min(self._max, val))
            if self._is_int:
                self._var.set(str(int(val)))
            else:
                self._var.set(f"{val:.2f}")
        except ValueError:
            self._var.set(str(int(self._min) if self._is_int else f"{self._min:.2f}"))
        if self._on_change:
            self._on_change()

    def get(self) -> float:
        try:
            val = float(self._var.get())
            return max(self._min, min(self._max, val))
        except ValueError:
            return self._min

    def set(self, value: float):
        if self._is_int:
            self._var.set(str(int(value)))
        else:
            self._var.set(f"{value:.2f}")


class FactorSlider(ctk.CTkFrame):
    """라벨 + 슬라이더 (0~1 factor류). 숫자 표시 포함."""

    def __init__(self, master, label: str, from_: float, to: float,
                 default: float, step: float = 0.05,
                 on_change: Callable | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_change = on_change

        ctk.CTkLabel(self, text=label, font=ctk.CTkFont(size=11),
                      anchor="w", width=160).pack(side="left", padx=(0, 4))

        self._val_label = ctk.CTkLabel(self, text=f"{default:.2f}",
                                        font=ctk.CTkFont(size=11, weight="bold"),
                                        width=40).pack(side="right")
        self._val_lbl = ctk.CTkLabel(self, text=f"{default:.2f}",
                                      font=ctk.CTkFont(size=11, weight="bold"),
                                      anchor="e", width=40)
        self._val_lbl.pack(side="right", padx=(4, 0))

        self._slider = ctk.CTkSlider(
            self, from_=from_, to=to,
            number_of_steps=int((to - from_) / step),
            command=self._on_slide,
        )
        self._slider.set(default)
        self._slider.pack(side="left", fill="x", expand=True, padx=4)

    def _on_slide(self, val):
        self._val_lbl.configure(text=f"{val:.2f}")
        if self._on_change:
            self._on_change()

    def get(self) -> float:
        return round(self._slider.get(), 2)

    def set(self, value: float):
        self._slider.set(value)
        self._val_lbl.configure(text=f"{value:.2f}")


class LabeledSwitch(ctk.CTkFrame):
    """스위치 토글."""

    def __init__(self, master, label: str, default: bool = False,
                 on_change: Callable | None = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_change = on_change
        self._var = ctk.BooleanVar(value=default)
        ctk.CTkSwitch(
            self, text=label, variable=self._var,
            font=ctk.CTkFont(size=11), command=self._fire,
            onvalue=True, offvalue=False,
        ).pack(side="left")

    def _fire(self):
        if self._on_change:
            self._on_change()

    def get(self) -> bool:
        return self._var.get()

    def set(self, value: bool):
        self._var.set(value)


# ============================================================
# 설정 창
# ============================================================

class SettingsWindow(ctk.CTkToplevel):
    """별도 설정 창. 탭: 타이밍 / 오타 / 고급."""

    def __init__(self, master, on_config_changed: Callable | None = None):
        super().__init__(master)
        self.title("⚙ 설정")
        self.geometry("480x560")
        self.resizable(True, True)
        self.transient(master)

        self._on_config_changed = on_config_changed
        self._build_ui()

    def _notify(self):
        if self._on_config_changed:
            self._on_config_changed()

    def _build_ui(self):
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self._tabview.add("타이밍")
        self._tabview.add("오타")
        self._tabview.add("고급")

        self._build_timing_tab(self._tabview.tab("타이밍"))
        self._build_typo_tab(self._tabview.tab("오타"))
        self._build_advanced_tab(self._tabview.tab("고급"))

        ctk.CTkButton(self, text="닫기", width=80, command=self.withdraw
                       ).pack(pady=(0, 10))

    # ── 타이밍 ──

    def _build_timing_tab(self, parent):
        s = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        s.pack(fill="both", expand=True)
        n = self._notify

        self._e_base_delay = NumEntry(s, "기본 딜레이", 70, 10, 500, "ms", on_change=n)
        self._e_base_delay.pack(fill="x", pady=2)

        self._e_variance = NumEntry(s, "딜레이 분산", 30, 0, 200, "ms", on_change=n)
        self._e_variance.pack(fill="x", pady=2)

        self._sw_word = LabeledSwitch(s, "단어 경계 딜레이", True, n)
        self._sw_word.pack(fill="x", pady=2)

        self._e_inter_word = NumEntry(s, "  단어 간 pause", 120, 0, 1000, "ms", on_change=n)
        self._e_inter_word.pack(fill="x", pady=2)

        self._f_intra_word = FactorSlider(s, "  단어 내 가속", 0.3, 1.0, 0.8, on_change=n)
        self._f_intra_word.pack(fill="x", pady=2)

        self._sw_punct = LabeledSwitch(s, "구두점 pause", True, n)
        self._sw_punct.pack(fill="x", pady=2)

        self._e_punct_pause = NumEntry(s, "  구두점 pause", 200, 0, 2000, "ms", on_change=n)
        self._e_punct_pause.pack(fill="x", pady=2)

        self._sw_newline = LabeledSwitch(s, "개행 pause", True, n)
        self._sw_newline.pack(fill="x", pady=2)

        self._e_newline_pause = NumEntry(s, "  개행 pause", 400, 0, 5000, "ms", on_change=n)
        self._e_newline_pause.pack(fill="x", pady=2)

        self._sw_shift = LabeledSwitch(s, "Shift 패널티", True, n)
        self._sw_shift.pack(fill="x", pady=2)

        self._e_shift_penalty = NumEntry(s, "  Shift 추가", 25, 0, 200, "ms", on_change=n)
        self._e_shift_penalty.pack(fill="x", pady=2)

        self._sw_double = LabeledSwitch(s, "동일 글자 가속", True, n)
        self._sw_double.pack(fill="x", pady=2)

        self._f_double_factor = FactorSlider(s, "  가속 계수", 0.3, 1.0, 0.6, on_change=n)
        self._f_double_factor.pack(fill="x", pady=2)

        self._sw_burst = LabeledSwitch(s, "버스트 타이핑", False, n)
        self._sw_burst.pack(fill="x", pady=2)

        self._e_burst_pause = NumEntry(s, "  버스트 pause", 40, 5, 500, "ms", on_change=n)
        self._e_burst_pause.pack(fill="x", pady=2)

        self._sw_fatigue = LabeledSwitch(s, "타이핑 피로", True, n)
        self._sw_fatigue.pack(fill="x", pady=2)

        self._f_fatigue = FactorSlider(s, "  피로 계수", 0.0, 0.30, 0.05, step=0.01, on_change=n)
        self._f_fatigue.pack(fill="x", pady=2)

    # ── 오타 ──

    def _build_typo_tab(self, parent):
        s = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        s.pack(fill="both", expand=True)
        n = self._notify

        self._e_typo_prob = NumEntry(s, "오타 확률 (만분율)", 30, 0, 9999, on_change=n)
        self._e_typo_prob.pack(fill="x", pady=2)

        self._typo_desc = ctk.CTkLabel(s, text="  → 0.30% (1000자당 약 3개)",
                                        font=ctk.CTkFont(size=10), text_color="gray", anchor="w")
        self._typo_desc.pack(fill="x", padx=(168, 0), pady=(0, 4))

        self._e_revision_prob = NumEntry(s, "오타 수정 확률", 85, 0, 100, "%", on_change=n)
        self._e_revision_prob.pack(fill="x", pady=2)

        ctk.CTkLabel(s, text="오타 유형:", font=ctk.CTkFont(size=12),
                      anchor="w").pack(fill="x", padx=4, pady=(8, 2))

        self._sw_adjacent = LabeledSwitch(s, "인접 키 오타", True, n)
        self._sw_adjacent.pack(fill="x", pady=2)

        self._sw_transposition = LabeledSwitch(s, "글자 전치 오타", False, n)
        self._sw_transposition.pack(fill="x", pady=2)

        self._sw_double_strike = LabeledSwitch(s, "이중 입력 오타", False, n)
        self._sw_double_strike.pack(fill="x", pady=2)

    # ── 고급 ──

    def _build_advanced_tab(self, parent):
        s = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        s.pack(fill="both", expand=True)
        n = self._notify

        ctk.CTkLabel(s, text="키 입력 모드:", font=ctk.CTkFont(size=12),
                      anchor="w").pack(fill="x", padx=4, pady=(4, 2))

        self._input_mode_var = ctk.StringVar(value="simple")
        mode_frame = ctk.CTkFrame(s, fg_color="transparent")
        mode_frame.pack(fill="x", padx=4, pady=2)

        ctk.CTkRadioButton(mode_frame, text="간편 모드", variable=self._input_mode_var,
                            value="simple", font=ctk.CTkFont(size=11), command=n
                            ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(mode_frame, text="정교 모드 (Shift 명시적)",
                            variable=self._input_mode_var, value="precise",
                            font=ctk.CTkFont(size=11), command=n
                            ).pack(side="left")

        ctk.CTkLabel(s, text="텍스트 전처리:", font=ctk.CTkFont(size=12),
                      anchor="w").pack(fill="x", padx=4, pady=(12, 2))

        self._sw_normalize_spaces = LabeledSwitch(s, "연속 공백 정규화", False, n)
        self._sw_normalize_spaces.pack(fill="x", pady=2)

        nf = ctk.CTkFrame(s, fg_color="transparent")
        nf.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(nf, text="개행 처리:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))
        self._newline_mode_var = ctk.StringVar(value="enter")
        for txt, val in [("Enter", "enter"), ("Space", "space"), ("제거", "remove")]:
            ctk.CTkRadioButton(nf, text=txt, variable=self._newline_mode_var,
                                value=val, font=ctk.CTkFont(size=11), command=n
                                ).pack(side="left", padx=(0, 8))

        self._sw_max_length = LabeledSwitch(s, "최대 길이 제한", False, n)
        self._sw_max_length.pack(fill="x", pady=2)

        self._e_max_length = NumEntry(s, "  최대 글자 수", 10000, 100, 99999, "자", on_change=n)
        self._e_max_length.pack(fill="x", pady=2)

    # ============================================================
    # Config 빌더 (설정 창 → dataclass)
    # ============================================================

    def get_timing_config(self) -> TimingConfig:
        return TimingConfig(
            base_delay_ms=int(self._e_base_delay.get()),
            delay_variance_ms=int(self._e_variance.get()),
            word_boundary_enabled=self._sw_word.get(),
            intra_word_speed_factor=self._f_intra_word.get(),
            inter_word_pause_ms=int(self._e_inter_word.get()),
            punctuation_pause_enabled=self._sw_punct.get(),
            punctuation_pause_ms=int(self._e_punct_pause.get()),
            newline_pause_enabled=self._sw_newline.get(),
            newline_pause_ms=int(self._e_newline_pause.get()),
            shift_penalty_enabled=self._sw_shift.get(),
            shift_penalty_ms=int(self._e_shift_penalty.get()),
            double_letter_enabled=self._sw_double.get(),
            double_letter_speed_factor=self._f_double_factor.get(),
            burst_enabled=self._sw_burst.get(),
            burst_pause_ms=int(self._e_burst_pause.get()),
            fatigue_enabled=self._sw_fatigue.get(),
            fatigue_factor=self._f_fatigue.get(),
        )

    def get_typo_config(self) -> TypoConfig:
        return TypoConfig(
            typo_prob=int(self._e_typo_prob.get()),
            typo_revision_prob=int(self._e_revision_prob.get()),
            adjacent_key_enabled=self._sw_adjacent.get(),
            transposition_enabled=self._sw_transposition.get(),
            double_strike_enabled=self._sw_double_strike.get(),
        )

    def get_preprocess_config(self) -> PreprocessConfig:
        return PreprocessConfig(
            normalize_spaces=self._sw_normalize_spaces.get(),
            newline_mode=self._newline_mode_var.get(),
            max_length_enabled=self._sw_max_length.get(),
            max_length=int(self._e_max_length.get()),
        )

    def is_precise_mode(self) -> bool:
        return self._input_mode_var.get() == "precise"

    # ============================================================
    # Config 로더 (dataclass → 설정 창)
    # ============================================================

    def set_timing_config(self, c: TimingConfig):
        self._e_base_delay.set(c.base_delay_ms)
        self._e_variance.set(c.delay_variance_ms)
        self._sw_word.set(c.word_boundary_enabled)
        self._e_inter_word.set(c.inter_word_pause_ms)
        self._f_intra_word.set(c.intra_word_speed_factor)
        self._sw_punct.set(c.punctuation_pause_enabled)
        self._e_punct_pause.set(c.punctuation_pause_ms)
        self._sw_newline.set(c.newline_pause_enabled)
        self._e_newline_pause.set(c.newline_pause_ms)
        self._sw_shift.set(c.shift_penalty_enabled)
        self._e_shift_penalty.set(c.shift_penalty_ms)
        self._sw_double.set(c.double_letter_enabled)
        self._f_double_factor.set(c.double_letter_speed_factor)
        self._sw_burst.set(c.burst_enabled)
        self._e_burst_pause.set(c.burst_pause_ms)
        self._sw_fatigue.set(c.fatigue_enabled)
        self._f_fatigue.set(c.fatigue_factor)

    def set_typo_config(self, c: TypoConfig):
        self._e_typo_prob.set(c.typo_prob)
        self._e_revision_prob.set(c.typo_revision_prob)
        self._sw_adjacent.set(c.adjacent_key_enabled)
        self._sw_transposition.set(c.transposition_enabled)
        self._sw_double_strike.set(c.double_strike_enabled)
