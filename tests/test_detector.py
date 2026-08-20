import openpyxl
import pytest

from core.detector import detect_association
from core.exceptions import DetectionError


def _write_approved_header(path, *, admin, directorate, assoc_name, sector):
    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(11):
        ws.append([None] * 32)
    admin_row = [None] * 32
    admin_row[3] = admin
    admin_row[19] = directorate
    ws.append(admin_row)
    ws.append([None] * 32)
    name_row = [None] * 32
    name_row[3] = assoc_name
    name_row[19] = sector
    ws.append(name_row)
    wb.save(path)


def test_detects_credit_association(tmp_path):
    path = tmp_path / "approved.xlsx"
    _write_approved_header(
        path,
        admin="اجا",
        directorate="الدقهليه",
        assoc_name="شنشا-الائتمان الزراعي",
        sector="الائتمان الزراعي",
    )
    result = detect_association(path)
    assert result["association_type"] == "credit"
    assert result["association_name"] == "شنشا-الائتمان الزراعي"
    assert result["administration"] == "اجا"
    assert result["directorate"] == "الدقهليه"


def test_detects_reform_association(tmp_path):
    path = tmp_path / "approved.xlsx"
    _write_approved_header(
        path,
        admin="اجا",
        directorate="الدقهليه",
        assoc_name="دروه-الإصلاح الزراعي",
        sector="الإصلاح الزراعي",
    )
    result = detect_association(path)
    assert result["association_type"] == "reform"


def test_raises_when_type_cannot_be_determined(tmp_path):
    path = tmp_path / "approved.xlsx"
    _write_approved_header(
        path, admin="اجا", directorate="الدقهليه", assoc_name="جمعية غامضة", sector=""
    )
    with pytest.raises(DetectionError):
        detect_association(path)


def test_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        detect_association(tmp_path / "missing.xlsx")
