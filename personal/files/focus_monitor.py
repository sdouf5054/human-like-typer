"""
포커스 모니터 — 타이핑 시작 시점의 활성 창 타이틀을 기록하고,
N글자마다 현재 포커스 창이 바뀌었는지 검사.

포커스 이탈 시 on_focus_lost 콜백을 호출하여 엔진 일시정지.
Windows: ctypes.windll.user32 사용
기타 OS: 비활성 (항상 True 반환)
"""

import sys
import logging

logger = logging.getLogger(__name__)

# Windows API 로드 시도
_win_api_available = False
if sys.platform == "win32":
    try:
        import ctypes
        _user32 = ctypes.windll.user32
        _win_api_available = True
    except Exception:
        pass


def get_active_window_title() -> str:
    """현재 포커스된 창의 타이틀을 반환. 실패 시 빈 문자열."""
    if not _win_api_available:
        return ""
    try:
        hwnd = _user32.GetForegroundWindow()
        length = _user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        _user32.GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception:
        return ""


class FocusMonitor:
    """
    포커스 모니터. 타이핑 엔진이 N글자마다 check()를 호출.

    사용법:
        monitor = FocusMonitor(enabled=True, check_interval=10)
        monitor.capture()  # 타이핑 시작 시 현재 창 기록
        ...
        if not monitor.check(char_index):  # 포커스 이탈 감지
            engine.pause()
    """

    def __init__(self, enabled: bool = True, check_interval: int = 10):
        self.enabled = enabled
        self.check_interval = max(1, check_interval)
        self._captured_title: str = ""
        self._last_check_index: int = -check_interval  # 첫 체크 즉시 실행

    def capture(self):
        """현재 활성 창 타이틀을 기록 (카운트다운 완료 시점에 호출)."""
        self._captured_title = get_active_window_title()
        self._last_check_index = -self.check_interval
        if self._captured_title:
            logger.info(f"[포커스 모니터] 타겟 창: \"{self._captured_title}\"")

    def check(self, char_index: int) -> bool:
        """
        포커스가 유지되고 있는지 검사.

        Args:
            char_index: 현재 글자 인덱스

        Returns:
            True = 포커스 유지 (또는 비활성), False = 포커스 이탈
        """
        if not self.enabled or not _win_api_available:
            return True

        # N글자마다만 검사 (성능)
        if char_index - self._last_check_index < self.check_interval:
            return True

        self._last_check_index = char_index
        current = get_active_window_title()

        if not self._captured_title or not current:
            return True

        if current != self._captured_title:
            logger.warning(
                f"[포커스 모니터] 이탈 감지! "
                f"\"{self._captured_title}\" → \"{current}\""
            )
            return False

        return True

    def reset(self):
        """상태 초기화."""
        self._captured_title = ""
        self._last_check_index = -self.check_interval


if __name__ == "__main__":
    import time
    print("=== 포커스 모니터 테스트 ===")
    print(f"Windows API 사용 가능: {_win_api_available}")

    title = get_active_window_title()
    print(f"현재 활성 창: \"{title}\"")

    monitor = FocusMonitor(enabled=True, check_interval=1)
    monitor.capture()
    print(f"캡처 완료. 5초간 포커스 변화 감시...")

    for i in range(50):
        ok = monitor.check(i)
        if not ok:
            print(f"  [{i}] ⚠️ 포커스 이탈!")
        time.sleep(0.1)

    print("테스트 완료.")
