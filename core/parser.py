"""Parses and cleans the registered and approved holdings Excel files."""

import logging
from pathlib import Path

import openpyxl
import pandas as pd

from core.exceptions import ParseError

logger = logging.getLogger(__name__)

# Registered file: data starts row 11 (1-based) = index 10 (0-based).
_REGISTERED_DATA_START_ROW = 11
_REGISTERED_COLUMNS = {
    "feddan": 0,
    "qirat": 2,
    "sahm": 3,
    "land_number": 4,
    "border_north": 6,
    "border_west": 7,
    "border_south": 8,
    "border_east": 9,
    "registry_page": 11,
    "holding_number": 13,
    "holder_name": 14,
    "basin_name": 18,
    "association_name": 19,
    "administration": 20,
    "directorate": 21,
}

_SUMMARY_ROW_BASIN_THRESHOLD = 13

_TYPO_CORRECTIONS = {
    "داير الناصيه": "داير الناحيه",
}

# Approved file: data starts row 18 (1-based) = index 17 (0-based).
_APPROVED_DATA_START_ROW = 18
_APPROVED_COLUMNS = {
    "parcel_count": 2,
    "feddan": 4,
    "qirat": 8,
    "sahm": 9,
    "unified_holding_id": 11,
    "holding_number": 17,
    "national_id": 21,
    "holder_name": 23,
}


def normalize_holding(value) -> str:
    """Return the holding number as text without changing its representation.

    Preserve leading zeros in text cells (``0048``, ``048``), including
    values such as ``0`` and ``00``. Numeric Excel cells are converted to
    natural text because Excel has already discarded leading zeros.
    """
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _normalize_basin_name(name) -> str:
    cleaned = str(name).strip().rstrip("*").strip() if name is not None else ""
    return _TYPO_CORRECTIONS.get(cleaned, cleaned)


def _clean(value) -> str:
    return str(value).strip() if value is not None else ""


def normalize_holder_name(value) -> str:
    """Normalize harmless Arabic spelling variants for matching only."""
    name = _clean(value)
    replacements = str.maketrans({
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
    })
    name = name.translate(replacements)
    return " ".join(name.split())


def _to_number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_rows(path: Path, start_row: int, min_columns: int) -> list[tuple]:
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except (FileNotFoundError, PermissionError) as e:
        raise ParseError(f"لا يمكن فتح الملف: {Path(path).name}") from e
    except Exception as e:
        logger.exception("Unexpected error opening workbook %s", path)
        raise ParseError(f"حدث خطأ غير متوقع أثناء قراءة الملف: {Path(path).name}") from e

    ws = wb.active
    rows = ws.iter_rows(min_row=start_row, values_only=True)
    return [_pad_row(row, min_columns) for row in rows]


def _pad_row(row: tuple, min_length: int) -> tuple:
    """openpyxl trims trailing empty cells from a row's tuple; pad it back
    out so fixed-index column lookups never raise IndexError."""
    if len(row) >= min_length:
        return row
    return row + (None,) * (min_length - len(row))


def parse_registered(path: Path) -> pd.DataFrame:
    """
    Reads the registered parcels file.
    - Data starts at row index 10 (0-based)
    - Removes empty rows
    - Detects and removes summary rows (holding repeated across >=13 basins)
    - Normalizes holding numbers, fixes basin name typos
    """
    min_columns = max(_REGISTERED_COLUMNS.values()) + 1
    rows = _read_rows(path, _REGISTERED_DATA_START_ROW, min_columns)
    records = []
    for row in rows:
        holding_raw = row[_REGISTERED_COLUMNS["holding_number"]]
        if holding_raw is None or str(holding_raw).strip() == "":
            continue
        records.append(
            {
                "feddan": _to_number(row[_REGISTERED_COLUMNS["feddan"]]),
                "qirat": _to_number(row[_REGISTERED_COLUMNS["qirat"]]),
                "sahm": _to_number(row[_REGISTERED_COLUMNS["sahm"]]),
                "holding_number": normalize_holding(holding_raw),
                "holder_name": _clean(row[_REGISTERED_COLUMNS["holder_name"]]),
                "land_number": _clean(row[_REGISTERED_COLUMNS["land_number"]]),
                "registry_page": _clean(row[_REGISTERED_COLUMNS["registry_page"]]),
                "basin_name": _normalize_basin_name(row[_REGISTERED_COLUMNS["basin_name"]]),
                "association_name": _clean(row[_REGISTERED_COLUMNS["association_name"]]),
                "administration": _clean(row[_REGISTERED_COLUMNS["administration"]]),
                "directorate": _clean(row[_REGISTERED_COLUMNS["directorate"]]),
                "border_north": _clean(row[_REGISTERED_COLUMNS["border_north"]]),
                "border_west": _clean(row[_REGISTERED_COLUMNS["border_west"]]),
                "border_south": _clean(row[_REGISTERED_COLUMNS["border_south"]]),
                "border_east": _clean(row[_REGISTERED_COLUMNS["border_east"]]),
            }
        )

    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df
    return _detect_and_remove_summary_rows(df)


def _detect_and_remove_summary_rows(df: pd.DataFrame) -> pd.DataFrame:
    """A holding that appears in >= 13 distinct basins is a system-generated
    total row (repeated once per basin), not real parcel data — drop it."""
    basin_counts = df.groupby("holding_number")["basin_name"].nunique()
    summary_holdings = basin_counts[basin_counts >= _SUMMARY_ROW_BASIN_THRESHOLD].index
    if len(summary_holdings) > 0:
        logger.info("Removing summary rows for holdings: %s", list(summary_holdings))
    return df[~df["holding_number"].isin(summary_holdings)].reset_index(drop=True)


def parse_approved(path: Path) -> pd.DataFrame:
    """
    Reads the approved holdings file.
    - Data starts at row index 17 (0-based)
    - Normalizes holding numbers
    """
    min_columns = max(_APPROVED_COLUMNS.values()) + 1
    rows = _read_rows(path, _APPROVED_DATA_START_ROW, min_columns)
    records = []
    for row in rows:
        holding_raw = row[_APPROVED_COLUMNS["holding_number"]]
        if holding_raw is None or str(holding_raw).strip() == "":
            continue
        records.append(
            {
                "holding_number": normalize_holding(holding_raw),
                "holder_name": _clean(row[_APPROVED_COLUMNS["holder_name"]]),
                "parcel_count": int(_to_number(row[_APPROVED_COLUMNS["parcel_count"]])),
                "feddan": _to_number(row[_APPROVED_COLUMNS["feddan"]]),
                "qirat": _to_number(row[_APPROVED_COLUMNS["qirat"]]),
                "sahm": _to_number(row[_APPROVED_COLUMNS["sahm"]]),
                "unified_holding_id": _clean(row[_APPROVED_COLUMNS["unified_holding_id"]]),
                "national_id": _clean(row[_APPROVED_COLUMNS["national_id"]]),
            }
        )
    return pd.DataFrame.from_records(records)
