import pandas as pd

from core.codes import CodesDB
from core.merger import merge
from core.models import AssociationInfo, AssociationType


def _make_association_info(codes_files) -> AssociationInfo:
    db = CodesDB(*codes_files)
    return db.find_association("شنشا-الائتمان الزراعي", AssociationType.CREDIT)


def _registered_df(rows):
    """rows: list of dict with holding_number, holder_name, basin_name, area fields."""
    defaults = {
        "feddan": 0.0,
        "qirat": 0.0,
        "sahm": 0.0,
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
        [
            {
                "holding_number": "48",
                "holder_name": "احمد محمد",
                "basin_name": "الدماسه",
                "feddan": 1.0,
                "qirat": 2.0,
                "sahm": 3.0,
            }
        ]
    )
    approved = _approved_df(
        [
            {
                "holding_number": "48",
                "holder_name": "احمد محمد",
                "feddan": 10.0,  # Different from registered (should be ignored)
                "qirat": 20.0,
                "sahm": 30.0,
            }
        ]
    )

    result = merge(registered, approved, db, info)
    assert result.unmatched_count == 0
    assert len(result.parcels) == 1
    parcel = result.parcels[0]
    assert parcel.area_feddan == 1.0  # From registered, NOT approved
    assert parcel.area_qirat == 2.0
    assert parcel.area_sahm == 3.0
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
    assert parcel.national_id == "11111111111111"
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


def test_same_holding_number_uses_matching_holder_data(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [
            {"holding_number": "50", "holder_name": "Ø£", "basin_name": "Ø§Ù„Ø¯Ù…Ø§Ø³Ù‡"},
            {"holding_number": "50", "holder_name": "Ø¨", "basin_name": "Ø§Ù„Ø¯Ù…Ø§Ø³Ù‡"},
        ]
    )
    approved = _approved_df(
        [
            {"holding_number": "50", "holder_name": "Ø£", "national_id": "11111111111111"},
            {"holding_number": "50", "holder_name": "Ø¨", "national_id": "22222222222222"},
        ]
    )

    result = merge(registered, approved, db, info)

    assert [p.national_id for p in result.parcels] == [
        "11111111111111",
        "22222222222222",
    ]
    assert result.unmatched_count == 0


def test_name_spelling_variants_still_match(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [{"holding_number": "50", "holder_name": "محمد علي", "basin_name": "الدماسه"}]
    )
    approved = _approved_df(
        [{"holding_number": "50", "holder_name": "محمد على", "national_id": "22222222222222"}]
    )

    result = merge(registered, approved, db, info)

    assert result.parcels[0].national_id == "22222222222222"
    assert result.unmatched_count == 0


def test_first_four_name_words_can_match_different_last_name(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [{"holding_number": "1021", "holder_name": "محمد علي محمد الشحات السيد", "basin_name": "الدماسه"}]
    )
    approved = _approved_df(
        [{"holding_number": "1021", "holder_name": "محمد على محمد الشحات شاهين", "national_id": "29510251202211"}]
    )

    result = merge(registered, approved, db, info)

    assert result.parcels[0].national_id == "29510251202211"
    assert result.parcels[0].holder_name == "محمد على محمد الشحات شاهين"
    assert result.unmatched_count == 0


def test_missing_holder_gets_unknown_national_id_even_if_holding_exists(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [{"holding_number": "50", "holder_name": "Ø¬", "basin_name": "Ø§Ù„Ø¯Ù…Ø§Ø³Ù‡"}]
    )
    approved = _approved_df(
        [{"holding_number": "50", "holder_name": "Ø£", "national_id": "22222222222222"}]
    )

    result = merge(registered, approved, db, info)

    assert result.parcels[0].national_id == "11111111111111"
    assert result.unmatched_count == 1


def test_conflicting_duplicate_person_ids_get_unknown_id_without_stopping_merge(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [{"holding_number": "546", "holder_name": "Ø£", "basin_name": "Ø§Ù„Ø¯Ù…Ø§Ø³Ù‡"}]
    )
    approved = _approved_df(
        [
            {"holding_number": "546", "holder_name": "Ø£", "national_id": "22222222222222"},
            {"holding_number": "546", "holder_name": "Ø£", "national_id": "33333333333333"},
        ]
    )

    result = merge(registered, approved, db, info)

    assert result.parcels[0].national_id == "11111111111111"
    assert result.unmatched_count == 0


def test_multiple_parcels_same_holding_get_individual_areas(codes_files):
    """Multiple parcels from registered file for same holding get their own
    individual areas from registered, NOT the person's total from approved."""
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)

    registered = _registered_df(
        [
            {
                "holding_number": "5",
                "holder_name": "شخص",
                "basin_name": "الدماسه",
                "feddan": 5.0,
            },
            {
                "holding_number": "5",
                "holder_name": "شخص",
                "basin_name": "الدماسه",
                "feddan": 4.0,
            },
            {
                "holding_number": "5",
                "holder_name": "شخص",
                "basin_name": "الدماسه",
                "feddan": 6.0,
            },
        ]
    )
    approved = _approved_df(
        [
            {
                "holding_number": "5",
                "holder_name": "شخص",
                "feddan": 15.0,  # Person's total area for all 3 parcels
            }
        ]
    )

    result = merge(registered, approved, db, info)
    assert len(result.parcels) == 3
    areas = [p.area_feddan for p in result.parcels]
    assert areas == [5.0, 4.0, 6.0]  # From registered, NOT [15, 15, 15]
    assert sum(areas) == 15.0  # Sum matches approved person's total (but distributed correctly)
