"""Joins registered + approved DataFrames with reference codes into a MergeResult."""

import logging

import pandas as pd

from core.area import calculate_m2
from core.codes import CodesDB
from core.models import AssociationInfo, MergeResult, Parcel

logger = logging.getLogger(__name__)


def _join_key(holding_number: str, holder_name: str) -> str:
    return f"{holding_number}||{holder_name}"


def _build_join_lookup(approved: pd.DataFrame) -> dict[str, dict]:
    """join_key -> {feddan, qirat, sahm}. For duplicate keys, prefer the row
    with non-zero area."""
    lookup: dict[str, dict] = {}
    for row in approved.itertuples():
        key = _join_key(row.holding_number, row.holder_name)
        area = {"feddan": row.feddan, "qirat": row.qirat, "sahm": row.sahm}
        existing = lookup.get(key)
        if existing is None or _is_zero_area(existing):
            lookup[key] = area
    return lookup


def _is_zero_area(area: dict) -> bool:
    return area["feddan"] == 0 and area["qirat"] == 0 and area["sahm"] == 0


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
    Area comes from the approved file; holding-level fields (national id,
    unified id, parcel count) come from the first approved row per holding.
    """
    join_lookup = _build_join_lookup(approved)
    holding_lookup = _build_holding_lookup(approved)
    basins = codes_db.get_basins(association_info.code, association_info.type)

    warnings: list[str] = []
    unmatched_count = 0
    parcels: list[Parcel] = []

    for row in registered.itertuples():
        key = _join_key(row.holding_number, row.holder_name)
        area = join_lookup.get(key)
        if area is None:
            unmatched_count += 1
            area = _fallback_area(join_lookup, row.holding_number)
            if area is None:
                warnings.append(
                    f"لم يتم العثور على مساحة للحيازة {row.holding_number} "
                    f"({row.holder_name})"
                )
                area = {"feddan": 0.0, "qirat": 0.0, "sahm": 0.0}

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
                area_feddan=area["feddan"],
                area_qirat=area["qirat"],
                area_sahm=area["sahm"],
                area_m2=calculate_m2(area["feddan"], area["qirat"], area["sahm"]),
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


def _fallback_area(join_lookup: dict[str, dict], holding_number: str) -> dict | None:
    """Fallback: match by holding_number only when the combined key fails."""
    suffix = f"{holding_number}||"
    for key, area in join_lookup.items():
        if key.startswith(suffix):
            return area
    return None
