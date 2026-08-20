"""Entry point: loads reference codes and launches the GUI."""

import logging
from pathlib import Path

import customtkinter as ctk

from core.codes import CodesDB
from gui.app import App

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    credit_path = base_dir / "data" / "اكواد_ائتمان.xlsx"
    reform_path = base_dir / "data" / "اكواد_اصلاح.xlsx"

    codes_db = CodesDB(credit_path, reform_path)

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")

    app = App(codes_db=codes_db)
    app.mainloop()
