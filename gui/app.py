"""Main CTk window — wires the home/result pages together with the merge runner."""

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

        self.title(theme.WINDOW_TITLE)
        self.geometry(f"{theme.WINDOW_WIDTH}x{theme.WINDOW_HEIGHT}")
        self.resizable(False, False)

        self._home_page = HomePage(self, on_start=self._handle_start)
        self._result_page = ResultPage(self, on_new_merge=self._show_home)

        self._show_home()

    def _show_home(self) -> None:
        self._result_page.pack_forget()
        self._result_page.reset()
        self._home_page.pack(fill="both", expand=True)

    def _show_result(self) -> None:
        self._home_page.pack_forget()
        self._result_page.pack(fill="both", expand=True)

    def _handle_start(
        self, registered_path: Path, approved_path: Path, output_path: Path, detected_info: dict
    ) -> None:
        self._show_result()
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
        if error is not None:
            self._result_page.append_log(f"❌ {error}")
            self._result_page.show_error(str(error))
            return

        matched = summary["parcel_count"] - summary["unmatched_count"]
        match_rate = (
            (matched / summary["parcel_count"]) * 100 if summary["parcel_count"] else 0
        )
        self._result_page.show_success(
            summary["output_path"], summary["parcel_count"], summary["basin_count"], match_rate
        )
