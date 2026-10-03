"""Association detection status card."""

import customtkinter as ctk

from gui import theme


class InfoBadge(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            fg_color=theme.PRIMARY_50,
            corner_radius=theme.RADIUS_CARD,
            **kwargs,
        )
        self.grid_columnconfigure(0, weight=1)
        self._title = ctk.CTkLabel(self, font=theme.FONT_HEADING, anchor="e")
        self._title.grid(row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_M, 4))
        self._details = ctk.CTkLabel(self, font=theme.FONT_BODY, anchor="e", justify="right")
        self._details.grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))
        self.show_empty()

    def show_empty(self) -> None:
        self._title.configure(text="بيانات الجمعية", text_color=theme.NEUTRAL_700)
        self._details.configure(
            text="اختر ملف المعتمد لقراءة بيانات الجمعية تلقائيًا.",
            text_color=theme.NEUTRAL_500,
        )

    def show_detected(self, info: dict) -> None:
        type_label = "ائتمان زراعي" if info["association_type"] == "credit" else "إصلاح زراعي"
        self._title.configure(text="تم التعرف على الجمعية", text_color=theme.SUCCESS)
        self._details.configure(
            text=(
                f"الجمعية: {info['association_name']}\n"
                f"النوع: {type_label}  |  الإدارة: {info['administration']}  |  المديرية: {info['directorate']}"
            ),
            text_color=theme.NEUTRAL_900,
        )

    def show_error(self, message: str) -> None:
        self._title.configure(text="تعذر قراءة بيانات الجمعية", text_color=theme.ERROR)
        self._details.configure(text=message, text_color=theme.ERROR)
