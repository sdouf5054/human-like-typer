"""
텍스트 전처리 모듈.
클립보드/직접 입력 텍스트를 타이핑 엔진에 전달하기 전에 정규화.

옵션:
- CRLF → LF 정규화
- 앞뒤 공백 제거 (trim)
- 연속 공백 정규화
- 개행 처리 모드 (유지 / space 치환 / 제거)
- 최대 길이 제한
"""

import re
from dataclasses import dataclass


@dataclass
class PreprocessConfig:
    """전처리 옵션. GUI 토글과 1:1 대응."""

    crlf_normalize: bool = True
    trim: bool = True
    normalize_spaces: bool = False
    newline_mode: str = "enter"   # "enter" | "space" | "remove"
    max_length_enabled: bool = False
    max_length: int = 10000


def preprocess(text: str, config: PreprocessConfig | None = None) -> str:
    """
    텍스트 전처리를 적용하여 반환.
    원본 텍스트는 변경하지 않음.
    """
    if config is None:
        config = PreprocessConfig()

    # 1. CRLF → LF
    if config.crlf_normalize:
        text = text.replace('\r\n', '\n')
        text = text.replace('\r', '\n')  # 혹시 남은 단독 CR 제거

    # 2. 앞뒤 공백 제거
    if config.trim:
        text = text.strip()

    # 3. 연속 공백 정규화 (2개 이상 → 1개)
    if config.normalize_spaces:
        text = re.sub(r' {2,}', ' ', text)

    # 4. 개행 처리
    if config.newline_mode == "space":
        text = text.replace('\n', ' ')
    elif config.newline_mode == "remove":
        text = text.replace('\n', '')
    # "enter" → 그대로 유지

    # 5. 최대 길이 제한
    if config.max_length_enabled and len(text) > config.max_length:
        text = text[:config.max_length]

    return text


if __name__ == "__main__":
    # 전처리 테스트
    test = "  Hello   world!  \r\n  This is a test.  \r\n  Line 3.  "
    print(f"원본:  {repr(test)}")
    print(f"길이:  {len(test)}")

    # 기본 설정
    result = preprocess(test)
    print(f"\n기본 전처리: {repr(result)}")

    # 연속 공백 정규화 ON
    result2 = preprocess(test, PreprocessConfig(normalize_spaces=True))
    print(f"공백 정규화: {repr(result2)}")

    # 개행 → space
    result3 = preprocess(test, PreprocessConfig(newline_mode="space"))
    print(f"개행→space: {repr(result3)}")

    # 개행 제거
    result4 = preprocess(test, PreprocessConfig(newline_mode="remove"))
    print(f"개행 제거:  {repr(result4)}")

    # 최대 길이 제한
    result5 = preprocess(test, PreprocessConfig(max_length_enabled=True, max_length=20))
    print(f"최대 20자:  {repr(result5)}")
