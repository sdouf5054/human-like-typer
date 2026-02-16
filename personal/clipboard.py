"""
클립보드 읽기 모듈.
pyperclip을 사용하여 현재 클립보드의 텍스트를 반환.
"""

import pyperclip


def get_clipboard_text() -> str:
    """
    현재 클립보드의 텍스트를 반환.
    텍스트가 아니거나 읽기 실패 시 빈 문자열 반환.
    """
    try:
        text = pyperclip.paste()
        return text if isinstance(text, str) else ""
    except Exception:
        return ""


if __name__ == "__main__":
    text = get_clipboard_text()
    if text:
        preview = text[:100] + ("..." if len(text) > 100 else "")
        print(f"클립보드 내용 ({len(text)}자):")
        print(preview)
    else:
        print("클립보드가 비어있거나 텍스트가 아닙니다.")
