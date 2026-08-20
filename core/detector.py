"""Detects association metadata from the approved holdings file header."""

from pathlib import Path

import openpyxl

from core.exceptions import DetectionError

_ROW_ADMIN_DIRECTORATE = 12  # 1-based
_ROW_NAME_TYPE = 14  # 1-based
_COL_ADMIN_NAME = 3  # 0-based
_COL_DIRECTORATE_NAME = 19  # 0-based
_COL_ASSOC_NAME = 3  # 0-based
_COL_SECTOR = 19  # 0-based


def detect_association(approved_path: Path) -> dict:
    """
    Reads the approved file header rows to extract:
    - association name  (row 14, col 3)
    - association type  (row 14, col 19 → "ائتمان" or "إصلاح")
    - administration    (row 12, col 3)
    - directorate       (row 12, col 19)

    Returns raw dict. Does NOT load codes or validate.
    Raises: FileNotFoundError, DetectionError (if type cannot be determined)
    """
    path = Path(approved_path)
    if not path.exists():
        raise FileNotFoundError(f"ملف المعتمد غير موجود: {path.name}")

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    admin_row = _get_row(ws, _ROW_ADMIN_DIRECTORATE)
    name_row = _get_row(ws, _ROW_NAME_TYPE)

    administration = _clean(admin_row[_COL_ADMIN_NAME])
    directorate = _clean(admin_row[_COL_DIRECTORATE_NAME])
    association_name = _clean(name_row[_COL_ASSOC_NAME])
    sector = _clean(name_row[_COL_SECTOR])

    association_type = _classify_type(sector, association_name)
    if association_type is None:
        raise DetectionError(
            "تعذر تحديد نوع الجمعية (ائتمان / إصلاح) من ملف المعتمد"
        )
    if not association_name:
        raise DetectionError("تعذر قراءة اسم الجمعية من ملف المعتمد")

    return {
        "association_name": association_name,
        "association_type": association_type,
        "directorate": directorate,
        "administration": administration,
    }


def _get_row(ws, row_number: int) -> tuple:
    for row in ws.iter_rows(min_row=row_number, max_row=row_number, values_only=True):
        return row
    raise DetectionError("ملف المعتمد لا يحتوي على صفوف كافية لقراءة بيانات الجمعية")


def _clean(value) -> str:
    return str(value).strip() if value is not None else ""


def _classify_type(sector: str, association_name: str) -> str | None:
    combined = f"{sector} {association_name}"
    if "ائتمان" in combined:
        return "credit"
    if "إصلاح" in combined or "اصلاح" in combined:
        return "reform"
    return None
