"""Domain dataclasses shared across all core/ modules."""

from dataclasses import dataclass, field
from enum import Enum


class AssociationType(Enum):
    CREDIT = "credit"  # ائتمان زراعي
    REFORM = "reform"  # إصلاح زراعي


@dataclass(frozen=True)
class AssociationInfo:
    name: str  # "شنشا-الائتمان الزراعي"
    type: AssociationType
    code: str  # "323925"
    directorate: str  # "الدقهليه"
    administration: str  # "اجا"


@dataclass(frozen=True)
class BasinInfo:
    name: str  # "الباشا"
    code: str  # "6323000003239000005"


@dataclass
class Parcel:
    """One row in the final merged output."""

    # Identity
    directorate: str
    administration: str
    association_name: str
    association_type: str
    association_code: str
    basin_name: str
    basin_code: str
    # Holding
    holding_number: str
    unified_holding_id: str
    registry_page: str
    national_id: str
    holder_name: str
    parcel_count_in_holding: int
    # Land
    land_number: str
    area_feddan: float
    area_qirat: float
    area_sahm: float
    area_m2: float
    # Borders
    border_north: str
    border_west: str
    border_south: str
    border_east: str


@dataclass
class MergeResult:
    parcels: list[Parcel]
    association: AssociationInfo
    basins: list[BasinInfo]
    unmatched_count: int
    warnings: list[str] = field(default_factory=list)
