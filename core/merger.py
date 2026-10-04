"""Joins registered + approved data with safe person-level review support."""

import logging
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from core.area import calculate_m2
from core.codes import CodesDB
from core.models import AssociationInfo, BasinInfo, MergeResult, Parcel
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
PersonKey = tuple[str, str]


@dataclass(frozen=True)
class ManualReviewPerson:
    """One unresolved person and all registered parcels that belong to them."""

    key: PersonKey
    holding_number: str
    holder_name: str
    parcel_indexes: tuple[int, ...]
    land_numbers: tuple[str, ...]
    basin_names: tuple[str, ...]
    reason: str
    suggested_national_id: str = ""
    suggested_holder_name: str = ""


@dataclass(frozen=True)
class ManualReviewBasin:
    raw_name: str
    parcel_indexes: tuple[int, ...]
    reason: str


def is_valid_national_id(value: str) -> bool:
    """Return whether a national ID has the required fourteen digits."""
    return len(value) == 14 and value.isdigit()


def _parcel_person_key(parcel: Parcel) -> PersonKey:
    """Return the registered-person key retained for manual review."""
    return parcel.review_person_key or (
        parcel.holding_number,
        normalize_holder_name(parcel.source_holder_name or parcel.holder_name),
    )


def build_manual_review_people(parcels: list[Parcel]) -> list[ManualReviewPerson]:
    """Group unresolved parcels so a person is reviewed once, not per parcel."""
    grouped: dict[PersonKey, list[tuple[int, Parcel]]] = defaultdict(list)
    for index, parcel in enumerate(parcels):
        if parcel.national_id == UNKNOWN_NATIONAL_ID:
            grouped[_parcel_person_key(parcel)].append((index, parcel))

    people: list[ManualReviewPerson] = []
    for key, entries in grouped.items():
        first = entries[0][1]
        people.append(
            ManualReviewPerson(
                key=key,
                holding_number=first.holding_number,
                holder_name=first.source_holder_name or first.holder_name,
                parcel_indexes=tuple(index for index, _ in entries),
                land_numbers=tuple(parcel.land_number for _, parcel in entries),
                basin_names=tuple(dict.fromkeys(parcel.basin_name for _, parcel in entries)),
                reason=first.review_reason or "لا يوجد رقم قومي مطابق في ملف المعتمد.",
                suggested_national_id=first.suggested_national_id,
                suggested_holder_name=first.suggested_holder_name,
            )
        )
    return people


def build_manual_review_basins(parcels: list[Parcel]) -> list[ManualReviewBasin]:
    """Group every unresolved raw basin name into one manual-review item."""
    grouped: dict[str, list[tuple[int, Parcel]]] = defaultdict(list)
    for index, parcel in enumerate(parcels):
        if parcel.basin_code == "غير محدد":
            grouped[parcel.raw_basin_name or parcel.basin_name].append((index, parcel))
    return [
        ManualReviewBasin(
            raw_name=raw_name,
            parcel_indexes=tuple(index for index, _ in entries),
            reason=entries[0][1].basin_review_reason or "الحوض يحتاج اختيارًا يدويًا.",
        )
        for raw_name, entries in grouped.items()
    ]


def apply_manual_basin_codes(
    result: MergeResult, updates: Mapping[str, BasinInfo]
) -> int:
    """Apply an approved official basin/code pair to all matching raw names."""
    applied = 0
    for parcel in result.parcels:
        raw_name = parcel.raw_basin_name or parcel.basin_name
        basin = updates.get(raw_name)
        if basin and parcel.basin_code == "غير محدد":
            parcel.basin_name = basin.name
            parcel.basin_code = basin.code
            parcel.basin_review_reason = ""
            applied += 1
    return applied


def apply_manual_national_ids(
    result: MergeResult, updates: Mapping[PersonKey, str]
) -> int:
    """Apply each validated ID to every unresolved parcel for that person."""
    for person_key, national_id in updates.items():
        if not is_valid_national_id(national_id):
            raise ValueError("National ID must contain exactly 14 digits")

    pending_by_person: dict[PersonKey, list[Parcel]] = defaultdict(list)
    for parcel in result.parcels:
        if parcel.national_id == UNKNOWN_NATIONAL_ID:
            pending_by_person[_parcel_person_key(parcel)].append(parcel)

    applied = 0
    for person_key, national_id in updates.items():
        for parcel in pending_by_person.get(person_key, []):
            parcel.national_id = national_id
            applied += 1
    return applied


def _build_person_lookup(approved: pd.DataFrame) -> tuple[dict[PersonKey, dict], dict[tuple[str, tuple[str, ...]], list[dict]]]:
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
        review_reason = ""
        suggested_national_id = ""
        suggested_holder_name = ""
        if person_fields is None:
            words = tuple(normalized_name.split())
            prefix_candidates = prefix_lookup.get((row.holding_number, words[:4]), []) if len(words) >= 4 else []
            if len(prefix_candidates) == 1:
                # Similar names are helpful evidence but not proof of identity.
                # Keep the candidate for the reviewer; never assign it silently.
                candidate = prefix_candidates[0]
                person_fields = {
                    "national_id": UNKNOWN_NATIONAL_ID,
                    "unified_holding_id": "",
                    "parcel_count": 0,
                    "approved_holder_name": "",
                }
                review_reason = "تطابق أول أربعة أسماء فقط؛ يلزم تأكيد الرقم القومي."
                suggested_national_id = candidate["national_id"]
                suggested_holder_name = candidate["approved_holder_name"]
            else:
                person_fields = {
                    "national_id": UNKNOWN_NATIONAL_ID,
                    "unified_holding_id": "",
                    "parcel_count": 0,
                    "approved_holder_name": "",
                }
                review_reason = (
                    "يوجد أكثر من مرشح متشابه للاسم؛ يلزم إدخال الرقم القومي يدويًا."
                    if prefix_candidates
                    else "لا يوجد رقم قومي مطابق في ملف المعتمد."
                )
        elif person_fields["national_id"] == UNKNOWN_NATIONAL_ID:
            review_reason = "تعارض في الأرقام القومية لنفس الحيازة والاسم في ملف المعتمد."
        basin, basin_review_reason = codes_db.resolve_basin(
            row.basin_name, association_info.code, association_info.type
        )

        parcels.append(
            Parcel(
                directorate=association_info.directorate,
                administration=association_info.administration,
                association_name=association_info.name,
                association_type=association_info.type.value,
                association_code=association_info.code,
                basin_name=basin.name if basin else row.basin_name,
                basin_code=basin.code if basin else "غير محدد",
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
                review_person_key=(row.holding_number, normalized_name),
                source_holder_name=row.holder_name,
                review_reason=review_reason,
                suggested_national_id=suggested_national_id,
                suggested_holder_name=suggested_holder_name,
                raw_basin_name=row.basin_name,
                basin_review_reason=basin_review_reason,
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


