"""
메인 윈도우 — 전체 레이아웃 조합 + 프리셋 + config 자동 저장.

레이아웃:
1. 상단바: 프리셋 드롭다운 + 커스텀 저장 + Always on Top
2. 입력 소스 패널 (InputPanel)
3. 대상 텍스트 표시
4. 설정 패널 (SettingsPanel)
5. 컨트롤 패널 (ControlPanel)
"""

import customtkinter as ctk

from gui.input_panel import InputPanel
from gui.control_panel import ControlPanel
from gui.settings_panel import SettingsPanel
from core.text_preprocessor import preprocess, PreprocessConfig
from preset_manager import (
    PresetManager, preset_to_configs, configs_to_preset,
    load_app_config, save_app_config,
)


class App(ctk.CTk):
    """Human-Like Typer 메인 윈도우."""

    def __init__(self):
        super().__init__()

        self.title("Human-Like Typer v1.0")
        self.geometry("750x900")
        self.minsize(600, 550)

        # 상태
        self._target_text: str = ""
        self._always_on_top = False
        self._preprocess_config = PreprocessConfig()

        # 프리셋 매니저
        self._preset_mgr = PresetManager()
        self._app_config = load_app_config()

        self._build_ui()
        self._load_last_preset()

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

        preset_names = self._preset_mgr.list_all_display_names()
        self._preset_dropdown = ctk.CTkOptionMenu(
            topbar, values=preset_names if preset_names else ["(없음)"],
            width=200, height=28,
            font=ctk.CTkFont(size=11),
            command=self._on_preset_selected,
        )
        self._preset_dropdown.pack(side="left", padx=4)

        ctk.CTkButton(
            topbar, text="💾 저장", width=60, height=28,
            font=ctk.CTkFont(size=11),
            command=self._on_save_custom,
        ).pack(side="left", padx=4)

        # Always on Top
        self._aot_var = ctk.BooleanVar(value=self._app_config.get("window", {}).get("always_on_top", False))
        ctk.CTkSwitch(
            topbar, text="📌 Always on Top",
            variable=self._aot_var,
            font=ctk.CTkFont(size=11),
            command=self._toggle_always_on_top,
            onvalue=True, offvalue=False, width=40,
        ).pack(side="right", padx=(4, 8))

        # 초기 always on top 적용
        if self._aot_var.get():
            self.attributes("-topmost", True)

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
            self, on_settings_changed=self._on_settings_changed,
        )
        self._settings_panel.pack(fill="both", padx=10, pady=4, expand=True)

        # ── 컨트롤 패널 ──
        self._control_panel = ControlPanel(
            self,
            get_target_text=lambda: self._target_text,
            get_settings=self._get_current_settings,
        )
        self._control_panel.pack(fill="both", padx=10, pady=(4, 8), expand=True)

    # ── 프리셋 ──

    def _load_last_preset(self):
        """앱 시작 시 마지막 사용 프리셋 로드."""
        name = self._app_config.get("last_preset", "default")
        is_custom = self._app_config.get("last_preset_custom", False)
        data = self._preset_mgr.load(name, custom=is_custom)
        if data:
            self._apply_preset(data)
            # 드롭다운도 맞춰주기
            display = data.get("preset_name", name)
            if is_custom:
                display = f"[커스텀] {display}"
            try:
                self._preset_dropdown.set(display)
            except Exception:
                pass

    def _on_preset_selected(self, display_name: str):
        """프리셋 드롭다운에서 선택."""
        result = self._preset_mgr.find_by_display_name(display_name)
        if result is None:
            return
        name, is_custom = result
        data = self._preset_mgr.load(name, custom=is_custom)
        if data:
            self._apply_preset(data)
            # config.json에 마지막 프리셋 저장
            self._app_config["last_preset"] = name
            self._app_config["last_preset_custom"] = is_custom
            save_app_config(self._app_config)

    def _apply_preset(self, data: dict):
        """프리셋 데이터를 설정 패널에 적용."""
        timing, typo, control, prep = preset_to_configs(data)
        self._settings_panel.apply_config(timing, typo, control)
        self._preprocess_config = prep
        # 컨트롤 패널에 카운트다운/포커스 반영
        countdown = control.get("countdown_seconds", 3)
        self._control_panel.set_countdown(countdown)
        focus_enabled = control.get("focus_monitor_enabled", True)
        self._control_panel.set_focus_monitor(focus_enabled)

    def _on_save_custom(self):
        """현재 설정을 커스텀 프리셋으로 저장."""
        dialog = ctk.CTkInputDialog(
            text="커스텀 프리셋 이름을 입력하세요:",
            title="프리셋 저장",
        )
        name = dialog.get_input()
        if not name or not name.strip():
            return

        timing = self._settings_panel.get_timing_config()
        typo = self._settings_panel.get_typo_config()
        precise = self._settings_panel.get_precise_mode()
        control = {
            "precise_mode": precise,
            "countdown_seconds": self._control_panel.get_countdown(),
            "focus_monitor_enabled": self._control_panel.get_focus_monitor(),
        }

        data = configs_to_preset(
            name.strip(), "사용자 커스텀 프리셋",
            timing, typo, control, self._preprocess_config,
        )
        # 파일명은 이름에서 공백→_ 변환
        file_name = name.strip().replace(" ", "_")
        self._preset_mgr.save_custom(file_name, data)

        # 드롭다운 갱신
        self._refresh_preset_dropdown()

    def _refresh_preset_dropdown(self):
        """프리셋 드롭다운 목록 갱신."""
        names = self._preset_mgr.list_all_display_names()
        self._preset_dropdown.configure(values=names if names else ["(없음)"])

    # ── 이벤트 핸들러 ──

    def _on_text_selected(self, raw_text: str):
        text = preprocess(raw_text, self._preprocess_config)
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
        self._app_config.setdefault("window", {})["always_on_top"] = self._always_on_top
        save_app_config(self._app_config)

    def _on_settings_changed(self):
        timing = self._settings_panel.get_timing_config()
        self._input_panel.update_base_delay(timing.base_delay_ms)

    def _get_current_settings(self) -> tuple:
        return (
            self._settings_panel.get_timing_config(),
            self._settings_panel.get_typo_config(),
            self._settings_panel.get_precise_mode(),
        )

    def _on_closing(self):
        save_app_config(self._app_config)
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

    def get_settings_panel(self) -> SettingsPanel:
        return self._settings_panel
