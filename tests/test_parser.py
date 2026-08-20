import openpyxl

from core.parser import normalize_holding, parse_approved, parse_registered


def _write_registered(path, rows):
    """rows: list of (holding_number, holder_name, basin_name)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(10):
        ws.append([None] * 23)
    for holding, holder, basin in rows:
        line = [None] * 23
        line[0] = 0
        line[2] = 0
        line[3] = 0
        line[4] = "11996268"
        line[6] = "."
        line[7] = "."
        line[8] = "."
        line[9] = "."
        line[11] = "1"
        line[13] = holding
        line[14] = holder
        line[18] = basin
        line[19] = "شنشا-الائتمان الزراعي"
        line[20] = "اجا"
        line[21] = "الدقهليه"
        ws.append(line)
    wb.save(path)


def _write_approved(path, rows):
    """rows: list of (holding_number, holder_name)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(17):
        ws.append([None] * 24)
    for holding, holder in rows:
        line = [None] * 24
        line[2] = 1
        line[4] = 1
        line[8] = 0
        line[9] = 0
        line[11] = "06-3230-00323925-000001"
        line[17] = holding
        line[21] = "12345678901234"
        line[23] = holder
        ws.append(line)
    wb.save(path)


def test_normalize_holding_strips_leading_zeros():
    assert normalize_holding("0048") == "48"
    assert normalize_holding("048") == "48"
    assert normalize_holding("48") == "48"


def test_normalize_holding_handles_non_numeric():
    assert normalize_holding("nan") == "nan"
    assert normalize_holding(None) == "None"


def test_summary_row_removed_when_repeated_across_many_basins(tmp_path):
    basins = [f"basin_{i}" for i in range(13)]
    rows = [("935", "فلان الفلاني", b) for b in basins]
    rows.append(("10", "شخص عادي", "basin_0"))
    path = tmp_path / "registered.xlsx"
    _write_registered(path, rows)

    df = parse_registered(path)
    assert "935" not in df["holding_number"].values
    assert "10" in df["holding_number"].values
    assert len(df) == 1


def test_summary_threshold_not_triggered_below_13_basins(tmp_path):
    basins = [f"basin_{i}" for i in range(5)]
    rows = [("935", "فلان الفلاني", b) for b in basins]
    path = tmp_path / "registered.xlsx"
    _write_registered(path, rows)

    df = parse_registered(path)
    assert len(df) == 5
    assert set(df["holding_number"]) == {"935"}


def test_empty_holding_rows_removed(tmp_path):
    rows = [("48", "شخص", "basin_0"), ("", "", "")]
    path = tmp_path / "registered.xlsx"
    _write_registered(path, rows)

    df = parse_registered(path)
    assert len(df) == 1


def test_basin_typo_corrected(tmp_path):
    rows = [("48", "شخص", "داير الناصيه**")]
    path = tmp_path / "registered.xlsx"
    _write_registered(path, rows)

    df = parse_registered(path)
    assert df.iloc[0]["basin_name"] == "داير الناحيه"


def test_parse_approved_basic(tmp_path):
    rows = [("48", "شخص"), ("49", "شخص اخر")]
    path = tmp_path / "approved.xlsx"
    _write_approved(path, rows)

    df = parse_approved(path)
    assert len(df) == 2
    assert set(df["holding_number"]) == {"48", "49"}


def test_parse_registered_handles_short_trailing_row(tmp_path):
    """openpyxl trims trailing empty cells from a row's tuple when the last
    populated cell in that row is earlier than the sheet's overall last
    column — fixed-index lookups must not raise IndexError on such rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(10):
        ws.append([None] * 23)
    full_row = [None] * 23
    full_row[4] = "11996268"
    full_row[13] = "48"
    full_row[14] = "شخص كامل"
    full_row[18] = "basin_0"
    full_row[19] = "شنشا-الائتمان الزراعي"
    full_row[20] = "اجا"
    full_row[21] = "الدقهليه"
    ws.append(full_row)
    # A row whose last non-empty cell is holding_number (index 13) — openpyxl
    # will only materialize 14 cells for it, not the full 23.
    short_row = [None] * 14
    short_row[4] = "11996269"
    short_row[13] = "49"
    ws.append(short_row)
    path = tmp_path / "registered.xlsx"
    wb.save(path)

    df = parse_registered(path)
    assert "49" in df["holding_number"].values
    assert len(df) == 2
