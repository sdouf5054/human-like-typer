"""
오타 모델 — 각 글자에 대해 오타 발생 여부를 판정하고,
오타 발생 시 Action 시퀀스(오타 입력 → 인지 → 수정)를 생성.

오타 유형 3종:
1. 인접 키 (Adjacent Key) — QWERTY 기준 물리적 인접 키로 대체
2. 글자 전치 (Transposition) — 연속 두 글자 순서 교환
3. 이중 입력 (Double Strike) — 같은 키 실수로 두 번

수정 시퀀스:
- 인지 딜레이 (오타를 알아채는 시간)
- Burst backspace (빠른 연타로 삭제)
- Retype 준비 딜레이 (손가락 재정렬)
- 올바른 글자 재입력
"""

import random
from dataclasses import dataclass
from enum import Enum
from core.keyboard_map import get_adjacent_keys


# ============================================================
# Action 타입 정의
# ============================================================

class ActionType(Enum):
    TYPE = "type"              # 글자 입력
    BACKSPACE = "backspace"    # 백스페이스 (count 지정)
    PAUSE = "pause"            # 딜레이 대기 (duration_ms 지정)


@dataclass
class Action:
    """타이핑 엔진이 실행할 단일 동작."""
    action_type: ActionType
    char: str = ""             # TYPE 시 입력할 문자
    count: int = 1             # BACKSPACE 시 횟수
    duration_ms: float = 0.0   # PAUSE 시 대기 시간 (ms)
    label: str = ""            # 로그용 라벨 (예: "오타", "수정", "인지 딜레이")

    def __repr__(self):
        if self.action_type == ActionType.TYPE:
            return f"Type('{self.char}', {self.label})"
        elif self.action_type == ActionType.BACKSPACE:
            return f"Backspace(×{self.count})"
        elif self.action_type == ActionType.PAUSE:
            return f"Pause({self.duration_ms:.0f}ms, {self.label})"
        return f"Action({self.action_type})"


# ============================================================
# 오타 설정
# ============================================================

@dataclass
class TypoConfig:
    """오타 모델의 모든 파라미터. GUI 입력/토글과 1:1 대응."""

    # 오타 확률 (만분율: 30 = 0.30%)
    typo_prob: int = 30
    # 오타 수정 확률 (백분율: 85 = 85%)
    typo_revision_prob: int = 85

    # 오타 유형 토글
    adjacent_key_enabled: bool = True
    transposition_enabled: bool = False
    double_strike_enabled: bool = False

    @property
    def actual_typo_prob(self) -> float:
        return self.typo_prob / 10000

    @property
    def actual_revision_prob(self) -> float:
        return self.typo_revision_prob / 100

    @property
    def enabled_types(self) -> list[str]:
        """활성화된 오타 유형 리스트."""
        types = []
        if self.adjacent_key_enabled:
            types.append("adjacent")
        if self.transposition_enabled:
            types.append("transposition")
        if self.double_strike_enabled:
            types.append("double_strike")
        return types


# ============================================================
# 오타 모델
# ============================================================

class TypoModel:
    """글자별 오타 발생 판정 및 Action 시퀀스 생성."""

    def __init__(self, config: TypoConfig | None = None):
        self.config = config or TypoConfig()

        # 통계 추적
        self.stats = {
            "total_chars": 0,
            "typos": 0,
            "adjacent": 0,
            "transposition": 0,
            "double_strike": 0,
            "revised": 0,
            "unrevised": 0,
        }

    def reset_stats(self):
        """통계 초기화."""
        for key in self.stats:
            self.stats[key] = 0

    def process_char(
        self,
        char: str,
        prev_char: str | None,
        next_char: str | None,
    ) -> tuple[list[Action], bool]:
        """
        단일 글자에 대해 오타 판정 및 Action 시퀀스를 생성.

        Args:
            char: 현재 입력할 문자
            prev_char: 직전 문자 (첫 글자면 None)
            next_char: 다음 문자 (마지막 글자면 None)

        Returns:
            (actions, skip_next)
            - actions: 실행할 Action 리스트
            - skip_next: True이면 다음 글자를 건너뜀 (전치 오타 시)
        """
        self.stats["total_chars"] += 1
        cfg = self.config

        # 활성화된 오타 유형이 없으면 정상 입력
        enabled = cfg.enabled_types
        if not enabled:
            return [Action(ActionType.TYPE, char=char, label="정상")], False

        # 오타 발생 여부 판정
        if random.random() >= cfg.actual_typo_prob:
            return [Action(ActionType.TYPE, char=char, label="정상")], False

        # 오타 유형 선택
        typo_type = random.choice(enabled)

        if typo_type == "adjacent":
            return self._adjacent_typo(char, cfg)
        elif typo_type == "transposition":
            return self._transposition_typo(char, next_char, cfg)
        elif typo_type == "double_strike":
            return self._double_strike_typo(char, cfg)

        # fallback
        return [Action(ActionType.TYPE, char=char, label="정상")], False

    def _adjacent_typo(
        self, char: str, cfg: TypoConfig
    ) -> tuple[list[Action], bool]:
        """인접 키 오타: 옆 키를 대신 누름."""
        neighbors = get_adjacent_keys(char)
        if not neighbors:
            # 인접 키가 없는 경우 (거의 없음) → 정상 입력
            return [Action(ActionType.TYPE, char=char, label="정상")], False

        wrong_char = random.choice(neighbors)
        actions: list[Action] = []
        self.stats["typos"] += 1
        self.stats["adjacent"] += 1

        # 오타 글자 입력
        actions.append(Action(ActionType.TYPE, char=wrong_char, label=f"오타(원래:{char})"))

        # 수정 여부 판정
        if random.random() < cfg.actual_revision_prob:
            self.stats["revised"] += 1
            # 인지 딜레이 (100~300ms)
            actions.append(Action(
                ActionType.PAUSE,
                duration_ms=max(30, random.gauss(200, 50)),
                label="인지 딜레이"
            ))
            # Backspace (burst)
            actions.append(Action(ActionType.BACKSPACE, count=1))
            # Retype 준비 딜레이 (50~150ms)
            actions.append(Action(
                ActionType.PAUSE,
                duration_ms=max(20, random.gauss(100, 30)),
                label="retype 준비"
            ))
            # 올바른 글자 입력
            actions.append(Action(ActionType.TYPE, char=char, label="수정"))
        else:
            self.stats["unrevised"] += 1

        return actions, False

    def _transposition_typo(
        self, char: str, next_char: str | None, cfg: TypoConfig
    ) -> tuple[list[Action], bool]:
        """글자 전치 오타: 연속 두 글자의 순서가 뒤바뀜."""
        # 다음 글자가 없으면 전치 불가 → 정상 입력
        if next_char is None:
            return [Action(ActionType.TYPE, char=char, label="정상")], False

        actions: list[Action] = []
        self.stats["typos"] += 1
        self.stats["transposition"] += 1

        # 뒤바뀐 순서로 입력
        actions.append(Action(ActionType.TYPE, char=next_char, label=f"전치(원래:{char}{next_char})"))
        actions.append(Action(ActionType.TYPE, char=char, label="전치"))

        # 수정 여부 판정
        if random.random() < cfg.actual_revision_prob:
            self.stats["revised"] += 1
            # 인지 딜레이 (150~400ms, 전치는 인지 더 오래 걸림)
            actions.append(Action(
                ActionType.PAUSE,
                duration_ms=max(50, random.gauss(275, 60)),
                label="인지 딜레이"
            ))
            # Backspace × 2 (burst)
            actions.append(Action(ActionType.BACKSPACE, count=2))
            # Retype 준비 딜레이 (50~150ms)
            actions.append(Action(
                ActionType.PAUSE,
                duration_ms=max(20, random.gauss(100, 30)),
                label="retype 준비"
            ))
            # 올바른 순서로 재입력
            actions.append(Action(ActionType.TYPE, char=char, label="수정"))
            actions.append(Action(ActionType.TYPE, char=next_char, label="수정"))
        else:
            self.stats["unrevised"] += 1

        # skip_next = True (다음 글자는 이미 처리됨)
        return actions, True

    def _double_strike_typo(
        self, char: str, cfg: TypoConfig
    ) -> tuple[list[Action], bool]:
        """이중 입력 오타: 같은 키를 실수로 두 번 누름."""
        actions: list[Action] = []
        self.stats["typos"] += 1
        self.stats["double_strike"] += 1

        # 정상 입력 + 이중 입력
        actions.append(Action(ActionType.TYPE, char=char, label="정상"))
        actions.append(Action(ActionType.TYPE, char=char, label=f"이중입력(실수)"))

        # 수정 여부 판정
        if random.random() < cfg.actual_revision_prob:
            self.stats["revised"] += 1
            # 인지 딜레이 (80~200ms, 이중 입력은 빨리 알아챔)
            actions.append(Action(
                ActionType.PAUSE,
                duration_ms=max(30, random.gauss(140, 40)),
                label="인지 딜레이"
            ))
            # Backspace × 1
            actions.append(Action(ActionType.BACKSPACE, count=1))
            # Retype 준비 딜레이 (30~80ms, 같은 위치이므로 짧음)
            actions.append(Action(
                ActionType.PAUSE,
                duration_ms=max(15, random.gauss(55, 15)),
                label="retype 준비"
            ))
        else:
            self.stats["unrevised"] += 1

        return actions, False

    def process_text(self, text: str) -> list[tuple[int, str, list[Action]]]:
        """
        텍스트 전체에 대해 오타 판정을 일괄 수행 (드라이런/테스트용).

        Returns:
            [(index, original_char, actions), ...] 리스트
        """
        results = []
        i = 0
        while i < len(text):
            char = text[i]
            prev_char = text[i - 1] if i > 0 else None
            next_char = text[i + 1] if i < len(text) - 1 else None

            actions, skip_next = self.process_char(char, prev_char, next_char)
            results.append((i, char, actions))

            if skip_next:
                i += 2  # 전치 오타: 다음 글자 건너뜀
            else:
                i += 1

        return results


# ============================================================
# 테스트 / 검증용
# ============================================================

def _format_char(c: str) -> str:
    if c == ' ':
        return '␣'
    elif c == '\n':
        return '↵'
    elif c == '\t':
        return '⇥'
    return c


if __name__ == "__main__":
    print("=" * 65)
    print("오타 모델 테스트")
    print("=" * 65)

    test_text = "The quick brown fox jumps over the lazy dog."

    # ── 단일 실행 상세 출력 ──
    print(f"\n텍스트: {repr(test_text)}")
    print(f"글자 수: {len(test_text)}")

    # 오타를 잘 볼 수 있게 높은 확률로 설정
    config_demo = TypoConfig(
        typo_prob=1500,         # 15% (데모용 높은 확률)
        typo_revision_prob=80,
        adjacent_key_enabled=True,
        transposition_enabled=True,
        double_strike_enabled=True,
    )
    model_demo = TypoModel(config_demo)
    results = model_demo.process_text(test_text)

    print(f"\n{'idx':>3}  {'문자':>4}  Actions")
    print("-" * 65)
    for idx, char, actions in results:
        action_str = " → ".join(repr(a) for a in actions)
        has_typo = any(a.label and "오타" in a.label or "전치" in a.label or "이중" in a.label
                       for a in actions)
        marker = " ⚠️" if has_typo else ""
        print(f"{idx:3d}  {_format_char(char):>4}  {action_str}{marker}")

    print(f"\n단일 실행 통계: {model_demo.stats}")

    # ── 100회 반복 통계 ──
    print(f"\n{'=' * 65}")
    print("100회 반복 통계 (3가지 설정)")
    print(f"{'=' * 65}")

    configs = {
        "기본 (0.30%, adj만)": TypoConfig(
            typo_prob=30, typo_revision_prob=85,
            adjacent_key_enabled=True,
            transposition_enabled=False,
            double_strike_enabled=False,
        ),
        "중간 (2%, 3종 모두)": TypoConfig(
            typo_prob=200, typo_revision_prob=85,
            adjacent_key_enabled=True,
            transposition_enabled=True,
            double_strike_enabled=True,
        ),
        "높음 (5%, 3종 모두)": TypoConfig(
            typo_prob=500, typo_revision_prob=70,
            adjacent_key_enabled=True,
            transposition_enabled=True,
            double_strike_enabled=True,
        ),
    }

    for name, cfg in configs.items():
        total_stats = {
            "total_chars": 0, "typos": 0,
            "adjacent": 0, "transposition": 0, "double_strike": 0,
            "revised": 0, "unrevised": 0,
        }

        for _ in range(100):
            m = TypoModel(cfg)
            m.process_text(test_text)
            for key in total_stats:
                total_stats[key] += m.stats[key]

        tc = total_stats["total_chars"]
        tp = total_stats["typos"]
        rate = (tp / tc * 100) if tc > 0 else 0
        adj = total_stats["adjacent"]
        trans = total_stats["transposition"]
        dbl = total_stats["double_strike"]
        rev = total_stats["revised"]
        unrev = total_stats["unrevised"]

        print(f"\n  [{name}]")
        print(f"    총 글자: {tc}  |  오타: {tp} ({rate:.2f}%)")
        print(f"    유형 — 인접키: {adj}  전치: {trans}  이중입력: {dbl}")
        print(f"    수정: {rev}  미수정: {unrev}")

    # ── 확률 정확도 검증 ──
    print(f"\n{'=' * 65}")
    print("확률 정확도 검증 (typo_prob=300 → 기대 3.00%)")
    print(f"{'=' * 65}")

    cfg_verify = TypoConfig(
        typo_prob=300,
        typo_revision_prob=50,
        adjacent_key_enabled=True,
    )
    total_chars = 0
    total_typos = 0
    for _ in range(1000):
        m = TypoModel(cfg_verify)
        m.process_text(test_text)
        total_chars += m.stats["total_chars"]
        total_typos += m.stats["typos"]

    actual_rate = total_typos / total_chars * 100
    print(f"  1000회 × {len(test_text)}글자 = {total_chars}글자 처리")
    print(f"  오타 {total_typos}회 → 실측 {actual_rate:.2f}% (기대 3.00%)")
