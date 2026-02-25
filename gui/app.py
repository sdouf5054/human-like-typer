"""
메인 윈도우 — 경량 유틸리티 스타일.

레이아웃:
1. 상단바: 프리셋 + ⚙ 설정 + 💾 저장 + 📌 AOT
2. 입력 소스 (InputPanel)
3. 대상 텍스트 표시
4. 컨트롤 + 로그 (가장 크게)
"""

import customtkinter as ctk

from gui.input_panel import InputPanel
from gui.settings_panel import SettingsWindow
from gui.control_panel import ControlPanel
from core.clipboard import get_clipboard_text
from core.text_preprocessor import preprocess, PreprocessConfig
from core.timing_model import TimingConfig
from core.typo_model import TypoConfig
from preset_manager import (
    PresetManager, preset_to_configs, configs_to_preset,
    load_app_config, save_app_config,
)


class App(ctk.CTk):
    """Human-Like Typer 메인 윈도우."""

    def __init__(self):
        super().__init__()
        self.title("Human-Like Typer v1.0")
        self.geometry("700x680")
        self.minsize(550, 480)

        self._target_text = ""
        self._preset_mgr = PresetManager()
        self._app_config = load_app_config()
        self._settings_win: SettingsWindow | None = None

        self._build_ui()
        self._init_settings_window()
        self._load_last_preset()

        aot = self._app_config.get("window", {}).get("always_on_top", False)
        if aot:
            self._aot_var.set(True)
            self.attributes("-topmost", True)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        # ── 상단바 ──
        topbar = ctk.CTkFrame(self, height=38)
        topbar.pack(fill="x", padx=8, pady=(6, 3))
        topbar.pack_propagate(False)

        ctk.CTkLabel(topbar, text="프리셋:", font=ctk.CTkFont(size=11)
                      ).pack(side="left", padx=(6, 3))

        preset_names = self._preset_mgr.list_all_display_names()
        self._preset_dd = ctk.CTkOptionMenu(
            topbar, values=preset_names or ["(없음)"],
            width=180, height=26, font=ctk.CTkFont(size=11),
            command=self._on_preset_selected,
        )
        self._preset_dd.pack(side="left", padx=3)

        ctk.CTkButton(topbar, text="⚙ 설정", width=65, height=26,
                       font=ctk.CTkFont(size=11),
                       command=self._open_settings).pack(side="left", padx=3)

        ctk.CTkButton(topbar, text="💾 저장", width=55, height=26,
                       font=ctk.CTkFont(size=11),
                       command=self._on_save_custom).pack(side="left", padx=3)

        self._aot_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(topbar, text="📌 AOT", variable=self._aot_var,
                       font=ctk.CTkFont(size=10), command=self._toggle_aot,
                       onvalue=True, offvalue=False, width=30
                       ).pack(side="right", padx=(3, 6))

        # ── 입력 소스 ──
        self._input_panel = InputPanel(self, on_text_selected=self._on_text_selected)
        self._input_panel.pack(fill="both", padx=8, pady=3, expand=False)

        # ── 대상 텍스트 ──
        tf = ctk.CTkFrame(self, height=36)
        tf.pack(fill="x", padx=8, pady=3)
        tf.pack_propagate(False)
        self._target_label = ctk.CTkLabel(
            tf, text="대상 텍스트: (설정되지 않음)",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w",
        )
        self._target_label.pack(fill="x", padx=8, pady=6)

        # ── 컨트롤 + 로그 (메인 영역) ──
        self._control_panel = ControlPanel(
            self,
            get_target_text=lambda: self._target_text,
            get_settings=self._get_current_settings,
            on_auto_clip_start=self._auto_clipboard_read,
        )
        self._control_panel.pack(fill="both", padx=8, pady=(3, 6), expand=True)

    # ── 자동 클립보드 콜백 ──

    def _auto_clipboard_read(self) -> str:
        """
        자동 클립보드 모드: 클립보드를 읽고 전처리 후 대상 텍스트로 설정.
        ControlPanel에서 트리거 시 호출됨.
        반환값이 타이핑 대상 텍스트.
        """
        raw = get_clipboard_text()
        if not raw:
            return ""
        prep_cfg = self._settings_win.get_preprocess_config() if self._settings_win else PreprocessConfig()
        text = preprocess(raw, prep_cfg)
        if text:
            self._target_text = text
            preview = text[:50].replace('\n', '↵')
            sfx = "..." if len(text) > 50 else ""
            self._target_label.configure(
                text=f"대상: \"{preview}{sfx}\" ({len(text)}자) [자동 클립보드]",
                text_color=("gray10", "gray90"),
            )
        return text

    # ── 설정 창 ──

    def _init_settings_window(self):
        """설정 창을 미리 생성 (숨긴 상태)."""
        self._settings_win = SettingsWindow(self, on_config_changed=self._on_settings_changed)
        self._settings_win.withdraw()

    def _open_settings(self):
        """설정 창 표시."""
        if self._settings_win is None or not self._settings_win.winfo_exists():
            self._settings_win = SettingsWindow(self, on_config_changed=self._on_settings_changed)
        else:
            self._settings_win.deiconify()
            self._settings_win.lift()

    # ── 프리셋 ──

    def _load_last_preset(self):
        name = self._app_config.get("last_preset", "default")
        is_custom = self._app_config.get("last_preset_custom", False)
        data = self._preset_mgr.load(name, custom=is_custom)
        if data:
            self._apply_preset(data)
            display = data.get("preset_name", name)
            if is_custom:
                display = f"[커스텀] {display}"
            try:
                self._preset_dd.set(display)
            except Exception:
                pass

    def _on_preset_selected(self, display_name):
        result = self._preset_mgr.find_by_display_name(display_name)
        if not result:
            return
        name, is_custom = result
        data = self._preset_mgr.load(name, custom=is_custom)
        if data:
            self._apply_preset(data)
            self._app_config["last_preset"] = name
            self._app_config["last_preset_custom"] = is_custom
            save_app_config(self._app_config)

    def _apply_preset(self, data):
        timing, typo, control, prep = preset_to_configs(data)
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.set_timing_config(timing)
            self._settings_win.set_typo_config(typo)
            if control.get("precise_mode", False):
                self._settings_win._input_mode_var.set("precise")
            else:
                self._settings_win._input_mode_var.set("simple")

        cd = control.get("countdown_seconds", 3)
        self._control_panel.set_countdown(cd)
        focus = control.get("focus_monitor_enabled", True)
        self._control_panel.set_focus_monitor(focus)

    def _on_save_custom(self):
        dialog = ctk.CTkInputDialog(text="커스텀 프리셋 이름:", title="프리셋 저장")
        name = dialog.get_input()
        if not name or not name.strip():
            return
        timing = self._settings_win.get_timing_config()
        typo = self._settings_win.get_typo_config()
        precise = self._settings_win.is_precise_mode()
        control = {
            "precise_mode": precise,
            "countdown_seconds": self._control_panel.get_countdown(),
            "focus_monitor_enabled": self._control_panel.get_focus_monitor(),
        }
        prep = self._settings_win.get_preprocess_config()
        data = configs_to_preset(name.strip(), "사용자 커스텀", timing, typo, control, prep)
        self._preset_mgr.save_custom(name.strip().replace(" ", "_"), data)
        names = self._preset_mgr.list_all_display_names()
        self._preset_dd.configure(values=names)
        self._preset_dd.set(f"[커스텀] {name.strip()}")

    # ── 이벤트 ──

    def _on_text_selected(self, raw_text):
        prep_cfg = self._settings_win.get_preprocess_config() if self._settings_win else PreprocessConfig()
        text = preprocess(raw_text, prep_cfg)
        self._target_text = text
        if text:
            preview = text[:50].replace('\n', '↵')
            sfx = "..." if len(text) > 50 else ""
            self._target_label.configure(
                text=f"대상: \"{preview}{sfx}\" ({len(text)}자)",
                text_color=("gray10", "gray90"),
            )
        else:
            self._target_label.configure(text="대상 텍스트: (비어있음)", text_color="gray")

    def _toggle_aot(self):
        val = self._aot_var.get()
        self.attributes("-topmost", val)
        self._app_config.setdefault("window", {})["always_on_top"] = val
        save_app_config(self._app_config)

    def _on_settings_changed(self):
        if self._settings_win:
            timing = self._settings_win.get_timing_config()
            self._input_panel.update_base_delay(timing.base_delay_ms)

    def _get_current_settings(self) -> tuple:
        if self._settings_win and self._settings_win.winfo_exists():
            return (
                self._settings_win.get_timing_config(),
                self._settings_win.get_typo_config(),
                self._settings_win.is_precise_mode(),
                self._control_panel.get_focus_monitor(),
            )
        return (TimingConfig(), TypoConfig(), False, True)

    def _on_closing(self):
        save_app_config(self._app_config)
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.destroy()
        self._control_panel.destroy()
        self.destroy()
