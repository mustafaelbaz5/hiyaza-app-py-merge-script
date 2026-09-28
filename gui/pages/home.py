"""Home page: file selection + auto-detect panel."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

import customtkinter as ctk

from core.detector import detect_association
from core.exceptions import MergerError
from gui import theme
from gui.widgets.file_picker import FilePicker
from gui.widgets.info_badge import InfoBadge


class HomePage(ctk.CTkFrame):
    def __init__(
        self, master, on_start: Callable[[Path, Path, Path, dict], None], **kwargs
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_start = on_start
        self._detected_info: dict | None = None

        self._build_title()
        self._registered_picker = FilePicker(
            self, "📄 ملف المسجل (الحيازات الزراعية المسجلة)"
        )
        self._registered_picker.pack(fill="x", padx=theme.PAD_L, pady=theme.PAD_S)

        self._approved_picker = FilePicker(
            self, "📋 ملف المعتمد (حيازات الجمعية المعتمدة)", on_selected=self._on_approved_selected
        )
        self._approved_picker.pack(fill="x", padx=theme.PAD_L, pady=theme.PAD_S)

        self._info_badge = InfoBadge(self)
        self._info_badge.pack(fill="x", padx=theme.PAD_L, pady=theme.PAD_M)

        self._output_picker = FilePicker(
            self, "💾 مكان حفظ الملف الناتج", save_mode=True
        )
        self._output_picker.pack(fill="x", padx=theme.PAD_L, pady=theme.PAD_S)

        self._start_button = ctk.CTkButton(
            self, text="ابدأ الدمج  →", height=44, command=self._handle_start
        )
        self._start_button.pack(pady=theme.PAD_L)

    def _build_title(self) -> None:
        title = ctk.CTkLabel(
            self, text=f"🌾  {theme.WINDOW_TITLE}", font=theme.FONT_TITLE
        )
        title.pack(pady=(theme.PAD_L, theme.PAD_M))

    def _on_approved_selected(self, path: Path) -> None:
        try:
            info = detect_association(path)
        except MergerError as e:
            self._info_badge.show_error(str(e))
            self._detected_info = None
            return
        except FileNotFoundError:
            self._info_badge.show_error("الملف غير موجود")
            self._detected_info = None
            return

        self._detected_info = info
        self._info_badge.show_detected(info)
        self._suggest_output_path(path, info)

    def _suggest_output_path(self, approved_path: Path, info: dict) -> None:
        city_name = info["association_name"].split("-")[0].strip()
        association_type_name = {
            "credit": "\u0627\u0626\u062a\u0645\u0627\u0646",
            "reform": "\u0627\u0635\u0644\u0627\u062d",
        }.get(info["association_type"], info["association_type"])
        today = date.today().isoformat()
        base_dir = theme.OUTPUT_BASE_DIRS.get(info["association_type"], approved_path.parent)
        suggested = base_dir / f"{city_name}_مدمج_{today}.xlsx"
        suggested = base_dir / f"{city_name}_\u0645\u062f\u0645\u062c_{association_type_name}_{today}.xlsx"
        self._output_picker.set_path(suggested)

    def _handle_start(self) -> None:
        registered_path = self._registered_picker.path
        approved_path = self._approved_picker.path
        output_path = self._output_picker.path

        if not (registered_path and approved_path and output_path and self._detected_info):
            return

        self._on_start(registered_path, approved_path, output_path, self._detected_info)
