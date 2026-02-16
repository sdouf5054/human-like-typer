"""
타이밍 모델 — 각 글자 입력 전 딜레이(ms)를 계산.

8가지 요소를 파이프라인으로 순차 적용:
1. 기본 딜레이 (가우시안)
2. 개행/문단 경계 pause
3. 단어 경계 (inter-word / intra-word)
4. 구두점 pause
5. Shift 패널티
6. 동일 글자 연속 가속
7. 버스트 타이핑 micro-pause
8. 타이핑 피로 (fatigue)

각 요소의 기여분을 breakdown dict로 기록하여 로그/시각화에 활용.
"""

import random
from dataclasses import dataclass, field
from core.keyboard_map import SHIFT_CHARS


@dataclass
class TimingConfig:
    """타이밍 모델의 모든 파라미터. GUI 슬라이더/토글과 1:1 대응."""

    # 기본 딜레이
    base_delay_ms: int = 70
    delay_variance_ms: int = 30

    # 단어 경계
    word_boundary_enabled: bool = True
    intra_word_speed_factor: float = 0.8
    inter_word_pause_ms: int = 120

    # 구두점 pause
    punctuation_pause_enabled: bool = True
    punctuation_pause_ms: int = 200

    # 개행/문단 경계 pause
    newline_pause_enabled: bool = True
    newline_pause_ms: int = 400

    # Shift 패널티
    shift_penalty_enabled: bool = True
    shift_penalty_ms: int = 25

    # 동일 글자 연속 가속
    double_letter_enabled: bool = False
    double_letter_speed_factor: float = 0.6

    # 버스트 타이핑
    burst_enabled: bool = False
    burst_length_min: int = 2
    burst_length_max: int = 5
    burst_pause_ms: int = 40

    # 피로
    fatigue_enabled: bool = False
    fatigue_factor: float = 0.05


PUNCTUATION_CHARS = set('.,!?:;')


class TimingModel:
    """글자별 딜레이를 계산하는 타이밍 엔진."""

    def __init__(self, config: TimingConfig | None = None):
        self.config = config or TimingConfig()
        self._burst_counter = 0
        self._burst_size = 0
        self._reset_burst()

    def _reset_burst(self):
        """버스트 카운터 초기화. 새 텍스트 시작 시 호출."""
        self._burst_counter = 0
        cfg = self.config
        self._burst_size = random.randint(cfg.burst_length_min, cfg.burst_length_max)

    def _check_burst_boundary(self) -> bool:
        """현재 글자가 버스트 경계인지 판정하고, 경계면 다음 버스트 길이 재설정."""
        self._burst_counter += 1
        if self._burst_counter >= self._burst_size:
            self._burst_counter = 0
            cfg = self.config
            self._burst_size = random.randint(cfg.burst_length_min, cfg.burst_length_max)
            return True
        return False

    def reset(self):
        """새 텍스트 타이핑 시작 전 내부 상태 초기화."""
        self._reset_burst()

    def calculate_delay(
        self,
        char: str,
        prev_char: str | None,
        index: int,
        total_length: int,
    ) -> tuple[float, dict]:
        """
        단일 글자에 대한 딜레이(ms)와 breakdown을 계산.

        Args:
            char: 현재 입력할 문자
            prev_char: 직전에 입력한 문자 (첫 글자면 None)
            index: 현재 글자의 인덱스 (0-based)
            total_length: 전체 텍스트 길이

        Returns:
            (delay_ms, breakdown_dict)
            breakdown_dict: 각 요소별 기여분 기록
        """
        cfg = self.config
        breakdown: dict = {}

        # ── 1. 기본 딜레이 (가우시안) ──
        delay = cfg.base_delay_ms + random.gauss(0, cfg.delay_variance_ms / 2)
        breakdown['base'] = round(delay, 1)

        # ── 2. 개행/문단 경계 (word boundary보다 우선) ──
        if cfg.newline_pause_enabled and prev_char == '\n':
            add = cfg.newline_pause_ms * (1 + random.gauss(0, 0.3))
            add = max(0, add)
            delay += add
            breakdown['newline'] = round(add, 1)

        # ── 3. 단어 경계 (개행이 아닐 때만) ──
        elif cfg.word_boundary_enabled:
            if prev_char == ' ':
                # 새 단어 시작 → 느리게
                add = cfg.inter_word_pause_ms * (1 + random.gauss(0, 0.2))
                add = max(0, add)
                delay += add
                breakdown['inter_word'] = round(add, 1)
            elif prev_char is not None and prev_char != ' ' and char != ' ':
                # 단어 내부 → 빠르게
                delay *= cfg.intra_word_speed_factor
                breakdown['intra_word_factor'] = cfg.intra_word_speed_factor

        # ── 4. 구두점 pause ──
        if cfg.punctuation_pause_enabled and prev_char in PUNCTUATION_CHARS:
            add = cfg.punctuation_pause_ms * (1 + random.gauss(0, 0.3))
            add = max(0, add)
            delay += add
            breakdown['punctuation'] = round(add, 1)

        # ── 5. Shift 패널티 ──
        if cfg.shift_penalty_enabled and char in SHIFT_CHARS:
            delay += cfg.shift_penalty_ms
            breakdown['shift'] = cfg.shift_penalty_ms

        # ── 6. 동일 글자 연속 가속 ──
        if (cfg.double_letter_enabled
                and prev_char is not None
                and char.lower() == prev_char.lower()):
            delay *= cfg.double_letter_speed_factor
            breakdown['double_letter_factor'] = cfg.double_letter_speed_factor

        # ── 7. 버스트 타이핑 micro-pause ──
        if cfg.burst_enabled and self._check_burst_boundary():
            add = cfg.burst_pause_ms * (1 + random.gauss(0, 0.3))
            add = max(0, add)
            delay += add
            breakdown['burst'] = round(add, 1)

        # ── 8. 피로 (fatigue) ──
        if cfg.fatigue_enabled and total_length > 0:
            progress = index / total_length
            multiplier = 1.0 + cfg.fatigue_factor * progress
            delay *= multiplier
            breakdown['fatigue_multiplier'] = round(multiplier, 4)

        # ── 최종 클램핑 ──
        final = max(15.0, delay)
        breakdown['final'] = round(final, 1)

        return final, breakdown

    def calculate_all(self, text: str) -> list[tuple[str, float, dict]]:
        """
        텍스트 전체에 대해 글자별 딜레이를 일괄 계산 (드라이런용).

        Returns:
            [(char, delay_ms, breakdown), ...] 리스트
        """
        self.reset()
        results = []
        prev_char = None

        for i, char in enumerate(text):
            delay, breakdown = self.calculate_delay(char, prev_char, i, len(text))
            results.append((char, delay, breakdown))
            prev_char = char

        return results


# ============================================================
# 테스트 / 검증용
# ============================================================

def _format_char(c: str) -> str:
    """출력용 문자 포맷. 제어문자는 이스케이프."""
    if c == ' ':
        return '␣'
    elif c == '\n':
        return '↵'
    elif c == '\t':
        return '⇥'
    return c


def _format_breakdown(bd: dict) -> str:
    """breakdown dict를 로그 태그 형태로 포맷."""
    parts = []
    for key, val in bd.items():
        if key == 'final':
            continue
        if key.endswith('_factor') or key.endswith('_multiplier'):
            parts.append(f"{key}:×{val}")
        elif key == 'base':
            parts.append(f"base:{val}")
        else:
            parts.append(f"{key}:+{val}")
    return ' '.join(parts)


if __name__ == "__main__":
    # 기본 설정으로 테스트
    print("=" * 60)
    print("타이밍 모델 드라이런 테스트")
    print("=" * 60)

    # 다양한 패턴이 포함된 테스트 텍스트
    test_text = "Hello, world! This is a test.\nNew line here."

    # 모든 옵션 ON으로 테스트
    config = TimingConfig(
        word_boundary_enabled=True,
        punctuation_pause_enabled=True,
        newline_pause_enabled=True,
        shift_penalty_enabled=True,
        double_letter_enabled=True,
        burst_enabled=True,
        fatigue_enabled=True,
    )
    model = TimingModel(config)
    results = model.calculate_all(test_text)

    # 결과 출력
    print(f"\n텍스트: {repr(test_text)}")
    print(f"글자 수: {len(test_text)}")
    print(f"\n{'#':>3}  {'문자':>4}  {'딜레이':>8}  breakdown")
    print("-" * 60)

    total_delay = 0
    for i, (char, delay, bd) in enumerate(results):
        total_delay += delay
        tag = _format_breakdown(bd)
        print(f"{i:3d}  {_format_char(char):>4}  {delay:7.1f}ms  [{tag}]")

    # 통계 요약
    delays = [d for _, d, _ in results]
    print("-" * 60)
    print(f"총 소요 시간: {total_delay / 1000:.2f}초")
    print(f"평균 딜레이:  {sum(delays) / len(delays):.1f}ms")
    print(f"최소 딜레이:  {min(delays):.1f}ms")
    print(f"최대 딜레이:  {max(delays):.1f}ms")

    # 옵션별 효과 비교 (간단)
    print(f"\n{'=' * 60}")
    print("옵션별 효과 비교 (같은 텍스트, 옵션 하나씩 끄기)")
    print(f"{'=' * 60}")

    configs = {
        "모든 옵션 ON": TimingConfig(
            word_boundary_enabled=True, punctuation_pause_enabled=True,
            newline_pause_enabled=True, shift_penalty_enabled=True,
            double_letter_enabled=True, burst_enabled=True, fatigue_enabled=True,
        ),
        "전부 OFF (로봇)": TimingConfig(
            delay_variance_ms=0,
            word_boundary_enabled=False, punctuation_pause_enabled=False,
            newline_pause_enabled=False, shift_penalty_enabled=False,
            double_letter_enabled=False, burst_enabled=False, fatigue_enabled=False,
        ),
    }

    for name, cfg in configs.items():
        m = TimingModel(cfg)
        r = m.calculate_all(test_text)
        ds = [d for _, d, _ in r]
        avg = sum(ds) / len(ds)
        total = sum(ds) / 1000
        mn, mx = min(ds), max(ds)
        print(f"  {name:20s}  avg={avg:6.1f}ms  min={mn:5.1f}  max={mx:6.1f}  총={total:.2f}s")
