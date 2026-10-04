"""Person-sized manual review for basin codes with no fuzzy matching."""

from collections.abc import Callable

import customtkinter as ctk

from core.merger import ManualReviewBasin, build_manual_review_basins
from core.models import BasinInfo
from gui import theme


class BasinReviewTable(ctk.CTkFrame):
    def __init__(self, master, on_status: Callable[[str, str], None], **kwargs) -> None:
        super().__init__(master, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_CARD, **kwargs)
        self._on_status = on_status
        self._items: list[ManualReviewBasin] = []
        self._choices: dict[str, BasinInfo] = {}
        self._drafts: dict[str, str] = {}
        self.grid_columnconfigure(0, weight=1)
        self._title = ctk.CTkLabel(self, font=theme.FONT_HEADING, anchor="e")
        self._title.grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_M, theme.PAD_S))
        self._body = ctk.CTkScrollableFrame(self, height=220, fg_color=theme.SURFACE_MUTED)
        self._body.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))
        self._body.grid_columnconfigure(0, weight=1)

    @property
    def count(self) -> int:
        return len(self._items)

    @property
    def has_items(self) -> bool:
        return bool(self._items)

    def clear(self) -> None:
        self._items = []
        self._choices = {}
        self._drafts = {}
        self._render()

    def set_data(self, parcels, basins: list[BasinInfo]) -> None:
        self._items = build_manual_review_basins(parcels)
        self._choices = {self._label(basin): basin for basin in basins}
        valid_names = {item.raw_name for item in self._items}
        self._drafts = {name: label for name, label in self._drafts.items() if name in valid_names}
        self._render()

    def valid_updates(self) -> dict[str, BasinInfo]:
        return {
            raw_name: self._choices[label]
            for raw_name, label in self._drafts.items()
            if label in self._choices
        }

    def _render(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()
        self._title.configure(text=f"أحواض تحتاج تحديدًا يدويًا ({self.count})")
        labels = ["اختر الحوض الرسمي"] + list(self._choices)
        for row, item in enumerate(self._items):
            self._add_row(row, item, labels)

    def _add_row(self, row: int, item: ManualReviewBasin, labels: list[str]) -> None:
        card = ctk.CTkFrame(self._body, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_BUTTON)
        card.grid(row=row, column=0, sticky="ew", padx=theme.PAD_S, pady=theme.PAD_XS)
        card.grid_columnconfigure(0, weight=1)
        text = f"الاسم الخام: {item.raw_name}\nعدد القطع: {len(item.parcel_indexes)} | السبب: {item.reason}"
        ctk.CTkLabel(card, text=text, font=theme.FONT_BODY, justify="right", anchor="e").grid(
            row=0, column=0, sticky="ew", padx=theme.PAD_S, pady=theme.PAD_S
        )
        ctk.CTkButton(card, text="نسخ الاسم", width=76, command=lambda: self._copy(item.raw_name)).grid(
            row=0, column=1, padx=(0, theme.PAD_S)
        )
        selected = self._drafts.get(item.raw_name, labels[0])
        picker = ctk.CTkOptionMenu(
            card, values=labels, width=250,
            command=lambda label, raw=item.raw_name: self._set_draft(raw, label),
        )
        picker.set(selected)
        picker.grid(row=0, column=2, padx=(0, theme.PAD_S))

    def _set_draft(self, raw_name: str, label: str) -> None:
        if label in self._choices:
            self._drafts[raw_name] = label
        else:
            self._drafts.pop(raw_name, None)

    def _copy(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self._on_status("تم نسخ اسم الحوض الخام.", theme.INFO)

    @staticmethod
    def _label(basin: BasinInfo) -> str:
        return f"{basin.code} — {basin.name}"
