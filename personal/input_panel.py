"""
입력 소스 패널 — 클립보드 미리보기 탭 + 직접 입력 탭.

기능:
- 클립보드 탭: 현재 클립보드 내용 미리보기 + 새로고침 + "이 텍스트 사용"
- 직접 입력 탭: 멀티라인 텍스트 편집 + "이 텍스트 사용"
- 글자 수 + 예상 소요 시간 실시간 표시
"""

import customtkinter as ctk
from typing import Callable

from core.clipboard import get_clipboard_text


class InputPanel(ctk.CTkFrame):
    """입력 소스 패널. 탭뷰로 클립보드/직접 입력 전환."""

    def __init__(self, master, on_text_selected: Callable[[str], None] | None = None,
                 **kwargs):
        super().__init__(master, **kwargs)
        self.on_text_selected = on_text_selected
        self._base_delay_ms = 70  # 예상 시간 계산용 기본값

        self._build_ui()

    def _build_ui(self):
        # 섹션 라벨
        title = ctk.CTkLabel(
            self, text="📝 입력 소스",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        title.pack(fill="x", padx=10, pady=(8, 4))

        # 탭뷰
        self._tabview = ctk.CTkTabview(self, height=200)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self._tabview.add("클립보드")
        self._tabview.add("직접 입력")

        self._build_clipboard_tab(self._tabview.tab("클립보드"))
        self._build_direct_tab(self._tabview.tab("직접 입력"))

    # ── 클립보드 탭 ──

    def _build_clipboard_tab(self, parent):
        # 상단: 라벨 + 새로고침 버튼
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=4, pady=(4, 2))

        ctk.CTkLabel(
            top, text="📋 현재 클립보드 내용",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(side="left")

        ctk.CTkButton(
            top, text="🔄 새로고침", width=90, height=28,
            font=ctk.CTkFont(size=11),
            command=self._refresh_clipboard,
        ).pack(side="right")

        # 미리보기 텍스트박스 (읽기 전용)
        self._clip_textbox = ctk.CTkTextbox(
            parent, height=100,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
            wrap="word",
        )
        self._clip_textbox.pack(fill="both", expand=True, padx=4, pady=2)

        # 하단: 정보 + 버튼
        bottom = ctk.CTkFrame(parent, fg_color="transparent")
        bottom.pack(fill="x", padx=4, pady=(2, 4))

        self._clip_info = ctk.CTkLabel(
            bottom, text="글자 수: 0  │  예상 소요: ~0.0초",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self._clip_info.pack(side="left")

        ctk.CTkButton(
            bottom, text="▶ 이 텍스트 사용", width=120, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._use_clipboard,
        ).pack(side="right")

        # 초기 로드
        self._refresh_clipboard()

    def _refresh_clipboard(self):
        """클립보드 내용을 읽어 미리보기에 표시."""
        text = get_clipboard_text()
        self._clip_text = text

        self._clip_textbox.configure(state="normal")
        self._clip_textbox.delete("1.0", "end")
        if text:
            # 미리보기는 5000자까지
            preview = text[:5000]
            if len(text) > 5000:
                preview += f"\n\n... ({len(text) - 5000}자 더 있음)"
            self._clip_textbox.insert("1.0", preview)
        else:
            self._clip_textbox.insert("1.0", "(클립보드가 비어있거나 텍스트가 아닙니다)")
        self._clip_textbox.configure(state="disabled")

        # 정보 업데이트
        count = len(text)
        est = count * self._base_delay_ms / 1000
        self._clip_info.configure(
            text=f"글자 수: {count}  │  예상 소요: ~{est:.1f}초"
        )

    def _use_clipboard(self):
        """클립보드 텍스트를 타이핑 대상으로 설정."""
        if self._clip_text and self.on_text_selected:
            self.on_text_selected(self._clip_text)

    # ── 직접 입력 탭 ──

    def _build_direct_tab(self, parent):
        # 라벨
        ctk.CTkLabel(
            parent, text="✏️ 텍스트 직접 입력",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x", padx=4, pady=(4, 2))

        # 입력 텍스트박스 (편집 가능)
        self._direct_textbox = ctk.CTkTextbox(
            parent, height=100,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
        )
        self._direct_textbox.pack(fill="both", expand=True, padx=4, pady=2)

        # 키 입력마다 정보 업데이트
        self._direct_textbox.bind("<KeyRelease>", self._on_direct_input_change)

        # 하단: 정보 + 버튼
        bottom = ctk.CTkFrame(parent, fg_color="transparent")
        bottom.pack(fill="x", padx=4, pady=(2, 4))

        self._direct_info = ctk.CTkLabel(
            bottom, text="글자 수: 0  │  예상 소요: ~0.0초",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self._direct_info.pack(side="left")

        ctk.CTkButton(
            bottom, text="▶ 이 텍스트 사용", width=120, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._use_direct,
        ).pack(side="right")

    def _on_direct_input_change(self, event=None):
        """직접 입력 텍스트가 변경될 때 정보 업데이트."""
        text = self._direct_textbox.get("1.0", "end-1c")
        count = len(text)
        est = count * self._base_delay_ms / 1000
        self._direct_info.configure(
            text=f"글자 수: {count}  │  예상 소요: ~{est:.1f}초"
        )

    def _use_direct(self):
        """직접 입력 텍스트를 타이핑 대상으로 설정."""
        text = self._direct_textbox.get("1.0", "end-1c")
        if text.strip() and self.on_text_selected:
            self.on_text_selected(text)

    # ── 외부 인터페이스 ──

    def update_base_delay(self, base_delay_ms: int):
        """예상 소요 시간 계산용 기본 딜레이 업데이트 (설정 변경 시 호출)."""
        self._base_delay_ms = base_delay_ms

    def get_active_tab(self) -> str:
        """현재 활성 탭 이름 반환."""
        return self._tabview.get()

    def set_active_tab(self, tab_name: str):
        """탭 전환."""
        self._tabview.set(tab_name)

    def get_direct_text(self) -> str:
        """직접 입력 탭의 텍스트 반환."""
        return self._direct_textbox.get("1.0", "end-1c")

    def set_direct_text(self, text: str):
        """직접 입력 탭의 텍스트 설정 (config 복원 시 사용)."""
        self._direct_textbox.delete("1.0", "end")
        self._direct_textbox.insert("1.0", text)
        self._on_direct_input_change()
