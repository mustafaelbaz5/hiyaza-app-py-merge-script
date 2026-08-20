import pandas as pd

from core.codes import CodesDB
from core.merger import merge
from core.models import AssociationInfo, AssociationType


def _make_association_info(codes_files) -> AssociationInfo:
    db = CodesDB(*codes_files)
    return db.find_association("شنشا-الائتمان الزراعي", AssociationType.CREDIT)


def _registered_df(rows):
    """rows: list of dict with holding_number, holder_name, basin_name."""
    defaults = {
        "land_number": "12345678",
        "registry_page": "1",
        "association_name": "شنشا-الائتمان الزراعي",
        "administration": "اجا",
        "directorate": "الدقهليه",
        "border_north": ".",
        "border_west": ".",
        "border_south": ".",
        "border_east": ".",
    }
    return pd.DataFrame.from_records([{**defaults, **r} for r in rows])


def _approved_df(rows):
    """rows: list of dict with holding_number, holder_name, feddan/qirat/sahm."""
    defaults = {
        "parcel_count": 1,
        "feddan": 0.0,
        "qirat": 0.0,
        "sahm": 0.0,
        "unified_holding_id": "06-3230-00323925-000001",
        "national_id": "12345678901234",
    }
    return pd.DataFrame.from_records([{**defaults, **r} for r in rows])


def test_full_match_by_holding_and_name(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)

    registered = _registered_df(
        [{"holding_number": "48", "holder_name": "احمد محمد", "basin_name": "الدماسه"}]
    )
    approved = _approved_df(
        [
            {
                "holding_number": "48",
                "holder_name": "احمد محمد",
                "feddan": 1.0,
                "qirat": 2.0,
                "sahm": 3.0,
            }
        ]
    )

    result = merge(registered, approved, db, info)
    assert result.unmatched_count == 0
    assert len(result.parcels) == 1
    parcel = result.parcels[0]
    assert parcel.area_feddan == 1.0
    assert parcel.national_id == "12345678901234"
    assert parcel.unified_holding_id == "06-3230-00323925-000001"


def test_nothing_dropped_when_unmatched(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)

    registered = _registered_df(
        [{"holding_number": "99", "holder_name": "شخص مجهول", "basin_name": "الدماسه"}]
    )
    approved = _approved_df([])

    result = merge(registered, approved, db, info)
    assert len(result.parcels) == 1
    assert result.unmatched_count == 1
    parcel = result.parcels[0]
    assert parcel.area_feddan == 0.0
    assert parcel.national_id == ""
    assert len(result.warnings) == 1


def test_parcel_count_matches_registered_input(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)

    registered = _registered_df(
        [
            {"holding_number": "1", "holder_name": "أ", "basin_name": "الدماسه"},
            {"holding_number": "2", "holder_name": "ب", "basin_name": "الدماسه"},
            {"holding_number": "3", "holder_name": "ج", "basin_name": "الدماسه"},
        ]
    )
    approved = _approved_df([])

    result = merge(registered, approved, db, info)
    assert len(result.parcels) == len(registered)


def test_ambiguous_holding_uses_name_to_disambiguate(codes_files):
    """Same holding_number shared by two different holders in a joint holding —
    each row must get its own area, not a blended/incorrect one."""
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)

    registered = _registered_df(
        [
            {"holding_number": "5", "holder_name": "شخص اول", "basin_name": "الدماسه"},
            {"holding_number": "5", "holder_name": "شخص ثاني", "basin_name": "الدماسه"},
        ]
    )
    approved = _approved_df(
        [
            {"holding_number": "5", "holder_name": "شخص اول", "feddan": 1.0},
            {"holding_number": "5", "holder_name": "شخص ثاني", "feddan": 2.0},
        ]
    )

    result = merge(registered, approved, db, info)
    by_name = {p.holder_name: p.area_feddan for p in result.parcels}
    assert by_name["شخص اول"] == 1.0
    assert by_name["شخص ثاني"] == 2.0
