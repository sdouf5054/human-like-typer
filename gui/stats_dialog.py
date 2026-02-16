"""
통계 다이얼로그 — 타이핑 완료 후 통계 요약 + 딜레이 시각화.
(미리보기 기능은 test_panel.py로 분리됨)
"""

import customtkinter as ctk

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.lines import Line2D
    import matplotlib.font_manager as fm
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False


def _setup_font():
    if not _HAS_MPL:
        return
    try:
        for name in ["Malgun Gothic", "맑은 고딕", "NanumGothic"]:
            if any(name in f.name for f in fm.fontManager.ttflist):
                plt.rcParams["font.family"] = name
                plt.rcParams["axes.unicode_minus"] = False
                return
    except Exception:
        pass

_setup_font()


class StatsDialog(ctk.CTkToplevel):
    """타이핑 완료 후 통계 + 차트."""

    def __init__(self, master, stats: dict, timing_data: list):
        super().__init__(master)
        self.title("📊 타이핑 통계")
        self.geometry("700x480")
        self.resizable(True, True)
        self.transient(master)

        self._stats = stats
        self._timing_data = timing_data
        self._fig = None

        self._build_ui()

    def _build_ui(self):
        s = self._stats
        ts = s.get("typo_stats", {})

        # ── 통계 요약 ──
        summary = ctk.CTkFrame(self)
        summary.pack(fill="x", padx=15, pady=(12, 5))

        lines = [
            f"소요: {s.get('total_time_sec', 0)}초  │  "
            f"글자: {s.get('total_chars', 0)}  │  "
            f"속도: {s.get('avg_cpm', 0)} CPM ({s.get('avg_wpm', 0)} WPM)",

            f"딜레이: 평균 {s.get('avg_delay_ms', 0)}ms  "
            f"(최소 {s.get('min_delay_ms', 0)} / 최대 {s.get('max_delay_ms', 0)})",

            f"오타: {ts.get('typos', 0)}회  "
            f"(수정 {ts.get('revised', 0)} / 미수정 {ts.get('unrevised', 0)})",
        ]
        for line in lines:
            ctk.CTkLabel(summary, text=line, font=ctk.CTkFont(size=12),
                          anchor="w").pack(fill="x", padx=10, pady=1)

        # ── 차트 (matplotlib 있을 때만) ──
        chart_frame = ctk.CTkFrame(self)
        chart_frame.pack(fill="both", expand=True, padx=15, pady=(5, 5))

        if _HAS_MPL and self._timing_data:
            self._draw_chart(chart_frame)
        elif not _HAS_MPL:
            ctk.CTkLabel(chart_frame, text="(matplotlib 미설치 — 차트 비활성)",
                          text_color="gray").pack(expand=True)
        else:
            ctk.CTkLabel(chart_frame, text="(타이밍 데이터 없음)",
                          text_color="gray").pack(expand=True)

        ctk.CTkButton(self, text="닫기", width=100, command=self.destroy
                       ).pack(pady=(0, 10))

    def _draw_chart(self, parent):
        delays = [d for _, d, _ in self._timing_data]
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 2.8), dpi=90)
        fig.patch.set_facecolor("#2b2b2b")

        # 히스토그램
        ax1.set_facecolor("#333")
        ax1.hist(delays, bins=min(30, max(5, len(delays) // 3)),
                 color="#4CAF50", edgecolor="#2b2b2b", alpha=0.85)
        avg = sum(delays) / len(delays)
        ax1.axvline(avg, color="#FF9800", linestyle="--", linewidth=1.5,
                    label=f"avg {avg:.0f}ms")
        ax1.set_title("Delay Distribution", color="white", fontsize=10)
        ax1.set_xlabel("ms", color="white", fontsize=8)
        ax1.tick_params(colors="white", labelsize=7)
        ax1.legend(fontsize=7, facecolor="#333", edgecolor="#555", labelcolor="white")
        for s in ax1.spines.values():
            s.set_color("#555")

        # 시계열
        ax2.set_facecolor("#333")
        colors = []
        for _, _, bd in self._timing_data:
            if "newline" in bd:       colors.append("#FF5722")
            elif "inter_word" in bd:  colors.append("#2196F3")
            elif "punctuation" in bd: colors.append("#FF9800")
            elif "shift" in bd:       colors.append("#9C27B0")
            else:                     colors.append("#4CAF50")
        ax2.scatter(range(len(delays)), delays, c=colors, s=5, alpha=0.7)
        ax2.set_title("Per-Character Delay", color="white", fontsize=10)
        ax2.set_xlabel("index", color="white", fontsize=8)
        ax2.tick_params(colors="white", labelsize=7)
        for s in ax2.spines.values():
            s.set_color("#555")

        fig.tight_layout(pad=1.2)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._fig = fig

    def destroy(self):
        if self._fig and _HAS_MPL:
            plt.close(self._fig)
        super().destroy()
