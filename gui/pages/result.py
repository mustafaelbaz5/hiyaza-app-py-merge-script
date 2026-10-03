"""Scrollable merge status and manual-review page."""

import os
import platform
import subprocess
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from core.merger import UNKNOWN_NATIONAL_ID, is_valid_national_id
from gui import theme
from gui.widgets.progress_bar import LabeledProgressBar


class ResultPage(ctk.CTkScrollableFrame):
    def __init__(self, master, on_new_merge: Callable[[], None], **kwargs) -> None:
        super().__init__(master, fg_color=theme.SURFACE_MUTED, **kwargs)
        self._on_new_merge = on_new_merge
        self._on_save_manual_ids: Callable[[dict[int, str]], None] | None = None
        self._output_path: Path | None = None
        self._entries: dict[int, ctk.CTkEntry] = {}
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
        self._log_toggle = ctk.CTkButton(self, text="إظهار سجل العمليات", command=self._toggle_log, fg_color="transparent", text_color=theme.PRIMARY_700)
        self._log_toggle.grid(row=4, column=0, sticky="e", padx=theme.PAD_L, pady=(0, theme.PAD_XS))
        self._log = ctk.CTkTextbox(self, height=120, font=theme.FONT_SMALL, state="disabled")
        self._review = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_CARD)
        self._actions = ctk.CTkFrame(self, fg_color="transparent")
        self._actions.grid(row=7, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_M, theme.PAD_XL))
        self._actions.grid_columnconfigure(0, weight=1)
        self._save = ctk.CTkButton(self._actions, text="حفظ الأرقام القومية المدخلة", command=self._save_manual_ids, state="disabled")
        self._save.grid(row=0, column=0, sticky="ew")
        buttons = ctk.CTkFrame(self._actions, fg_color="transparent")
        buttons.grid(row=1, column=0, sticky="e", pady=(theme.PAD_S, 0))
        self._open = ctk.CTkButton(buttons, text="فتح ملف الناتج", command=self._open_output, state="disabled")
        self._open.grid(row=0, column=0, padx=(0, theme.PAD_S))
        ctk.CTkButton(buttons, text="دمج جديد", command=self._on_new_merge).grid(row=0, column=1)

    def reset(self) -> None:
        self._progress.reset()
        self._message.configure(text="", text_color=theme.NEUTRAL_700)
        self._summary.configure(text="")
        self._output_path = None
        self._on_save_manual_ids = None
        self._entries = {}
        self._review.grid_forget()
        self._log.grid_forget()
        self._log_toggle.configure(text="إظهار سجل العمليات")
        self._open.configure(state="disabled")
        self._save.configure(state="disabled")
        self._set_log("")

    def update_progress(self, fraction: float, message: str) -> None:
        self._progress.update_progress(fraction, message)
        self.show_message(message, theme.INFO)

    def append_log(self, message: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", f"{message}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def show_success(self, summary: dict, on_save_manual_ids: Callable[[dict[int, str]], None]) -> None:
        self._output_path = summary["output_path"]
        self._on_save_manual_ids = on_save_manual_ids
        parcels = summary["result"].parcels
        review_count = sum(parcel.national_id == UNKNOWN_NATIONAL_ID for parcel in parcels)
        match_rate = self._match_rate(summary)
        self._summary.configure(text=(f"إجمالي القطع: {summary['parcel_count']}  |  الأحواض: {summary['basin_count']}\nنسبة الربط: {match_rate:.0f}%  |  تحتاج مراجعة: {review_count}"))
        self.show_message("اكتمل الدمج. راجع الحالات اليدوية إن وُجدت ثم احفظ.", theme.SUCCESS)
        self._render_review_table(parcels)
        self._open.configure(state="normal")

    def refresh_review_table(self, parcels, applied: int) -> None:
        self._render_review_table(parcels)
        remaining = sum(parcel.national_id == UNKNOWN_NATIONAL_ID for parcel in parcels)
        self.show_message(f"تم حفظ {applied} رقم قومي يدويًا. المتبقي للمراجعة: {remaining}.", theme.SUCCESS)

    def show_message(self, message: str, color: str) -> None:
        self._message.configure(text=message, text_color=color)

    def set_saving(self, is_saving: bool) -> None:
        self._save.configure(state="disabled" if is_saving else "normal")
        if is_saving:
            self.show_message("جارٍ حفظ التصحيحات في ملف Excel...", theme.INFO)

    def _render_review_table(self, parcels) -> None:
        for child in self._review.winfo_children():
            child.destroy()
        self._entries = {}
        items = [(i, parcel) for i, parcel in enumerate(parcels) if parcel.national_id == UNKNOWN_NATIONAL_ID]
        if not items:
            self._review.grid_forget()
            self._save.configure(state="disabled")
            return
        self._review.grid(row=5, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_M)
        self._review.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._review, text=f"حالات تحتاج مراجعة يدوية ({len(items)})", font=theme.FONT_HEADING, anchor="e").grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_M, theme.PAD_S))
        body = ctk.CTkScrollableFrame(self._review, height=240, fg_color=theme.SURFACE_MUTED)
        body.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))
        body.grid_columnconfigure(0, weight=1)
        for row, (index, parcel) in enumerate(items):
            self._add_review_row(body, row, index, parcel)
        self._save.configure(state="normal")

    def _add_review_row(self, parent, row: int, index: int, parcel) -> None:
        item = ctk.CTkFrame(parent, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_BUTTON)
        item.grid(row=row, column=0, sticky="ew", padx=theme.PAD_S, pady=theme.PAD_XS)
        item.grid_columnconfigure(0, weight=1)
        details = f"الحيازة: {parcel.holding_number} | الحائز: {parcel.holder_name}\nالقطعة: {parcel.land_number} | الحوض: {parcel.basin_name}"
        ctk.CTkLabel(item, text=details, font=theme.FONT_BODY, justify="right", anchor="e").grid(row=0, column=0, sticky="ew", padx=theme.PAD_S, pady=theme.PAD_S)
        ctk.CTkButton(
            item,
            text="نسخ الاسم",
            width=76,
            command=lambda: self._copy_text(parcel.holder_name, "اسم الحائز"),
        ).grid(row=0, column=1, padx=(0, theme.PAD_S))
        ctk.CTkButton(
            item,
            text="نسخ الحيازة",
            width=88,
            command=lambda: self._copy_text(parcel.holding_number, "رقم الحيازة"),
        ).grid(row=0, column=2, padx=(0, theme.PAD_S))
        entry = ctk.CTkEntry(item, width=160, placeholder_text="الرقم القومي (14 رقمًا)")
        entry.grid(row=0, column=3, padx=(0, theme.PAD_S))
        self._entries[index] = entry

    def _save_manual_ids(self) -> None:
        updates, invalid = self._collect_updates()
        if invalid:
            self.show_message("أدخل رقمًا قوميًّا مكوّنًا من 14 رقمًا في كل خانة مستخدمة.", theme.ERROR)
            return
        if not updates:
            self.show_message("أدخل رقمًا قوميًّا واحدًا على الأقل للحفظ.", theme.WARNING)
            return
        if self._on_save_manual_ids:
            self._on_save_manual_ids(updates)

    def _collect_updates(self) -> tuple[dict[int, str], bool]:
        updates = {}
        invalid = False
        for index, entry in self._entries.items():
            value = entry.get().strip()
            if not value:
                continue
            is_valid = is_valid_national_id(value)
            entry.configure(border_color=theme.NEUTRAL_300 if is_valid else theme.ERROR)
            if is_valid:
                updates[index] = value
            else:
                invalid = True
        return updates, invalid

    def _copy_text(self, value: str, label: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self.show_message(f"تم نسخ {label}.", theme.INFO)

    def _toggle_log(self) -> None:
        if self._log.winfo_ismapped():
            self._log.grid_forget()
            self._log_toggle.configure(text="إظهار سجل العمليات")
        else:
            self._log.grid(row=6, column=0, sticky="ew", padx=theme.PAD_L, pady=(0, theme.PAD_S))
            self._log_toggle.configure(text="إخفاء سجل العمليات")

    def _match_rate(self, summary: dict) -> float:
        total = summary["parcel_count"]
        return ((total - summary["unmatched_count"]) / total * 100) if total else 0

    def _set_log(self, text: str) -> None:
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
