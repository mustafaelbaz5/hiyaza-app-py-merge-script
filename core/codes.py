"""Loads reference code files (association/basin codes) and provides lookups."""

import logging
import re
from pathlib import Path

import openpyxl
import pandas as pd

from core.models import AssociationInfo, AssociationType, BasinInfo

logger = logging.getLogger(__name__)

# Header spans two rows (labels row 8, units row 9, 1-based); data starts row 10.
_DATA_START_ROW = 10  # 1-based, matches openpyxl min_row
_COL_BASIN_CODE = 15
_COL_BASIN_NAME = 16
_COL_ASSOC_CODE = 18
_COL_ASSOC_NAME = 19
_COL_ADMIN_CODE = 21
_COL_ADMIN_NAME = 22
_COL_DIRECTORATE_CODE = 23
_COL_DIRECTORATE_NAME = 24

_TYPO_CORRECTIONS = {
    "داير الناصيه": "داير الناحيه",
}


def _normalize_basin_name(name: str) -> str:
    """Strips whitespace/asterisks and applies known typo corrections."""
    cleaned = str(name).strip().rstrip("*").strip()
    return _TYPO_CORRECTIONS.get(cleaned, cleaned)


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip())


def _code_to_str(value) -> str:
    """Renders a code cell (possibly a float/int) as a plain string, no precision loss."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _load_code_table(path: Path) -> pd.DataFrame:
    """Reads the raw sheet via openpyxl to preserve long numeric codes as text
    (pandas' default engine coerces them to float64, losing precision beyond
    ~15 significant digits — basin codes are 20 digits long)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    records = []
    for row in ws.iter_rows(min_row=_DATA_START_ROW, values_only=True):
        if not row[_COL_ASSOC_NAME] or not row[_COL_BASIN_NAME]:
            continue
        records.append(
            {
                "basin_code": _code_to_str(row[_COL_BASIN_CODE]),
                "basin_name": _normalize_basin_name(row[_COL_BASIN_NAME]),
                "assoc_code": _code_to_str(row[_COL_ASSOC_CODE]),
                "assoc_name": _normalize_name(row[_COL_ASSOC_NAME]),
                "admin_code": _code_to_str(row[_COL_ADMIN_CODE]),
                "admin_name": _normalize_name(row[_COL_ADMIN_NAME]),
                "directorate_code": _code_to_str(row[_COL_DIRECTORATE_CODE]),
                "directorate_name": _normalize_name(row[_COL_DIRECTORATE_NAME]),
            }
        )
    return pd.DataFrame.from_records(records)


class CodesDB:
    """Loads both code files once on init. Lookups are case/typo tolerant."""

    def __init__(self, credit_path: Path, reform_path: Path) -> None:
        self._tables = {
            AssociationType.CREDIT: _load_code_table(Path(credit_path)),
            AssociationType.REFORM: _load_code_table(Path(reform_path)),
        }

    def _table(self, assoc_type: AssociationType) -> pd.DataFrame:
        return self._tables[assoc_type]

    def find_association(
        self, name: str, assoc_type: AssociationType
    ) -> AssociationInfo | None:
        table = self._table(assoc_type)
        target = _normalize_name(name)

        exact = table[table["assoc_name"] == target]
        match = exact.iloc[0] if not exact.empty else self._partial_match(table, target)
        if match is None:
            logger.warning("Association not found: %s (%s)", name, assoc_type)
            return None

        return AssociationInfo(
            name=match["assoc_name"],
            type=assoc_type,
            code=match["assoc_code"],
            directorate=match["directorate_name"],
            administration=match["admin_name"],
        )

    @staticmethod
    def _partial_match(table: pd.DataFrame, target: str) -> pd.Series | None:
        mask = table["assoc_name"].apply(
            lambda candidate: target in candidate or candidate in target
        )
        candidates = table[mask]
        return candidates.iloc[0] if not candidates.empty else None

    def get_basins(
        self, assoc_code: str, assoc_type: AssociationType
    ) -> list[BasinInfo]:
        table = self._table(assoc_type)
        rows = table[table["assoc_code"] == str(assoc_code)]
        rows = rows.drop_duplicates(subset=["basin_code"]).sort_values("basin_code")
        return [BasinInfo(name=r.basin_name, code=r.basin_code) for r in rows.itertuples()]

    def find_basin_code(
        self, basin_name: str, assoc_code: str, assoc_type: AssociationType
    ) -> str:
        table = self._table(assoc_type)
        target = _normalize_basin_name(basin_name)
        rows = table[table["assoc_code"] == str(assoc_code)]

        exact = rows[rows["basin_name"] == target]
        if not exact.empty:
            return exact.iloc[0]["basin_code"]

        partial = rows[
            rows["basin_name"].apply(lambda c: target in c or c in target)
        ]
        if not partial.empty:
            return partial.iloc[0]["basin_code"]

        logger.warning("Basin code not found: %s (assoc %s)", basin_name, assoc_code)
        return "غير محدد"
