"""Scrollable start page for selecting merge inputs."""

from collections.abc import Callable
from datetime import date
from pathlib import Path

import customtkinter as ctk

from core.detector import detect_association
from core.exceptions import MergerError
from gui import theme
from gui.widgets.file_picker import FilePicker
from gui.widgets.info_badge import InfoBadge


class HomePage(ctk.CTkScrollableFrame):
    def __init__(
        self, master, on_start: Callable[[Path, Path, Path, dict], None], **kwargs
    ) -> None:
        super().__init__(master, fg_color=theme.SURFACE_MUTED, **kwargs)
        self._on_start = on_start
        self._detected_info: dict | None = None
        self.grid_columnconfigure(0, weight=1)
        self._build_header()
        self._build_inputs()
        self._build_actions()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_XL, theme.PAD_M))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text=theme.WINDOW_TITLE, font=theme.FONT_TITLE, anchor="e").grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkLabel(
            header,
            text="اختر ملفي المسجل والمعتمد ثم راجع بيانات الجمعية قبل بدء الدمج.",
            font=theme.FONT_BODY,
            text_color=theme.NEUTRAL_700,
            anchor="e",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

    def _build_inputs(self) -> None:
        self._registered_picker = FilePicker(
            self,
            "ملف المسجل",
            "القطع والحيازات المسجلة التي ستكون أساس ملف الناتج.",
            on_selected=self._update_readiness,
        )
        self._registered_picker.grid(row=1, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_S)
        self._approved_picker = FilePicker(
            self,
            "ملف المعتمد",
            "الأرقام القومية وبيانات الحائزين المعتمدة.",
            on_selected=self._on_approved_selected,
        )
        self._approved_picker.grid(row=2, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_S)
        self._info_badge = InfoBadge(self)
        self._info_badge.grid(row=3, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_S)
        self._output_picker = FilePicker(
            self,
            "مكان حفظ ملف الناتج",
            "سيتم إنشاء أو تحديث ملف Excel في المكان الذي تختاره.",
            on_selected=self._update_readiness,
            save_mode=True,
        )
        self._output_picker.grid(row=4, column=0, sticky="ew", padx=theme.PAD_L, pady=theme.PAD_S)

    def _build_actions(self) -> None:
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=5, column=0, sticky="ew", padx=theme.PAD_L, pady=(theme.PAD_M, theme.PAD_XL))
        actions.grid_columnconfigure(0, weight=1)
        self._ready_label = ctk.CTkLabel(
            actions, text="أكمل اختيار الملفات لبدء الدمج.", font=theme.FONT_SMALL, text_color=theme.NEUTRAL_500, anchor="e"
        )
        self._ready_label.grid(row=0, column=0, sticky="ew", pady=(0, theme.PAD_S))
        self._start_button = ctk.CTkButton(
            actions, text="بدء الدمج", height=46, command=self._handle_start, state="disabled"
        )
        self._start_button.grid(row=1, column=0, sticky="ew")

    def _on_approved_selected(self, path: Path) -> None:
        try:
            self._detected_info = detect_association(path)
        except MergerError as error:
            self._detected_info = None
            self._info_badge.show_error(str(error))
        except FileNotFoundError:
            self._detected_info = None
            self._info_badge.show_error("ملف المعتمد غير موجود.")
        else:
            self._info_badge.show_detected(self._detected_info)
            self._suggest_output_path(path)
        self._update_readiness()

    def _suggest_output_path(self, approved_path: Path) -> None:
        info = self._detected_info
        if info is None:
            return
        city_name = info["association_name"].split("-")[0].strip()
        type_name = "ائتمان" if info["association_type"] == "credit" else "اصلاح"
        base_dir = theme.OUTPUT_BASE_DIRS.get(info["association_type"], approved_path.parent)
        filename = f"{city_name}_مدمج_{type_name}_{date.today().isoformat()}.xlsx"
        self._output_picker.set_path(base_dir / filename)

    def _update_readiness(self, _path: Path | None = None) -> None:
        is_ready = bool(
            self._registered_picker.path
            and self._approved_picker.path
            and self._output_picker.path
            and self._detected_info
        )
        self._start_button.configure(state="normal" if is_ready else "disabled")
        text = "الملفات جاهزة للدمج." if is_ready else "أكمل اختيار الملفات لبدء الدمج."
        color = theme.SUCCESS if is_ready else theme.NEUTRAL_500
        self._ready_label.configure(text=text, text_color=color)

    def _handle_start(self) -> None:
        if not self._detected_info:
            return
        self._on_start(
            self._registered_picker.path,
            self._approved_picker.path,
            self._output_picker.path,
            self._detected_info,
        )
