"""Scrollable merge status and manual-review page."""

import os
import platform
import subprocess
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from gui import theme
from gui.widgets.progress_bar import LabeledProgressBar
from gui.widgets.review_table import ReviewTable


class ResultPage(ctk.CTkScrollableFrame):
    def __init__(self, master, on_new_merge: Callable[[], None], **kwargs) -> None:
        super().__init__(master, fg_color=theme.SURFACE_MUTED, **kwargs)
        self._on_new_merge = on_new_merge
        self._on_save_manual_ids: Callable[[dict, str], None] | None = None
        self._output_path: Path | None = None
        self.grid_columnconfigure(0, weight=1)
        self._build_layout()

    def _build_layout(self) -> None:
        ctk.CTkLabel(self, text="نتيجة الدمج", font=theme.FONT_TITLE, anchor="e").grid(
            row=0, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_XL, theme.PAD_S)
        )
        self._message = ctk.CTkLabel(self, text="", font=theme.FONT_BODY, anchor="e")
        self._message.grid(row=1, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_M))
        self._progress = LabeledProgressBar(self)
        self._progress.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_S)
        self._summary = ctk.CTkLabel(self, text="", font=theme.FONT_BODY, anchor="e", justify="right")
        self._summary.grid(row=3, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_S)
        self._build_log()
        self._review = ReviewTable(self, on_status=self.show_message)
        self._build_actions()

    def _build_log(self) -> None:
        self._log_toggle = ctk.CTkButton(
            self, text="إظهار سجل العمليات", command=self._toggle_log,
            fg_color="transparent", text_color=theme.PRIMARY_700,
        )
        self._log_toggle.grid(row=4, column=0, sticky="e", padx=theme.PAD_L, pady=(0, theme.PAD_XS))
        self._log = ctk.CTkTextbox(self, height=120, font=theme.FONT_SMALL, state="disabled")

    def _build_actions(self) -> None:
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=7, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_M, theme.PAD_XL))
        actions.grid_columnconfigure(0, weight=1)
        self._save = ctk.CTkButton(actions, text="حفظ الأرقام القومية المدخلة", command=self._save_manual_ids, state="disabled")
        self._save.grid(row=0, column=0, sticky="ew")
        buttons = ctk.CTkFrame(actions, fg_color="transparent")
        buttons.grid(row=1, column=0, sticky="e", pady=(theme.PAD_S, 0))
        self._open = ctk.CTkButton(buttons, text="فتح ملف الناتج", command=self._open_output, state="disabled")
        self._open.grid(row=0, column=0, padx=(0, theme.PAD_S))
        ctk.CTkButton(buttons, text="دمج جديد", command=self._on_new_merge).grid(row=0, column=1)

    def reset(self) -> None:
        self._progress.reset()
        self._summary.configure(text="")
        self._output_path = None
        self._on_save_manual_ids = None
        self._review.clear()
        self._review.grid_forget()
        self._log.grid_forget()
        self._log_toggle.configure(text="إظهار سجل العمليات")
        self._open.configure(state="disabled")
        self._save.configure(state="disabled")
        self._replace_log("")
        self.show_message("", theme.NEUTRAL_700)

    def update_progress(self, fraction: float, message: str) -> None:
        self._progress.update_progress(fraction, message)
        self.show_message(message, theme.INFO)

    def append_log(self, message: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", f"{message}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def show_success(self, summary: dict, on_save_manual_ids: Callable[[dict, str], None]) -> None:
        self._output_path = summary["output_path"]
        self._on_save_manual_ids = on_save_manual_ids
        parcels = summary["result"].parcels
        self._summary.configure(text=self._summary_text(summary, parcels))
        self._review.set_parcels(parcels)
        if self._review.has_items:
            self._review.grid(row=5, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_M)
            self._save.configure(state="normal")
        self.show_message("اكتمل الدمج. راجع الحالات اليدوية إن وُجدت ثم احفظ.", theme.SUCCESS)
        self._open.configure(state="normal")

    def refresh_review_table(self, parcels, applied: int, people_saved: int) -> None:
        self._review.set_parcels(parcels)
        self._save.configure(state="normal" if self._review.has_items else "disabled")
        if not self._review.has_items:
            self._review.grid_forget()
        self.show_message(
            f"تم حفظ أرقام {people_saved} شخص وتحديث {applied} قطعة. المتبقي للمراجعة: {self._review.count}.",
            theme.SUCCESS,
        )

    def show_message(self, message: str, color: str) -> None:
        self._message.configure(text=message, text_color=color)

    def set_saving(self, is_saving: bool) -> None:
        self._save.configure(state="disabled" if is_saving else "normal")
        if is_saving:
            self.show_message("جارٍ حفظ التصحيحات في ملف Excel...", theme.INFO)

    def _save_manual_ids(self) -> None:
        updates, error = self._review.valid_updates()
        if error:
            self.show_message(error, theme.ERROR)
        elif updates and self._on_save_manual_ids:
            self._on_save_manual_ids(updates)
        else:
            self.show_message("أدخل رقمًا قوميًّا واحدًا على الأقل للحفظ.", theme.WARNING)

    def _summary_text(self, summary: dict, parcels) -> str:
        total = summary["parcel_count"]
        rate = ((total - summary["unmatched_count"]) / total * 100) if total else 0
        return f"إجمالي القطع: {total}  |  الأحواض: {summary['basin_count']}\nنسبة الربط: {rate:.0f}%  |  تحتاج مراجعة: {self._review.count_for(parcels)}"

    def _toggle_log(self) -> None:
        if self._log.winfo_ismapped():
            self._log.grid_forget()
            self._log_toggle.configure(text="إظهار سجل العمليات")
        else:
            self._log.grid(row=6, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_S))
            self._log_toggle.configure(text="إخفاء سجل العمليات")

    def _replace_log(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.insert("end", text)
        self._log.configure(state="disabled")

    def _open_output(self) -> None:
        if not self._output_path:
            return
        if platform.system() == "Windows":
            os.startfile(self._output_path)
        else:
            opener = "open" if platform.system() == "Darwin" else "xdg-open"
            subprocess.run([opener, str(self._output_path)], check=False)
