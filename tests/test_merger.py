import pandas as pd
import pytest

from core.codes import CodesDB
from core.merger import (
    UNKNOWN_NATIONAL_ID,
    apply_manual_national_ids,
    apply_manual_basin_codes,
    build_manual_review_basins,
    build_manual_review_people,
    is_valid_national_id,
    merge,
)
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


def test_first_four_name_words_are_suggested_for_manual_review(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [{"holding_number": "1021", "holder_name": "محمد علي محمد الشحات السيد", "basin_name": "الدماسه"}]
    )
    approved = _approved_df(
        [{"holding_number": "1021", "holder_name": "محمد على محمد الشحات شاهين", "national_id": "29510251202211"}]
    )

    result = merge(registered, approved, db, info)

    parcel = result.parcels[0]
    assert parcel.national_id == UNKNOWN_NATIONAL_ID
    assert parcel.suggested_national_id == "29510251202211"
    assert parcel.suggested_holder_name == "محمد على محمد الشحات شاهين"
    assert result.unmatched_count == 1


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


def test_manual_national_id_replaces_unknown_value_only(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [
            {"holding_number": "50", "holder_name": "غير موجود", "basin_name": "الدماسه"},
            {"holding_number": "51", "holder_name": "حائز معتمد", "basin_name": "الدماسه"},
        ]
    )
    approved = _approved_df(
        [{"holding_number": "51", "holder_name": "حائز معتمد", "national_id": "27812251200234"}]
    )
    result = merge(registered, approved, db, info)

    person = build_manual_review_people(result.parcels)[0]
    applied = apply_manual_national_ids(result, {person.key: "29510251202211"})

    assert applied == 1
    assert result.parcels[0].national_id == "29510251202211"
    assert result.parcels[1].national_id == "27812251200234"


def test_manual_id_updates_all_parcels_for_one_registered_person(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [
            {"holding_number": "50", "holder_name": "غير موجود", "land_number": "1", "basin_name": "الدماسه"},
            {"holding_number": "50", "holder_name": "غير موجود", "land_number": "2", "basin_name": "الدماسه"},
            {"holding_number": "50", "holder_name": "شخص آخر", "land_number": "3", "basin_name": "الدماسه"},
        ]
    )
    result = merge(registered, _approved_df([]), db, info)

    people = build_manual_review_people(result.parcels)
    assert len(people) == 2
    assert len(people[0].parcel_indexes) == 2

    applied = apply_manual_national_ids(result, {people[0].key: "29510251202211"})
    assert applied == 2
    assert [parcel.national_id for parcel in result.parcels] == [
        "29510251202211", "29510251202211", UNKNOWN_NATIONAL_ID,
    ]


def test_leading_zero_holding_is_not_the_same_holding(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [{"holding_number": "0048", "holder_name": "احمد محمد", "basin_name": "الدماسه"}]
    )
    approved = _approved_df(
        [{"holding_number": "48", "holder_name": "احمد محمد", "national_id": "29510251202211"}]
    )

    result = merge(registered, approved, db, info)
    assert result.parcels[0].holding_number == "0048"
    assert result.parcels[0].national_id == UNKNOWN_NATIONAL_ID


def test_unmatched_basin_stays_unresolved_until_manually_selected(codes_files):
    info = _make_association_info(codes_files)
    db = CodesDB(*codes_files)
    registered = _registered_df(
        [
            {"holding_number": "1", "holder_name": "شخص", "basin_name": "داير الناصيه"},
            {"holding_number": "2", "holder_name": "شخص", "basin_name": "داير الناصيه"},
        ]
    )
    result = merge(registered, _approved_df([]), db, info)

    reviews = build_manual_review_basins(result.parcels)
    assert len(reviews) == 1
    assert len(reviews[0].parcel_indexes) == 2
    assert result.parcels[0].basin_code == "غير محدد"

    official = next(basin for basin in result.basins if basin.name == "داير الناصيه**")
    applied = apply_manual_basin_codes(result, {"داير الناصيه": official})
    assert applied == 2
    assert {parcel.basin_code for parcel in result.parcels} == {official.code}


@pytest.mark.parametrize(
    "national_id",
    ["2951025120221", "295102512022111", "2951025120221a"],
)
def test_invalid_manual_national_id_fails_validation(national_id):
    assert not is_valid_national_id(national_id)


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
