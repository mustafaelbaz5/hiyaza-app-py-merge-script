"""Joins registered + approved DataFrames with reference codes into a MergeResult."""

import logging

import pandas as pd

from core.area import calculate_m2
from core.codes import CodesDB
from core.models import AssociationInfo, MergeResult, Parcel

logger = logging.getLogger(__name__)


def _join_key(holding_number: str, holder_name: str) -> str:
    return f"{holding_number}||{holder_name}"


def _build_join_lookup(approved: pd.DataFrame) -> set[str]:
    """Set of join_keys present in the approved file (for existence check only)."""
    lookup: set[str] = set()
    for row in approved.itertuples():
        key = _join_key(row.holding_number, row.holder_name)
        lookup.add(key)
    return lookup


def _build_holding_lookup(approved: pd.DataFrame) -> dict[str, dict]:
    """normalized_holding -> {national_id, unified_holding_id, parcel_count}
    (first occurrence per holding)."""
    lookup: dict[str, dict] = {}
    for row in approved.itertuples():
        if row.holding_number in lookup:
            continue
        lookup[row.holding_number] = {
            "national_id": row.national_id,
            "unified_holding_id": row.unified_holding_id,
            "parcel_count": row.parcel_count,
        }
    return lookup


def merge(
    registered: pd.DataFrame,
    approved: pd.DataFrame,
    codes_db: CodesDB,
    association_info: AssociationInfo,
) -> MergeResult:
    """
    Join strategy: primary key = normalize(holding_number) + "||" + holder_name.
    Falls back to holding_number only when the combined key has no match.
    Area ALWAYS comes from the registered file (individual parcel area).
    Holding-level fields (national id, unified id, parcel count) come from
    the first approved row per holding.
    """
    join_lookup = _build_join_lookup(approved)
    holding_lookup = _build_holding_lookup(approved)
    basins = codes_db.get_basins(association_info.code, association_info.type)

    warnings: list[str] = []
    unmatched_count = 0
    parcels: list[Parcel] = []

    for row in registered.itertuples():
        key = _join_key(row.holding_number, row.holder_name)
        matched = key in join_lookup
        if not matched:
            unmatched_count += 1
            fallback_matched = _fallback_exists(join_lookup, row.holding_number)
            if not fallback_matched:
                warnings.append(
                    f"لم يتم العثور على بيانات الحائز للحيازة {row.holding_number} "
                    f"({row.holder_name})"
                )

        holding_fields = holding_lookup.get(
            row.holding_number,
            {"national_id": "", "unified_holding_id": "", "parcel_count": 0},
        )
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
                unified_holding_id=holding_fields["unified_holding_id"],
                registry_page=row.registry_page,
                national_id=holding_fields["national_id"],
                holder_name=row.holder_name,
                parcel_count_in_holding=holding_fields["parcel_count"],
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


def _fallback_exists(join_lookup: set[str], holding_number: str) -> bool:
    """Check if any join_key for this holding_number exists in approved file."""
    suffix = f"{holding_number}||"
    return any(key.startswith(suffix) for key in join_lookup)
