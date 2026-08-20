"""Custom progress bar with a step label above it."""

import customtkinter as ctk

from gui import theme


class LabeledProgressBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)

        self._label = ctk.CTkLabel(
            self, text="", font=theme.FONT_BODY, anchor="e", text_color=theme.NEUTRAL_700
        )
        self._label.pack(fill="x", pady=(0, theme.PAD_XS))

        self._bar = ctk.CTkProgressBar(self, progress_color=theme.PRIMARY_700)
        self._bar.pack(fill="x")
        self._bar.set(0)

    def update_progress(self, fraction: float, message: str) -> None:
        self._bar.set(max(0.0, min(1.0, fraction)))
        self._label.configure(text=message)

    def reset(self) -> None:
        self._bar.set(0)
        self._label.configure(text="")
