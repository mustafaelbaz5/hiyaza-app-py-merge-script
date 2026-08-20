"""Displays detected association info (name/type/admin/directorate)."""

import customtkinter as ctk

from gui import theme


class InfoBadge(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master, fg_color=theme.PRIMARY_50, corner_radius=theme.RADIUS_CARD, **kwargs
        )
        self._rows: dict[str, ctk.CTkLabel] = {}
        self._title = ctk.CTkLabel(
            self, text="التعرف التلقائي", font=theme.FONT_HEADING, anchor="e",
            text_color=theme.PRIMARY_900,
        )
        self._title.pack(fill="x", padx=theme.PAD_M, pady=(theme.PAD_S, theme.PAD_XS))

        self._add_row("association", "الجمعية")
        self._add_row("type", "النوع")
        self._add_row("administration", "الإدارة")
        self._add_row("directorate", "المديرية")

        self.show_empty()

    def _add_row(self, key: str, label: str) -> None:
        row = ctk.CTkLabel(self, text=f"{label}: —", font=theme.FONT_BODY, anchor="e")
        row.pack(fill="x", padx=theme.PAD_M, pady=2)
        self._rows[key] = row
        self._labels = getattr(self, "_labels", {})
        self._labels[key] = label

    def show_empty(self) -> None:
        for key, row in self._rows.items():
            row.configure(text=f"{self._labels[key]}: —", text_color=theme.NEUTRAL_700)

    def show_detected(self, info: dict) -> None:
        type_label = "ائتمان زراعي" if info["association_type"] == "credit" else "إصلاح زراعي"
        values = {
            "association": info["association_name"],
            "type": type_label,
            "administration": info["administration"],
            "directorate": info["directorate"],
        }
        for key, value in values.items():
            self._rows[key].configure(
                text=f"✅ {self._labels[key]}: {value}", text_color=theme.SUCCESS
            )

    def show_error(self, message: str) -> None:
        for key, row in self._rows.items():
            row.configure(text=f"{self._labels[key]}: —", text_color=theme.NEUTRAL_700)
        self._rows["association"].configure(
            text=f"⚠️ {message}", text_color=theme.ERROR
        )
