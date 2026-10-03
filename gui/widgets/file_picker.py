"""Responsive file selection card."""

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from gui import theme


class FilePicker(ctk.CTkFrame):
    def __init__(
        self,
        master,
        label_text: str,
        hint_text: str,
        on_selected: Callable[[Path], None] | None = None,
        save_mode: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.SURFACE,
            corner_radius=theme.RADIUS_CARD,
            **kwargs,
        )
        self._on_selected = on_selected
        self._save_mode = save_mode
        self._path: Path | None = None
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=label_text, font=theme.FONT_HEADING, anchor="e").grid(
            row=0, column=0, sticky="ew", padx=theme.PAD_M, pady=(theme.PAD_M, 0)
        )
        ctk.CTkLabel(
            self,
            text=hint_text,
            font=theme.FONT_SMALL,
            text_color=theme.NEUTRAL_500,
            anchor="e",
        ).grid(row=1, column=0, sticky="ew", padx=theme.PAD_M, pady=(2, theme.PAD_S))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=theme.PAD_M, pady=(0, theme.PAD_M))
        row.grid_columnconfigure(0, weight=1)
        self._display = ctk.CTkEntry(row, state="disabled", font=theme.FONT_DATA)
        self._display.grid(row=0, column=0, sticky="ew")
        self._button = ctk.CTkButton(
            row, text="اختيار ملف", width=112, command=self._browse
        )
        self._button.grid(row=0, column=1, padx=(theme.PAD_S, 0))

    def _browse(self) -> None:
        selected = self._select_path()
        if not selected:
            return
        self.set_path(Path(selected))
        if self._on_selected and self._path:
            self._on_selected(self._path)

    def _select_path(self) -> str:
        if self._save_mode:
            return filedialog.asksaveasfilename(
                defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")]
            )
        return filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])

    def set_path(self, path: Path) -> None:
        self._path = path
        self._display.configure(state="normal")
        self._display.delete(0, "end")
        self._display.insert(0, path.name)
        self._display.configure(state="disabled")

    @property
    def path(self) -> Path | None:
        return self._path
