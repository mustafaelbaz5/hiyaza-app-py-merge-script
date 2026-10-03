"""Paged, stateful table for manual national-ID review."""

from collections.abc import Callable

import customtkinter as ctk

from core.merger import UNKNOWN_NATIONAL_ID, is_valid_national_id
from gui import theme

PAGE_SIZE = 25


class ReviewTable(ctk.CTkFrame):
    def __init__(self, master, on_status: Callable[[str, str], None], **kwargs) -> None:
        super().__init__(master, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_CARD, **kwargs)
        self._on_status = on_status
        self._items = []
        self._draft_ids: dict[int, str] = {}
        self._page = 0
        self.grid_columnconfigure(0, weight=1)
        self._build_layout()

    @property
    def count(self) -> int:
        return len(self._items)

    @property
    def has_items(self) -> bool:
        return bool(self._items)

    def count_for(self, parcels) -> int:
        return sum(parcel.national_id == UNKNOWN_NATIONAL_ID for parcel in parcels)

    def clear(self) -> None:
        self._items = []
        self._draft_ids = {}
        self._page = 0
        self._render_page()

    def set_parcels(self, parcels) -> None:
        self._items = [
            (index, parcel)
            for index, parcel in enumerate(parcels)
            if parcel.national_id == UNKNOWN_NATIONAL_ID
        ]
        valid_indexes = {index for index, _ in self._items}
        self._draft_ids = {index: value for index, value in self._draft_ids.items() if index in valid_indexes}
        self._page = min(self._page, self._page_count() - 1)
        self._render_page()

    def valid_updates(self) -> tuple[dict[int, str], str | None]:
        updates = {index: value for index, value in self._draft_ids.items() if is_valid_national_id(value)}
        if len(updates) != len(self._draft_ids):
            return {}, "أدخل رقمًا قوميًّا مكوّنًا من 14 رقمًا في كل خانة مستخدمة."
        return updates, None

    def _build_layout(self) -> None:
        self._title = ctk.CTkLabel(self, font=theme.FONT_HEADING, anchor="e")
        self._title.grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_M, theme.PAD_S))
        self._body = ctk.CTkScrollableFrame(self, height=260, fg_color=theme.SURFACE_MUTED)
        self._body.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_S))
        self._body.grid_columnconfigure(0, weight=1)
        pager = ctk.CTkFrame(self, fg_color="transparent")
        pager.grid(row=2, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))
        pager.grid_columnconfigure(1, weight=1)
        self._next = ctk.CTkButton(pager, text="التالي", width=78, command=lambda: self._change_page(1))
        self._next.grid(row=0, column=0)
        self._page_label = ctk.CTkLabel(pager, text="", font=theme.FONT_SMALL)
        self._page_label.grid(row=0, column=1)
        self._previous = ctk.CTkButton(pager, text="السابق", width=78, command=lambda: self._change_page(-1))
        self._previous.grid(row=0, column=2)

    def _render_page(self) -> None:
        for child in self._body.winfo_children():
            child.destroy()
        self._title.configure(text=f"حالات تحتاج مراجعة يدوية ({self.count})")
        start = self._page * PAGE_SIZE
        for row, (index, parcel) in enumerate(self._items[start:start + PAGE_SIZE]):
            self._add_row(row, index, parcel)
        pages = self._page_count()
        self._page_label.configure(text=f"صفحة {self._page + 1} من {pages}")
        self._previous.configure(state="normal" if self._page else "disabled")
        self._next.configure(state="normal" if self._page + 1 < pages else "disabled")

    def _add_row(self, row: int, index: int, parcel) -> None:
        item = ctk.CTkFrame(self._body, fg_color=theme.SURFACE, corner_radius=theme.RADIUS_BUTTON)
        item.grid(row=row, column=0, sticky="ew", padx=theme.PAD_S, pady=theme.PAD_XS)
        item.grid_columnconfigure(0, weight=1)
        details = f"الحيازة: {parcel.holding_number} | الحائز: {parcel.holder_name}\nالقطعة: {parcel.land_number} | الحوض: {parcel.basin_name}"
        ctk.CTkLabel(item, text=details, font=theme.FONT_BODY, justify="right", anchor="e").grid(row=0, column=0, sticky="ew", padx=theme.PAD_S, pady=theme.PAD_S)
        ctk.CTkButton(item, text="نسخ الاسم", width=76, command=lambda: self._copy(parcel.holder_name, "اسم الحائز")).grid(row=0, column=1, padx=(0, theme.PAD_S))
        ctk.CTkButton(item, text="نسخ الحيازة", width=88, command=lambda: self._copy(parcel.holding_number, "رقم الحيازة")).grid(row=0, column=2, padx=(0, theme.PAD_S))
        entry = ctk.CTkEntry(item, width=160, placeholder_text="الرقم القومي (14 رقمًا)")
        entry.insert(0, self._draft_ids.get(index, ""))
        entry.bind("<KeyRelease>", lambda _event, i=index, field=entry: self._remember_draft(i, field))
        entry.grid(row=0, column=3, padx=(0, theme.PAD_S))

    def _remember_draft(self, index: int, entry: ctk.CTkEntry) -> None:
        value = entry.get().strip()
        if value:
            self._draft_ids[index] = value
        else:
            self._draft_ids.pop(index, None)

    def _change_page(self, direction: int) -> None:
        self._page = max(0, min(self._page + direction, self._page_count() - 1))
        self._render_page()

    def _page_count(self) -> int:
        return max(1, (self.count + PAGE_SIZE - 1) // PAGE_SIZE)

    def _copy(self, value: str, label: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self._on_status(f"تم نسخ {label}.", theme.INFO)
