"""
프리셋 매니저 — 기본 프리셋 4개 + 커스텀 프리셋 저장/불러오기 + config.json.

파일 구조:
    presets/
        default.json
        fast_accurate.json
        slow_natural.json
        sloppy_beginner.json
        custom/          ← 사용자 저장
            my_preset.json
    config.json          ← 마지막 프리셋, 창 설정 등
"""

import json
import os
from pathlib import Path
from dataclasses import asdict

from core.timing_model import TimingConfig
from core.typo_model import TypoConfig
from core.text_preprocessor import PreprocessConfig


# ============================================================
# 경로
# ============================================================

_BASE_DIR = Path(__file__).parent
PRESETS_DIR = _BASE_DIR / "presets"
CUSTOM_DIR = PRESETS_DIR / "custom"
CONFIG_PATH = _BASE_DIR / "config.json"

# 커스텀 폴더 보장
CUSTOM_DIR.mkdir(parents=True, exist_ok=True)

# 기본 프리셋 파일명 → 표시 이름
BUILTIN_PRESETS = {
    "default":         "기본 (Default)",
    "fast_accurate":   "빠르고 정확한",
    "slow_natural":    "느리고 자연스러운",
    "sloppy_beginner": "오타 많은 초보",
}


# ============================================================
# 프리셋 ↔ Config 변환
# ============================================================

def preset_to_configs(data: dict) -> tuple[TimingConfig, TypoConfig, dict, PreprocessConfig]:
    """프리셋 JSON dict → (TimingConfig, TypoConfig, control_dict, PreprocessConfig)."""
    timing = TimingConfig(**data.get("timing", {}))
    typo = TypoConfig(**data.get("typo", {}))
    control = data.get("control", {})
    prep = PreprocessConfig(**data.get("preprocessing", {}))
    return timing, typo, control, prep


def configs_to_preset(
    name: str, description: str,
    timing: TimingConfig, typo: TypoConfig,
    control: dict, prep: PreprocessConfig,
) -> dict:
    """Config 객체들 → 프리셋 JSON dict."""
    return {
        "preset_name": name,
        "preset_description": description,
        "timing": asdict(timing),
        "typo": asdict(typo),
        "control": control,
        "preprocessing": asdict(prep),
    }


# ============================================================
# 프리셋 매니저
# ============================================================

class PresetManager:
    """프리셋 로드/저장/목록 관리."""

    def list_builtin(self) -> list[tuple[str, str]]:
        """기본 프리셋 목록: [(파일명, 표시이름), ...]."""
        return [(k, v) for k, v in BUILTIN_PRESETS.items()]

    def list_custom(self) -> list[tuple[str, str]]:
        """커스텀 프리셋 목록: [(파일명, 표시이름), ...]."""
        result = []
        for f in sorted(CUSTOM_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                display = data.get("preset_name", f.stem)
            except Exception:
                display = f.stem
            result.append((f.stem, f"[커스텀] {display}"))
        return result

    def list_all_display_names(self) -> list[str]:
        """드롭다운용 표시 이름 리스트."""
        names = [v for _, v in self.list_builtin()]
        names += [v for _, v in self.list_custom()]
        return names

    def find_by_display_name(self, display: str) -> tuple[str, bool] | None:
        """표시 이름 → (파일명, is_custom). 없으면 None."""
        for fname, dname in self.list_builtin():
            if dname == display:
                return fname, False
        for fname, dname in self.list_custom():
            if dname == display:
                return fname, True
        return None

    def load(self, name: str, custom: bool = False) -> dict | None:
        """프리셋 로드. custom=True면 custom/ 폴더에서."""
        if custom:
            path = CUSTOM_DIR / f"{name}.json"
        else:
            path = PRESETS_DIR / f"{name}.json"

        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def save_custom(self, name: str, data: dict):
        """커스텀 프리셋 저장."""
        path = CUSTOM_DIR / f"{name}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def delete_custom(self, name: str) -> bool:
        """커스텀 프리셋 삭제."""
        path = CUSTOM_DIR / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False


# ============================================================
# config.json 관리
# ============================================================

def load_app_config() -> dict:
    """config.json 로드. 없으면 기본값."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "last_preset": "default",
        "last_preset_custom": False,
        "window": {"always_on_top": False},
    }


def save_app_config(cfg: dict):
    """config.json 저장."""
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================
# 테스트
# ============================================================

if __name__ == "__main__":
    mgr = PresetManager()

    print("=== 기본 프리셋 ===")
    for fname, dname in mgr.list_builtin():
        data = mgr.load(fname)
        if data:
            print(f"  {dname}: timing keys={list(data.get('timing', {}).keys())}")
        else:
            print(f"  {dname}: (파일 없음)")

    print(f"\n=== 커스텀 프리셋 ===")
    customs = mgr.list_custom()
    print(f"  {len(customs)}개")

    print(f"\n=== 드롭다운 ===")
    print(f"  {mgr.list_all_display_names()}")

    print(f"\n=== config.json ===")
    cfg = load_app_config()
    print(f"  {cfg}")
