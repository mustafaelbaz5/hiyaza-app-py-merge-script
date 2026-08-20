"""Reusable file-selection row: label + path display + browse button."""

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
        on_selected: Callable[[Path], None] | None = None,
        save_mode: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_selected = on_selected
        self._save_mode = save_mode
        self._path: Path | None = None

        self._label = ctk.CTkLabel(
            self, text=label_text, font=theme.FONT_BODY, anchor="e"
        )
        self._label.pack(fill="x", pady=(0, theme.PAD_XS))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        self._button = ctk.CTkButton(
            row, text="اختر ملف", width=90, command=self._browse
        )
        self._button.pack(side="right", padx=(theme.PAD_S, 0))

        self._display = ctk.CTkEntry(row, placeholder_text="لم يتم اختيار ملف")
        self._display.pack(side="right", fill="x", expand=True)
        self._display.configure(state="disabled")

    def _browse(self) -> None:
        if self._save_mode:
            selected = filedialog.asksaveasfilename(
                defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")]
            )
        else:
            selected = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])

        if not selected:
            return

        self.set_path(Path(selected))
        if self._on_selected:
            self._on_selected(self._path)

    def set_path(self, path: Path) -> None:
        self._path = path
        self._display.configure(state="normal")
        self._display.delete(0, "end")
        self._display.insert(0, path.name)
        self._display.configure(state="disabled")

    @property
    def path(self) -> Path | None:
        return self._path
