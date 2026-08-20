"""Result page: progress log + final summary + actions."""

import os
import platform
import subprocess
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from gui import theme
from gui.widgets.progress_bar import LabeledProgressBar


class ResultPage(ctk.CTkFrame):
    def __init__(self, master, on_new_merge: Callable[[], None], **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_new_merge = on_new_merge
        self._output_path: Path | None = None

        title = ctk.CTkLabel(self, text=f"🌾  {theme.WINDOW_TITLE}", font=theme.FONT_TITLE)
        title.pack(pady=(theme.PAD_L, theme.PAD_M))

        self._progress = LabeledProgressBar(self)
        self._progress.pack(fill="x", padx=theme.PAD_L, pady=theme.PAD_S)

        self._log_box = ctk.CTkTextbox(self, height=180, font=theme.FONT_SMALL)
        self._log_box.pack(fill="both", expand=True, padx=theme.PAD_L, pady=theme.PAD_S)
        self._log_box.configure(state="disabled")

        self._summary_label = ctk.CTkLabel(
            self, text="", font=theme.FONT_BODY, anchor="e", justify="right"
        )
        self._summary_label.pack(fill="x", padx=theme.PAD_L, pady=theme.PAD_S)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(pady=theme.PAD_M)

        self._open_button = ctk.CTkButton(
            actions, text="فتح الملف ↗", command=self._open_output, state="disabled"
        )
        self._open_button.pack(side="right", padx=theme.PAD_S)

        self._new_button = ctk.CTkButton(
            actions, text="← دمج جديد", command=self._on_new_merge
        )
        self._new_button.pack(side="right", padx=theme.PAD_S)

    def reset(self) -> None:
        self._progress.reset()
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        self._summary_label.configure(text="")
        self._open_button.configure(state="disabled")
        self._output_path = None

    def update_progress(self, fraction: float, message: str) -> None:
        self._progress.update_progress(fraction, message)

    def append_log(self, message: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"{message}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def show_success(self, output_path: Path, parcel_count: int, basin_count: int, match_rate: float) -> None:
        self._output_path = output_path
        self._summary_label.configure(
            text=(
                f"📊 إجمالي القطع: {parcel_count}\n"
                f"🏞️ عدد الأحواض: {basin_count}\n"
                f"🔗 نسبة الربط: {match_rate:.0f}%"
            ),
            text_color=theme.SUCCESS,
        )
        self._open_button.configure(state="normal")

    def show_error(self, message: str) -> None:
        self._summary_label.configure(text=f"❌ {message}", text_color=theme.ERROR)

    def _open_output(self) -> None:
        if not self._output_path:
            return
        if platform.system() == "Windows":
            os.startfile(self._output_path)
        else:
            opener = "open" if platform.system() == "Darwin" else "xdg-open"
            subprocess.run([opener, str(self._output_path)], check=False)
