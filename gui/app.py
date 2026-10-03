"""Application window and asynchronous workflow wiring."""

from pathlib import Path

import customtkinter as ctk

from core.codes import CodesDB
from gui import theme
from gui.merge_runner import MergeRunner
from gui.pages.home import HomePage
from gui.pages.result import ResultPage


class App(ctk.CTk):
    def __init__(self, codes_db: CodesDB) -> None:
        super().__init__()
        self._runner = MergeRunner(codes_db)
        self._merge_result = None
        self._output_path: Path | None = None
        self.title(theme.WINDOW_TITLE)
        self.geometry(f"{theme.WINDOW_WIDTH}x{theme.WINDOW_HEIGHT}")
        self.minsize(theme.WINDOW_MIN_WIDTH, theme.WINDOW_MIN_HEIGHT)
        self.configure(fg_color=theme.SURFACE_MUTED)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._home_page = HomePage(self, on_start=self._handle_start)
        self._result_page = ResultPage(self, on_new_merge=self._show_home)
        self._show_home()

    def _show_home(self) -> None:
        self._result_page.grid_remove()
        self._result_page.reset()
        self._merge_result = None
        self._output_path = None
        self._home_page.grid(row=0, column=0, sticky="nsew")

    def _show_result(self) -> None:
        self._home_page.grid_remove()
        self._result_page.grid(row=0, column=0, sticky="nsew")

    def _handle_start(
        self, registered_path: Path, approved_path: Path, output_path: Path, detected_info: dict
    ) -> None:
        self._show_result()
        self._result_page.reset()
        self._runner.run_async(
            registered_path,
            approved_path,
            output_path,
            detected_info,
            on_progress=self._on_progress,
            on_done=self._on_done,
        )

    def _on_progress(self, fraction: float, message: str) -> None:
        self.after(0, self._apply_progress, fraction, message)

    def _apply_progress(self, fraction: float, message: str) -> None:
        self._result_page.update_progress(fraction, message)
        self._result_page.append_log(message)

    def _on_done(self, summary: dict | None, error: Exception | None) -> None:
        self.after(0, self._apply_done, summary, error)

    def _apply_done(self, summary: dict | None, error: Exception | None) -> None:
        if error:
            self._result_page.show_message(str(error), theme.ERROR)
            return
        self._merge_result = summary["result"]
        self._output_path = summary["output_path"]
        self._result_page.show_success(summary, self._save_manual_ids)

    def _save_manual_ids(self, updates: dict[int, str]) -> None:
        if not self._merge_result or not self._output_path:
            self._result_page.show_message("تعذر العثور على نتيجة الدمج للحفظ.", theme.ERROR)
            return
        self._result_page.set_saving(True)
        self._runner.save_manual_ids_async(
            self._merge_result,
            self._output_path,
            updates,
            on_done=self._on_manual_save_done,
        )

    def _on_manual_save_done(self, summary: dict | None, error: Exception | None) -> None:
        self.after(0, self._apply_manual_save_done, summary, error)

    def _apply_manual_save_done(self, summary: dict | None, error: Exception | None) -> None:
        if error:
            self._result_page.show_message(str(error), theme.ERROR)
            self._result_page.set_saving(False)
            return
        self._result_page.refresh_review_table(self._merge_result.parcels, summary["applied"])
