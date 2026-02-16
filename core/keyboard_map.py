"""
QWERTY 키보드 레이아웃 기반 인접 키 맵 + Shift 조합 맵.

용도:
- 오타 모델에서 인접 키 오타 생성 시 사용
- Shift 패널티 판정 시 사용
- 대문자/특수문자의 기본 키(base key) 변환 시 사용
"""

# ============================================================
# QWERTY 인접 키 맵
# 각 키의 물리적으로 인접한 키 목록 (소문자 기준)
# ============================================================

ADJACENT_KEYS: dict[str, list[str]] = {
    # ── 숫자 행 ──
    '`': ['1'],
    '1': ['`', '2', 'q'],
    '2': ['1', '3', 'q', 'w'],
    '3': ['2', '4', 'w', 'e'],
    '4': ['3', '5', 'e', 'r'],
    '5': ['4', '6', 'r', 't'],
    '6': ['5', '7', 't', 'y'],
    '7': ['6', '8', 'y', 'u'],
    '8': ['7', '9', 'u', 'i'],
    '9': ['8', '0', 'i', 'o'],
    '0': ['9', '-', 'o', 'p'],
    '-': ['0', '=', 'p', '['],
    '=': ['-', '[', ']'],

    # ── 상단 행 (QWERTY) ──
    'q': ['1', '2', 'w', 'a'],
    'w': ['2', '3', 'q', 'e', 'a', 's'],
    'e': ['3', '4', 'w', 'r', 's', 'd'],
    'r': ['4', '5', 'e', 't', 'd', 'f'],
    't': ['5', '6', 'r', 'y', 'f', 'g'],
    'y': ['6', '7', 't', 'u', 'g', 'h'],
    'u': ['7', '8', 'y', 'i', 'h', 'j'],
    'i': ['8', '9', 'u', 'o', 'j', 'k'],
    'o': ['9', '0', 'i', 'p', 'k', 'l'],
    'p': ['0', '-', 'o', '[', 'l', ';'],
    '[': ['-', '=', 'p', ']', ';', "'"],
    ']': ['=', '[', '\\', "'"],
    '\\': ['=', ']'],

    # ── 중단 행 (ASDF) ──
    'a': ['q', 'w', 's', 'z'],
    's': ['q', 'w', 'e', 'a', 'd', 'z', 'x'],
    'd': ['w', 'e', 'r', 's', 'f', 'x', 'c'],
    'f': ['e', 'r', 't', 'd', 'g', 'c', 'v'],
    'g': ['r', 't', 'y', 'f', 'h', 'v', 'b'],
    'h': ['t', 'y', 'u', 'g', 'j', 'b', 'n'],
    'j': ['y', 'u', 'i', 'h', 'k', 'n', 'm'],
    'k': ['u', 'i', 'o', 'j', 'l', 'm', ','],
    'l': ['i', 'o', 'p', 'k', ';', ',', '.'],
    ';': ['o', 'p', '[', 'l', "'", '.'],
    "'": ['p', '[', ']', ';'],

    # ── 하단 행 (ZXCV) ──
    'z': ['a', 's', 'x'],
    'x': ['a', 's', 'd', 'z', 'c'],
    'c': ['s', 'd', 'f', 'x', 'v'],
    'v': ['d', 'f', 'g', 'c', 'b'],
    'b': ['f', 'g', 'h', 'v', 'n'],
    'n': ['g', 'h', 'j', 'b', 'm'],
    'm': ['h', 'j', 'k', 'n', ','],
    ',': ['j', 'k', 'l', 'm', '.'],
    '.': ['k', 'l', ';', ',', '/'],
    '/': ['l', ';', '.'],
}


# ============================================================
# Shift 조합 매핑
# ============================================================

# shifted_char → base_key
SHIFT_MAP: dict[str, str] = {
    '~': '`',
    '!': '1',
    '@': '2',
    '#': '3',
    '$': '4',
    '%': '5',
    '^': '6',
    '&': '7',
    '*': '8',
    '(': '9',
    ')': '0',
    '_': '-',
    '+': '=',
    '{': '[',
    '}': ']',
    '|': '\\',
    ':': ';',
    '"': "'",
    '<': ',',
    '>': '.',
    '?': '/',
}

# base_key → shifted_char (역방향)
UNSHIFT_MAP: dict[str, str] = {v: k for k, v in SHIFT_MAP.items()}

# A-Z ↔ a-z 도 SHIFT_MAP에 추가
for _c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
    SHIFT_MAP[_c] = _c.lower()

# Shift가 필요한 모든 문자 집합
SHIFT_CHARS: set[str] = set(SHIFT_MAP.keys())


# ============================================================
# 유틸리티 함수
# ============================================================

def get_base_key(char: str) -> str:
    """
    Shift 조합 문자의 기본 키를 반환.
    예: 'A' → 'a', '!' → '1', 'a' → 'a' (이미 기본 키)
    """
    return SHIFT_MAP.get(char, char)


def get_adjacent_keys(char: str) -> list[str]:
    """
    주어진 문자의 인접 키 목록을 반환.
    대문자/Shift 특수문자는 base_key 기준으로 조회 후,
    원래 문자가 Shift 문자였으면 인접 키도 Shift 변환하여 반환.

    예: 'e' → ['3', '4', 'w', 'r', 's', 'd']
        'E' → ['#', '$', 'W', 'R', 'S', 'D']  (Shift 적용)
        '!' → ['~', '@', 'Q']                   (Shift 적용)
    """
    is_shifted = char in SHIFT_CHARS
    base = get_base_key(char)

    neighbors = ADJACENT_KEYS.get(base, [])

    if not is_shifted:
        return list(neighbors)

    # Shift 문자였으면 인접 키도 Shift 변환
    shifted_neighbors = []
    for n in neighbors:
        if n in UNSHIFT_MAP:
            shifted_neighbors.append(UNSHIFT_MAP[n])
        else:
            shifted_neighbors.append(n.upper())
    return shifted_neighbors


def is_shift_required(char: str) -> bool:
    """해당 문자 입력에 Shift 키가 필요한지 반환."""
    return char in SHIFT_CHARS


# ============================================================
# 테스트 / 검증용
# ============================================================

if __name__ == "__main__":
    print("=== ADJACENT_KEYS 검증 ===")
    print(f"ADJACENT_KEYS['e'] = {ADJACENT_KEYS['e']}")
    print(f"ADJACENT_KEYS['a'] = {ADJACENT_KEYS['a']}")
    print(f"ADJACENT_KEYS['5'] = {ADJACENT_KEYS['5']}")
    print(f"ADJACENT_KEYS[','] = {ADJACENT_KEYS[',']}")
    print(f"ADJACENT_KEYS['/'] = {ADJACENT_KEYS['/']}")

    print("\n=== get_adjacent_keys() 검증 ===")
    print(f"get_adjacent_keys('e') = {get_adjacent_keys('e')}")
    print(f"get_adjacent_keys('E') = {get_adjacent_keys('E')}")
    print(f"get_adjacent_keys('!') = {get_adjacent_keys('!')}")
    print(f"get_adjacent_keys('a') = {get_adjacent_keys('a')}")
    print(f"get_adjacent_keys('A') = {get_adjacent_keys('A')}")

    print("\n=== SHIFT 검증 ===")
    print(f"is_shift_required('A') = {is_shift_required('A')}")
    print(f"is_shift_required('a') = {is_shift_required('a')}")
    print(f"is_shift_required('!') = {is_shift_required('!')}")
    print(f"is_shift_required('1') = {is_shift_required('1')}")
    print(f"get_base_key('!') = {get_base_key('!')}")
    print(f"get_base_key('A') = {get_base_key('A')}")

    print(f"\n총 매핑된 키 수: {len(ADJACENT_KEYS)}")
    print(f"Shift 문자 수: {len(SHIFT_CHARS)}")
