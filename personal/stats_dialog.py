"""
stats_dialog.py
- StatsDialog: 타이핑 완료 후 통계 요약 + matplotlib 시각화
- PreviewDialog: 미리보기 — 텍스트 입력 없이 현재 설정을 즉시 시뮬레이션
"""

import customtkinter as ctk

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D

from core.timing_model import TimingModel, TimingConfig
from core.typo_model import TypoModel, TypoConfig, ActionType


# ── 한글 폰트 ──

def _setup_font():
    try:
        for name in ["Malgun Gothic", "맑은 고딕", "NanumGothic", "AppleGothic"]:
            if any(name in f.name for f in fm.fontManager.ttflist):
                plt.rcParams["font.family"] = name
                plt.rcParams["axes.unicode_minus"] = False
                return
    except Exception:
        pass

_setup_font()


# ── 공통: 딜레이 차트 그리기 ──

def _draw_delay_charts(parent_widget, timing_data: list[tuple[str, float, dict]],
                       figsize=(9, 3), dpi=90):
    """히스토그램 + 시계열 scatter를 그려서 parent_widget에 임베드."""
    delays = [d for _, d, _ in timing_data]
    if not delays:
        return None, None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor("#2b2b2b")

    # ── 히스토그램 ──
    ax1.set_facecolor("#333333")
    ax1.hist(delays, bins=min(30, max(5, len(delays) // 3)),
             color="#4CAF50", edgecolor="#2b2b2b", alpha=0.85)
    avg = sum(delays) / len(delays)
    ax1.axvline(avg, color="#FF9800", linestyle="--", linewidth=1.5,
                label=f"avg {avg:.0f}ms")
    ax1.set_title("Delay Distribution", color="white", fontsize=10)
    ax1.set_xlabel("ms", color="white", fontsize=8)
    ax1.set_ylabel("count", color="white", fontsize=8)
    ax1.tick_params(colors="white", labelsize=7)
    ax1.legend(fontsize=7, facecolor="#333", edgecolor="#555", labelcolor="white")
    for s in ax1.spines.values():
        s.set_color("#555")

    # ── 시계열 scatter (색상 = 타이밍 원인) ──
    ax2.set_facecolor("#333333")
    colors = []
    for _, _, bd in timing_data:
        if "newline" in bd:       colors.append("#FF5722")
        elif "inter_word" in bd:  colors.append("#2196F3")
        elif "punctuation" in bd: colors.append("#FF9800")
        elif "shift" in bd:       colors.append("#9C27B0")
        else:                     colors.append("#4CAF50")

    ax2.scatter(range(len(delays)), delays, c=colors, s=5, alpha=0.7)
    ax2.set_title("Per-Character Delay", color="white", fontsize=10)
    ax2.set_xlabel("index", color="white", fontsize=8)
    ax2.set_ylabel("ms", color="white", fontsize=8)
    ax2.tick_params(colors="white", labelsize=7)
    for s in ax2.spines.values():
        s.set_color("#555")

    legend_items = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markersize=5, label=l)
        for c, l in [("#4CAF50", "일반"), ("#2196F3", "단어경계"),
                     ("#FF9800", "구두점"), ("#FF5722", "개행"), ("#9C27B0", "Shift")]
    ]
    ax2.legend(handles=legend_items, fontsize=6, facecolor="#333",
               edgecolor="#555", labelcolor="white", loc="upper right")

    fig.tight_layout(pad=1.2)

    canvas = FigureCanvasTkAgg(fig, master=parent_widget)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

    return fig, canvas


# ============================================================
# StatsDialog — 타이핑 완료 후 통계 창
# ============================================================

class StatsDialog(ctk.CTkToplevel):
    """타이핑 완료 후 자동으로 뜨는 통계 + 차트 다이얼로그."""

    def __init__(self, master, stats: dict, timing_data: list):
        super().__init__(master)
        self.title("📊 타이핑 통계")
        self.geometry("720x520")
        self.resizable(True, True)
        self.transient(master)

        self._stats = stats
        self._timing_data = timing_data
        self._fig = None
        self._canvas = None

        self._build_ui()

    def _build_ui(self):
        s = self._stats
        ts = s.get("typo_stats", {})

        # ── 통계 요약 ──
        summary = ctk.CTkFrame(self)
        summary.pack(fill="x", padx=15, pady=(12, 5))

        lines = [
            f"총 소요: {s.get('total_time_sec', 0)}초   │   "
            f"글자 수: {s.get('total_chars', 0)}   │   "
            f"속도: {s.get('avg_cpm', 0)} CPM ({s.get('avg_wpm', 0)} WPM)",

            f"딜레이 평균: {s.get('avg_delay_ms', 0)}ms   │   "
            f"최소: {s.get('min_delay_ms', 0)}ms   │   "
            f"최대: {s.get('max_delay_ms', 0)}ms",

            f"오타: {ts.get('typos', 0)}회  "
            f"(인접 {ts.get('adjacent', 0)}, "
            f"전치 {ts.get('transposition', 0)}, "
            f"이중 {ts.get('double_strike', 0)})   │   "
            f"수정 {ts.get('revised', 0)} / 미수정 {ts.get('unrevised', 0)}",
        ]
        for line in lines:
            ctk.CTkLabel(summary, text=line, font=ctk.CTkFont(size=12),
                          anchor="w").pack(fill="x", padx=10, pady=1)

        # ── 차트 ──
        chart_frame = ctk.CTkFrame(self)
        chart_frame.pack(fill="both", expand=True, padx=15, pady=(5, 5))

        if self._timing_data:
            self._fig, self._canvas = _draw_delay_charts(chart_frame, self._timing_data)
        else:
            ctk.CTkLabel(chart_frame, text="(타이밍 데이터 없음)",
                          text_color="gray").pack(expand=True)

        # 닫기
        ctk.CTkButton(self, text="닫기", width=100, command=self.destroy
                       ).pack(pady=(0, 10))

    def destroy(self):
        if self._fig:
            plt.close(self._fig)
        super().destroy()


# ============================================================
# PreviewDialog — 미리보기 시뮬레이션
# ============================================================

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


class PreviewDialog(ctk.CTkToplevel):
    """
    미리보기 — 텍스트 입력/화면 전환 없이 현재 설정으로 시뮬레이션.
    샘플 텍스트를 선택하면 타이밍 + 오타 결과를 즉시 보여줌.
    """

    def __init__(self, master, timing_cfg: TimingConfig, typo_cfg: TypoConfig):
        super().__init__(master)
        self.title("🔬 미리보기 — 설정 시뮬레이션")
        self.geometry("820x620")
        self.resizable(True, True)
        self.transient(master)

        self._timing_cfg = timing_cfg
        self._typo_cfg = typo_cfg
        self._fig = None
        self._canvas = None

        self._build_ui()
        self._run_simulation()

    def _build_ui(self):
        # ── 상단: 샘플 선택 + 다시 실행 ──
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(top, text="샘플:", font=ctk.CTkFont(size=12)).pack(side="left")

        self._sample_var = ctk.StringVar(value="영문 기본")
        ctk.CTkOptionMenu(
            top, values=list(SAMPLE_TEXTS.keys()),
            variable=self._sample_var, width=200, height=28,
            font=ctk.CTkFont(size=11),
            command=lambda _: self._run_simulation(),
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            top, text="🔄 다시 실행", width=110, height=28,
            font=ctk.CTkFont(size=11), command=self._run_simulation,
        ).pack(side="left", padx=4)

        self._config_label = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=10), text_color="gray",
        )
        self._config_label.pack(side="right", padx=8)

        # ── 시뮬레이션 결과 ──
        self._result_textbox = ctk.CTkTextbox(
            self, height=140,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled", wrap="word",
        )
        self._result_textbox.pack(fill="x", padx=15, pady=(5, 2))

        # ── 통계 한 줄 ──
        self._stats_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11), anchor="w",
        )
        self._stats_label.pack(fill="x", padx=20, pady=2)

        # ── 차트 ──
        self._chart_frame = ctk.CTkFrame(self)
        self._chart_frame.pack(fill="both", expand=True, padx=15, pady=(2, 5))

        # 닫기
        ctk.CTkButton(self, text="닫기", width=100, command=self.destroy
                       ).pack(pady=(0, 10))

    def _run_simulation(self):
        """현재 설정으로 시뮬레이션 실행 후 결과 표시."""
        text = SAMPLE_TEXTS.get(self._sample_var.get(), SAMPLE_TEXTS["영문 기본"])

        self._config_label.configure(
            text=f"딜레이:{self._timing_cfg.base_delay_ms}ms  │  "
                 f"분산:±{self._timing_cfg.delay_variance_ms}ms  │  "
                 f"오타:{self._typo_cfg.typo_prob / 100:.2f}%"
        )

        # 타이밍 시뮬레이션
        timing = TimingModel(self._timing_cfg)
        timing_data = timing.calculate_all(text)

        # 오타 시뮬레이션
        typo = TypoModel(self._typo_cfg)
        typo_results = typo.process_text(text)

        # 결과 텍스트 재구성: 오타가 어디서 발생했는지 표시
        output_chars = []
        typo_annotations = []

        for idx, orig_char, actions in typo_results:
            has_typo = any("오타" in a.label or "전치" in a.label or "이중" in a.label
                          for a in actions)
            has_fix = any(a.action_type == ActionType.BACKSPACE for a in actions)

            if has_typo:
                # 오타 발생 — 어떤 글자가 잘못 입력됐는지
                wrong_char = ""
                for a in actions:
                    if a.action_type == ActionType.TYPE and (
                        "오타" in a.label or "전치" in a.label or "이중" in a.label
                    ):
                        wrong_char = a.char
                        break

                if has_fix:
                    typo_annotations.append(
                        f"  [{idx:3d}] '{orig_char}' → '{wrong_char}' (수정됨 ✓)"
                    )
                    output_chars.append(orig_char)  # 수정 후 원래 글자
                else:
                    typo_annotations.append(
                        f"  [{idx:3d}] '{orig_char}' → '{wrong_char}' (미수정 ✗)"
                    )
                    output_chars.append(wrong_char)  # 수정 안 됨
            else:
                output_chars.append(orig_char)

        final_text = "".join(output_chars)

        # 결과 표시
        self._result_textbox.configure(state="normal")
        self._result_textbox.delete("1.0", "end")

        self._result_textbox.insert("1.0", f"[원본] {text}\n")
        self._result_textbox.insert("end", f"[결과] {final_text}\n")

        if typo_annotations:
            self._result_textbox.insert("end", f"\n오타 발생 ({len(typo_annotations)}건):\n")
            for ann in typo_annotations:
                self._result_textbox.insert("end", ann + "\n")
        else:
            self._result_textbox.insert("end", "\n(오타 없음)")

        self._result_textbox.configure(state="disabled")

        # 통계 한 줄
        delays = [d for _, d, _ in timing_data]
        avg = sum(delays) / len(delays) if delays else 0
        total_sec = sum(delays) / 1000
        cpm = len(text) / total_sec * 60 if total_sec > 0 else 0
        ts = typo.stats

        self._stats_label.configure(
            text=f"예상 소요: {total_sec:.1f}초  │  "
                 f"평균: {avg:.0f}ms  │  "
                 f"속도: {cpm:.0f} CPM ({cpm / 5:.0f} WPM)  │  "
                 f"오타: {ts['typos']}회 "
                 f"(수정 {ts['revised']}, 미수정 {ts['unrevised']})"
        )

        # 차트 갱신
        self._redraw_chart(timing_data)

    def _redraw_chart(self, timing_data):
        """차트 영역 갱신."""
        # 이전 차트 정리
        if self._fig:
            plt.close(self._fig)
        for w in self._chart_frame.winfo_children():
            w.destroy()

        if timing_data:
            self._fig, self._canvas = _draw_delay_charts(
                self._chart_frame, timing_data, figsize=(10, 2.6)
            )

    def destroy(self):
        if self._fig:
            plt.close(self._fig)
        super().destroy()
