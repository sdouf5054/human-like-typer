"""
메인 윈도우 — 전체 레이아웃 조합 + 상태 관리.

레이아웃:
1. 상단바: 프리셋 드롭다운 + Always on Top
2. 입력 소스 패널 (InputPanel)
3. 대상 텍스트 표시
4. 설정 패널 (SettingsPanel)
5. 컨트롤 패널 (ControlPanel)
"""

import customtkinter as ctk

from gui.input_panel import InputPanel
from gui.settings_panel import SettingsPanel
from gui.control_panel import ControlPanel
from core.text_preprocessor import preprocess, PreprocessConfig


class App(ctk.CTk):
    """Human-Like Typer 메인 윈도우."""

    def __init__(self):
        super().__init__()

        self.title("Human-Like Typer v1.0")
        self.geometry("750x900")
        self.minsize(600, 600)

        # 상태
        self._target_text: str = ""
        self._always_on_top = False

        self._build_ui()

        # 윈도우 닫기 시 정리
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        # ── 상단바 ──
        topbar = ctk.CTkFrame(self, height=40)
        topbar.pack(fill="x", padx=10, pady=(8, 4))
        topbar.pack_propagate(False)

        ctk.CTkLabel(
            topbar, text="프리셋:",
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 4))

        self._preset_dropdown = ctk.CTkOptionMenu(
            topbar,
            values=["기본 (Default)", "빠르고 정확한", "느리고 자연스러운", "오타 많은 초보"],
            width=180, height=28,
            font=ctk.CTkFont(size=11),
        )
        self._preset_dropdown.pack(side="left", padx=4)

        self._aot_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            topbar, text="📌 Always on Top",
            variable=self._aot_var,
            font=ctk.CTkFont(size=11),
            command=self._toggle_always_on_top,
            onvalue=True, offvalue=False, width=40,
        ).pack(side="right", padx=(4, 8))

        # ── 입력 소스 패널 ──
        self._input_panel = InputPanel(
            self, on_text_selected=self._on_text_selected,
        )
        self._input_panel.pack(fill="both", padx=10, pady=4, expand=False)

        # ── 대상 텍스트 표시 ──
        self._target_frame = ctk.CTkFrame(self, height=50)
        self._target_frame.pack(fill="x", padx=10, pady=4)
        self._target_frame.pack_propagate(False)

        self._target_label = ctk.CTkLabel(
            self._target_frame,
            text="대상 텍스트: (설정되지 않음)",
            font=ctk.CTkFont(size=12),
            text_color="gray", anchor="w",
        )
        self._target_label.pack(fill="x", padx=10, pady=10)

        # ── 설정 패널 ──
        self._settings_panel = SettingsPanel(
            self, on_config_changed=self._on_settings_changed,
        )
        self._settings_panel.pack(fill="both", padx=10, pady=4, expand=True)

        # ── 컨트롤 패널 ──
        self._control_panel = ControlPanel(
            self,
            get_target_text=lambda: self._target_text,
            get_settings=self._get_current_settings,
        )
        self._control_panel.pack(fill="both", padx=10, pady=(4, 8), expand=True)

    # ── 이벤트 핸들러 ──

    def _on_text_selected(self, raw_text: str):
        """입력 패널에서 '이 텍스트 사용' 클릭 시 호출."""
        preprocess_cfg = self._settings_panel.get_preprocess_config()
        text = preprocess(raw_text, preprocess_cfg)
        self._target_text = text

        if text:
            preview = text[:60].replace('\n', '↵')
            suffix = "..." if len(text) > 60 else ""
            self._target_label.configure(
                text=f"대상 텍스트: \"{preview}{suffix}\" ({len(text)}자)",
                text_color=("gray10", "gray90"),
            )
        else:
            self._target_label.configure(
                text="대상 텍스트: (비어있음)",
                text_color="gray",
            )

    def _toggle_always_on_top(self):
        self._always_on_top = self._aot_var.get()
        self.attributes("-topmost", self._always_on_top)

    def _on_settings_changed(self):
        """설정 패널 값 변경 시 — 예상 시간 재계산."""
        timing = self._settings_panel.get_timing_config()
        self._input_panel.update_base_delay(timing.base_delay_ms)

    def _get_current_settings(self) -> tuple:
        """컨트롤 패널이 엔진 생성 시 호출 — 현재 설정 값 반환."""
        return (
            self._settings_panel.get_timing_config(),
            self._settings_panel.get_typo_config(),
            self._settings_panel.is_precise_mode(),
        )

    def _on_closing(self):
        self._control_panel.destroy()
        self.destroy()

    # ── 외부 인터페이스 ──

    @property
    def target_text(self) -> str:
        return self._target_text

    def get_input_panel(self) -> InputPanel:
        return self._input_panel

    def get_settings_panel(self) -> SettingsPanel:
        return self._settings_panel

    def get_control_panel(self) -> ControlPanel:
        return self._control_panel
