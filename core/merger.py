"""Joins registered + approved DataFrames with reference codes into a MergeResult."""

import logging

import pandas as pd

from core.area import calculate_m2
from core.codes import CodesDB
from core.models import AssociationInfo, MergeResult, Parcel
from core.parser import normalize_holder_name

logger = logging.getLogger(__name__)


def _join_key(holding_number: str, holder_name: str) -> str:
    return f"{holding_number}||{normalize_holder_name(holder_name)}"


def _build_join_lookup(approved: pd.DataFrame) -> set[str]:
    """Set of join_keys present in the approved file (for existence check only)."""
    lookup: set[str] = set()
    for row in approved.itertuples():
        key = _join_key(row.holding_number, row.holder_name)
        lookup.add(key)
    return lookup


UNKNOWN_NATIONAL_ID = "11111111111111"


def is_valid_national_id(value: str) -> bool:
    """Return whether a national ID has the required fourteen digits."""
    return len(value) == 14 and value.isdigit()


def apply_manual_national_ids(result: MergeResult, updates: dict[int, str]) -> int:
    """Apply validated manual national IDs to parcels awaiting review."""
    applied = 0
    for index, national_id in updates.items():
        if not is_valid_national_id(national_id):
            raise ValueError("National ID must contain exactly 14 digits")
        parcel = result.parcels[index]
        if parcel.national_id == UNKNOWN_NATIONAL_ID:
            parcel.national_id = national_id
            applied += 1
    return applied


def _build_person_lookup(approved: pd.DataFrame) -> tuple[dict[tuple[str, str], dict], dict[tuple[str, tuple[str, ...]], list[dict]]]:
    """Return exact and first-four-name approved lookups."""
    lookup: dict[tuple[str, str], dict] = {}
    prefix_lookup: dict[tuple[str, tuple[str, ...]], list[dict]] = {}
    for row in approved.itertuples():
        normalized_name = normalize_holder_name(row.holder_name)
        key = (row.holding_number, normalized_name)
        words = tuple(normalized_name.split())
        prefix_key = (row.holding_number, words[:4]) if len(words) >= 4 else None
        fields = {
            "national_id": row.national_id,
            "unified_holding_id": row.unified_holding_id,
            "parcel_count": row.parcel_count,
            "approved_holder_name": row.holder_name,
        }
        if key in lookup:
            if lookup[key]["national_id"] != row.national_id:
                # The source contains conflicting records for the same person.
                # Do not stop the whole merge or choose one ID silently.
                logger.warning(
                    "Conflicting national IDs for the same holding and holder: %s / %s",
                    row.holding_number,
                    row.holder_name,
                )
                lookup[key]["national_id"] = UNKNOWN_NATIONAL_ID
            continue
        lookup[key] = fields
        if prefix_key is not None:
            prefix_lookup.setdefault(prefix_key, []).append(fields)
    return lookup, prefix_lookup


def merge(
    registered: pd.DataFrame,
    approved: pd.DataFrame,
    codes_db: CodesDB,
    association_info: AssociationInfo,
) -> MergeResult:
    """
    Join strategy: primary key = normalize(holding_number) + "||" + holder_name.
    Person-level fields are looked up by the same combined key.
    Area ALWAYS comes from the registered file (individual parcel area).
    If the combined key is missing, the national ID is set to the configured
    unknown marker instead of borrowing another person's data.
    """
    join_lookup = _build_join_lookup(approved)
    person_lookup, prefix_lookup = _build_person_lookup(approved)
    basins = codes_db.get_basins(association_info.code, association_info.type)

    warnings: list[str] = []
    unmatched_count = 0
    parcels: list[Parcel] = []

    for row in registered.itertuples():
        key = _join_key(row.holding_number, row.holder_name)
        matched = key in join_lookup
        if not matched:
            unmatched_count += 1
            warnings.append(
                f"لم يتم العثور على بيانات الحائز للحيازة {row.holding_number} "
                f"({row.holder_name})"
            )

        normalized_name = normalize_holder_name(row.holder_name)
        prefix_candidates = []
        person_fields = person_lookup.get((row.holding_number, normalized_name))
        if person_fields is None:
            words = tuple(normalized_name.split())
            prefix_candidates = prefix_lookup.get((row.holding_number, words[:4]), []) if len(words) >= 4 else []
            if len(prefix_candidates) == 1:
                person_fields = prefix_candidates[0]
            else:
                person_fields = {
                    "national_id": UNKNOWN_NATIONAL_ID,
                    "unified_holding_id": "",
                    "parcel_count": 0,
                    "approved_holder_name": "",
                }
        if not matched and len(prefix_candidates) == 1:
            matched = True
            unmatched_count -= 1
            warnings.pop()
        basin_code = codes_db.find_basin_code(
            row.basin_name, association_info.code, association_info.type
        )

        parcels.append(
            Parcel(
                directorate=association_info.directorate,
                administration=association_info.administration,
                association_name=association_info.name,
                association_type=association_info.type.value,
                association_code=association_info.code,
                basin_name=row.basin_name,
                basin_code=basin_code,
                holding_number=row.holding_number,
                unified_holding_id=person_fields["unified_holding_id"],
                registry_page=row.registry_page,
                national_id=person_fields["national_id"],
                holder_name=person_fields["approved_holder_name"] or row.holder_name,
                parcel_count_in_holding=person_fields["parcel_count"],
                land_number=row.land_number,
                area_feddan=row.feddan,
                area_qirat=row.qirat,
                area_sahm=row.sahm,
                area_m2=calculate_m2(row.feddan, row.qirat, row.sahm),
                border_north=row.border_north,
                border_west=row.border_west,
                border_south=row.border_south,
                border_east=row.border_east,
            )
        )

    if unmatched_count:
        logger.warning("%d parcels unmatched by join_key", unmatched_count)

    return MergeResult(
        parcels=parcels,
        association=association_info,
        basins=basins,
        unmatched_count=unmatched_count,
        warnings=warnings,
    )


