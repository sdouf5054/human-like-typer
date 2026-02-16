"""
내장 테스트 패널 — 프로그램 내부에서 현재 프리셋 설정대로
실제 타이핑이 어떻게 보이는지 시뮬레이션.

OS 키보드 이벤트 대신 엔진 액션(TYPE/BACKSPACE/PAUSE)을
내부 텍스트 위젯에 직접 적용.
"""

import time
import threading
import customtkinter as ctk
from typing import Callable

from core.timing_model import TimingModel, TimingConfig
from core.typo_model import TypoModel, TypoConfig, ActionType


SAMPLE_TEXTS = {
    "영문 기본": "The quick brown fox jumps over the lazy dog. Hello, World!",
    "영문 긴 문장": (
        "In the beginning, there was nothing but darkness. "
        "Then a spark of light appeared, illuminating the vast emptiness. "
        "Stars formed, galaxies spun into existence, and life emerged.\n"
        "It was beautiful."
    ),
    "혼합 (영문+숫자+기호)": (
        "Project v2.0 launched on 2025-01-15 with 3,500+ users! "
        "Contact: support@example.com (24/7 available)."
    ),
    "코드 스니펫": (
        'def hello(name="World"):\n'
        '    print(f"Hello, {name}!")\n'
        '    return True\n'
    ),
}


class TestPanel(ctk.CTkToplevel):
    """
    내장 테스트 — 현재 프리셋으로 앱 안에서 타이핑 시뮬레이션.

    왼쪽: 원문 / 오른쪽: 실시간 타이핑 결과
    하단: 통계 요약
    """

    def __init__(self, master, timing_cfg: TimingConfig, typo_cfg: TypoConfig):
        super().__init__(master)

        self.title("🧪 테스트 — 내장 시뮬레이션")
        self.geometry("800x500")
        self.resizable(True, True)
        self.transient(master)

        self._timing_cfg = timing_cfg
        self._typo_cfg = typo_cfg
        self._running = False
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self):
        # ── 상단: 샘플 선택 + 버튼 ──
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10, 5))

        ctk.CTkLabel(top, text="샘플:", font=ctk.CTkFont(size=12)).pack(side="left")

        self._sample_var = ctk.StringVar(value="영문 기본")
        ctk.CTkOptionMenu(
            top, values=list(SAMPLE_TEXTS.keys()),
            variable=self._sample_var, width=200, height=28,
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=8)

        self._btn_run = ctk.CTkButton(
            top, text="▶ 테스트 실행", width=110, height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2B7A3E", hover_color="#236B33",
            command=self._on_run,
        )
        self._btn_run.pack(side="left", padx=4)

        self._btn_stop = ctk.CTkButton(
            top, text="⏹ 중지", width=70, height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#AA3333", hover_color="#882222",
            state="disabled",
            command=self._on_stop,
        )
        self._btn_stop.pack(side="left", padx=4)

        self._btn_clear = ctk.CTkButton(
            top, text="🧹 지우기", width=80, height=30,
            font=ctk.CTkFont(size=11),
            fg_color="#555555", hover_color="#444444",
            command=self._on_clear,
        )
        self._btn_clear.pack(side="left", padx=4)

        self._config_label = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=10), text_color="gray",
        )
        self._config_label.pack(side="right", padx=8)

        # ── 본문: 원문 / 결과 나란히 ──
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=5)

        # 원문
        left = ctk.CTkFrame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))

        ctk.CTkLabel(left, text="원문", font=ctk.CTkFont(size=11, weight="bold"),
                      anchor="w").pack(fill="x", padx=6, pady=(4, 2))

        self._source_box = ctk.CTkTextbox(
            left, font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled", wrap="word", fg_color="#1a1a2e",
        )
        self._source_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # 결과
        right = ctk.CTkFrame(body)
        right.pack(side="right", fill="both", expand=True, padx=(4, 0))

        ctk.CTkLabel(right, text="타이핑 결과 (실시간)", font=ctk.CTkFont(size=11, weight="bold"),
                      anchor="w").pack(fill="x", padx=6, pady=(4, 2))

        self._output_box = ctk.CTkTextbox(
            right, font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled", wrap="word", fg_color="#1a2e1a",
        )
        self._output_box.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # ── 하단: 통계 ──
        self._stats_label = ctk.CTkLabel(
            self, text="테스트 실행 대기중...",
            font=ctk.CTkFont(size=11), anchor="w",
        )
        self._stats_label.pack(fill="x", padx=16, pady=(2, 10))

    # ── 버튼 핸들러 ──

    def _on_run(self):
        """테스트 실행 — 별도 스레드에서 시뮬레이션."""
        if self._running:
            return

        text = SAMPLE_TEXTS.get(self._sample_var.get(), SAMPLE_TEXTS["영문 기본"])

        self._config_label.configure(
            text=f"딜레이:{self._timing_cfg.base_delay_ms}ms  "
                 f"오타:{self._typo_cfg.typo_prob / 100:.2f}%"
        )

        # 원문 표시
        self._source_box.configure(state="normal")
        self._source_box.delete("1.0", "end")
        self._source_box.insert("1.0", text)
        self._source_box.configure(state="disabled")

        # 결과 초기화
        self._output_box.configure(state="normal")
        self._output_box.delete("1.0", "end")
        self._output_box.configure(state="disabled")

        self._stats_label.configure(text="실행중...")
        self._running = True
        self._stop_flag.clear()

        self._btn_run.configure(state="disabled")
        self._btn_stop.configure(state="normal")

        self._thread = threading.Thread(
            target=self._run_simulation, args=(text,), daemon=True
        )
        self._thread.start()

    def _on_stop(self):
        self._stop_flag.set()

    def _on_clear(self):
        self._output_box.configure(state="normal")
        self._output_box.delete("1.0", "end")
        self._output_box.configure(state="disabled")
        self._stats_label.configure(text="테스트 실행 대기중...")

    # ── 시뮬레이션 스레드 ──

    def _run_simulation(self, text: str):
        """엔진과 동일한 로직으로 액션을 생성하되, OS키 대신 텍스트박스에 적용."""
        timing = TimingModel(self._timing_cfg)
        typo = TypoModel(self._typo_cfg)

        total = len(text)
        i = 0
        prev_char = None
        start_time = time.time()
        typed_count = 0

        while i < total:
            if self._stop_flag.is_set():
                self.after(0, self._finish, "중지됨", typed_count, time.time() - start_time, timing)
                return

            char = text[i]
            next_char = text[i + 1] if i < total - 1 else None

            delay, breakdown = timing.calculate_delay(char, prev_char, i, total)
            actions, skip_next = typo.process_char(char, prev_char, next_char)

            # 실제 딜레이 대기 (체감용)
            time.sleep(delay / 1000)

            # 액션을 GUI 텍스트박스에 적용
            for action in actions:
                if self._stop_flag.is_set():
                    self.after(0, self._finish, "중지됨", typed_count, time.time() - start_time, timing)
                    return

                if action.action_type == ActionType.TYPE:
                    self.after(0, self._insert_char, action.char)
                    typed_count += 1

                elif action.action_type == ActionType.BACKSPACE:
                    self.after(0, self._do_backspace, action.count)

                elif action.action_type == ActionType.PAUSE:
                    time.sleep(action.duration_ms / 1000)

            prev_char = char
            if skip_next:
                i += 2
            else:
                i += 1

        elapsed = time.time() - start_time
        self.after(0, self._finish, "완료", typed_count, elapsed, timing)

    # ── GUI 조작 (메인 스레드에서 호출) ──

    def _insert_char(self, char: str):
        if not self.winfo_exists():
            return
        self._output_box.configure(state="normal")
        self._output_box.insert("end", char)
        self._output_box.see("end")
        self._output_box.configure(state="disabled")

    def _do_backspace(self, count: int):
        if not self.winfo_exists():
            return
        self._output_box.configure(state="normal")
        for _ in range(count):
            self._output_box.delete("end-2c", "end-1c")
        self._output_box.configure(state="disabled")

    def _finish(self, status: str, typed_count: int, elapsed: float, timing: TimingModel):
        self._running = False
        if not self.winfo_exists():
            return

        self._btn_run.configure(state="normal")
        self._btn_stop.configure(state="disabled")

        cpm = typed_count / elapsed * 60 if elapsed > 0 else 0
        delays = [d for _, d, _ in timing._history] if hasattr(timing, '_history') else []

        ts = getattr(self, '_typo_stats', {})
        self._stats_label.configure(
            text=f"{status}  │  {elapsed:.1f}초  │  {typed_count}자  │  "
                 f"{cpm:.0f} CPM ({cpm / 5:.0f} WPM)"
        )

    def destroy(self):
        self._stop_flag.set()
        super().destroy()
