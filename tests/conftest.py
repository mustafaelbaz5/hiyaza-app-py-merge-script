"""Shared pytest fixtures — synthetic Excel files, no real data."""

import openpyxl
import pytest

CODE_HEADER_ROW = 8  # 1-based row where header labels live
CODE_DATA_START_ROW = 10  # 1-based first data row


def _write_codes_file(path, rows):
    """rows: list of (basin_code, basin_name, assoc_code, assoc_name, admin_code,
    admin_name, directorate_code, directorate_name)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in range(1, CODE_DATA_START_ROW):
        ws.append([None] * 26)
    for row in rows:
        basin_code, basin_name, assoc_code, assoc_name, admin_code, admin_name, dir_code, dir_name = row
        line = [None] * 26
        line[15] = basin_code
        line[16] = basin_name
        line[18] = assoc_code
        line[19] = assoc_name
        line[21] = admin_code
        line[22] = admin_name
        line[23] = dir_code
        line[24] = dir_name
        ws.append(line)
    wb.save(path)


@pytest.fixture
def codes_files(tmp_path):
    credit_path = tmp_path / "credit_codes.xlsx"
    reform_path = tmp_path / "reform_codes.xlsx"

    _write_codes_file(
        credit_path,
        [
            (
                "06323000003239000001",
                "الدماسه",
                "323925",
                "شنشا-الائتمان الزراعي",
                "3230",
                "اجا",
                "6",
                "الدقهليه",
            ),
            (
                "06323000003239000012",
                "داير الناصيه**",
                "323925",
                "شنشا-الائتمان الزراعي",
                "3230",
                "اجا",
                "6",
                "الدقهليه",
            ),
        ],
    )
    _write_codes_file(
        reform_path,
        [
            (
                "06111000001111000001",
                "حوض الإصلاح",
                "111111",
                "جمعية إصلاح تجريبية",
                "1000",
                "ادارة",
                "1",
                "مديرية",
            ),
        ],
    )
    return credit_path, reform_path
