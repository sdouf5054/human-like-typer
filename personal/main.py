"""
Human-Like Typer — 메인 진입점.
GUI 애플리케이션을 실행한다.
"""

import customtkinter as ctk
from gui.app import App


def main():
    # 테마 설정
    ctk.set_appearance_mode("dark")   # "dark" / "light" / "system"
    ctk.set_default_color_theme("blue")

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
