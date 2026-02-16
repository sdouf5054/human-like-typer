"""
메인 윈도우 — 전체 레이아웃 조합 + 상태 관리.

레이아웃 (상하 구조):
1. 상단바: 프리셋 드롭다운 + Always on Top
2. 입력 소스 패널 (InputPanel)
3. 대상 텍스트 표시
4. 설정 패널 (Step 9에서 추가)
5. 컨트롤 패널 (ControlPanel)
"""

import customtkinter as ctk

from gui.input_panel import InputPanel
from gui.control_panel import ControlPanel
from core.text_preprocessor import preprocess, PreprocessConfig


class App(ctk.CTk):
    """Human-Like Typer 메인 윈도우."""

    def __init__(self):
        super().__init__()

        # 윈도우 기본 설정
        self.title("Human-Like Typer v1.0")
        self.geometry("750x850")
        self.minsize(600, 500)

        # 상태
        self._target_text: str = ""
        self._always_on_top = False
        self._preprocess_config = PreprocessConfig()

        self._build_ui()

        # 윈도우 닫기 시 정리
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        # ── 상단바 ──
        topbar = ctk.CTkFrame(self, height=40)
        topbar.pack(fill="x", padx=10, pady=(8, 4))
        topbar.pack_propagate(False)

        # 프리셋 (placeholder — Step 10에서 완성)
        ctk.CTkLabel(
            topbar, text="프리셋:",
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 4))

        self._preset_dropdown = ctk.CTkOptionMenu(
            topbar, values=["기본 (Default)", "빠르고 정확한", "느리고 자연스러운", "오타 많은 초보"],
            width=160, height=28,
            font=ctk.CTkFont(size=11),
        )
        self._preset_dropdown.pack(side="left", padx=4)

        # Always on Top 토글
        self._aot_var = ctk.BooleanVar(value=False)
        self._aot_switch = ctk.CTkSwitch(
            topbar, text="📌 Always on Top",
            variable=self._aot_var,
            font=ctk.CTkFont(size=11),
            command=self._toggle_always_on_top,
            onvalue=True, offvalue=False,
            width=40,
        )
        self._aot_switch.pack(side="right", padx=(4, 8))

        # ── 입력 소스 패널 ──
        self._input_panel = InputPanel(
            self,
            on_text_selected=self._on_text_selected,
        )
        self._input_panel.pack(fill="both", padx=10, pady=4, expand=False)

        # ── 대상 텍스트 표시 영역 ──
        self._target_frame = ctk.CTkFrame(self, height=50)
        self._target_frame.pack(fill="x", padx=10, pady=4)
        self._target_frame.pack_propagate(False)

        self._target_label = ctk.CTkLabel(
            self._target_frame,
            text="대상 텍스트: (설정되지 않음)",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self._target_label.pack(fill="x", padx=10, pady=10)

        # ── 설정 패널 placeholder ──
        self._settings_placeholder = ctk.CTkFrame(self, height=150)
        self._settings_placeholder.pack(fill="both", padx=10, pady=4, expand=False)
        self._settings_placeholder.pack_propagate(False)

        ctk.CTkLabel(
            self._settings_placeholder,
            text="⚙️ 설정 패널 (Step 9에서 구현)",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(expand=True)

        # ── 컨트롤 패널 (실제 연결) ──
        self._control_panel = ControlPanel(
            self,
            get_target_text=lambda: self._target_text,
        )
        self._control_panel.pack(fill="both", padx=10, pady=(4, 8), expand=True)

    # ── 이벤트 핸들러 ──

    def _on_text_selected(self, raw_text: str):
        """입력 패널에서 '이 텍스트 사용' 클릭 시 호출."""
        # 전처리 적용
        text = preprocess(raw_text, self._preprocess_config)
        self._target_text = text

        # 대상 텍스트 표시 업데이트
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
        """Always on Top 토글."""
        self._always_on_top = self._aot_var.get()
        self.attributes("-topmost", self._always_on_top)

    def _on_closing(self):
        """윈도우 닫기 시 정리."""
        self._control_panel.destroy()
        self.destroy()

    # ── 외부 인터페이스 ──

    @property
    def target_text(self) -> str:
        return self._target_text

    def get_input_panel(self) -> InputPanel:
        return self._input_panel

    def get_control_panel(self) -> ControlPanel:
        return self._control_panel
