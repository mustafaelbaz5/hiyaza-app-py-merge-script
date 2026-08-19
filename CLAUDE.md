# CLAUDE.md — Agricultural Holdings Merger
## Complete Instructions for Claude Code

> **READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE.**
> Every rule here exists for a reason. Do not skip, summarize, or selectively apply.

---

## 1. PROJECT IDENTITY

**What this is:** A Python desktop application that merges two Excel files
(registered parcels + approved holdings) for Egyptian agricultural associations,
enriches them with reference codes, and exports a structured multi-sheet Excel report.

**Language of data:** Arabic (RTL). All Excel output must be right-to-left.
**Target OS:** Windows (primary). Must also run on macOS/Linux without code changes.
**Python version:** 3.11+

---

## 2. NON-NEGOTIABLE RULES

These are hard stops. Violating any of them means the implementation is wrong.

```
❌ NEVER delete a parcel row, even if it has no data
❌ NEVER invent data — empty fields stay empty
❌ NEVER modify the input files — they are read-only sources
❌ NEVER block the UI thread with heavy processing
❌ NEVER use print() for user-facing messages — use the logger
❌ NEVER hardcode file paths — always use pathlib.Path relative to project root
❌ NEVER use a bare except: — always catch specific exceptions
❌ NEVER write a function longer than 40 lines — extract helpers
❌ NEVER write a file longer than 200 lines — split into modules
❌ NEVER import from gui/ inside core/ — core must have zero GUI dependencies
```

---

## 3. PROJECT STRUCTURE

Exactly this. No additions, no renames.

```
holdings_merger/
│
├── CLAUDE.md               ← this file
├── PLAN.md                 ← business logic reference
├── main.py                 ← entry point only (~20 lines)
├── requirements.txt
├── pyproject.toml          ← project metadata + tool config
│
├── core/                   ← pure business logic, zero GUI imports
│   ├── __init__.py
│   ├── models.py           ← dataclasses for all domain objects
│   ├── detector.py         ← detect association name/type from approved file
│   ├── parser.py           ← parse & clean registered + approved files
│   ├── codes.py            ← load reference code files, lookup functions
│   ├── area.py             ← area calculation (m²)
│   ├── merger.py           ← join registered + approved + codes
│   └── exporter.py         ← write final Excel with formatting
│
├── gui/
│   ├── __init__.py
│   ├── app.py              ← main CTk window, wires everything together
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── home.py         ← file selection + auto-detect panel
│   │   └── result.py       ← progress + results panel
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── file_picker.py  ← reusable file input row
│   │   ├── info_badge.py   ← detected association info display
│   │   └── progress_bar.py ← custom progress with step label
│   └── theme.py            ← all colors, fonts, spacing constants
│
├── data/
│   ├── اكواد_ائتمان.xlsx   ← credit reference codes (ship with app)
│   └── اكواد_اصلاح.xlsx    ← reform reference codes (ship with app)
│
└── tests/
    ├── conftest.py
    ├── test_area.py
    ├── test_detector.py
    ├── test_parser.py
    ├── test_merger.py
    └── test_codes.py
```

---

## 4. SOLID PRINCIPLES — APPLIED

### Single Responsibility
Each module does exactly one thing:
- `detector.py` → only detects association metadata
- `parser.py` → only reads and cleans raw Excel data
- `codes.py` → only manages the reference code database
- `area.py` → only calculates area
- `merger.py` → only joins DataFrames
- `exporter.py` → only writes Excel output

### Open/Closed
Use the `AssociationType` enum + strategy pattern for credit vs reform differences.
Adding a new association type = add a new strategy class, not modify existing code.

### Liskov Substitution
`CodesDB` has a clear interface. Tests can inject a `FakeCodesDB` that returns
predictable values without reading real files.

### Interface Segregation
`core/` modules communicate through `models.py` dataclasses, not raw DataFrames
passed between every layer.

### Dependency Inversion
`merger.py` depends on the `CodesDB` *interface*, not its concrete implementation.
`app.py` depends on a `MergeRunner` protocol, not the implementation directly.

---

## 5. DOMAIN MODELS (core/models.py)

Define these first. Everything else depends on them.

```python
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class AssociationType(Enum):
    CREDIT = "credit"   # ائتمان زراعي
    REFORM = "reform"   # إصلاح زراعي


@dataclass(frozen=True)
class AssociationInfo:
    name: str            # "شنشا-الائتمان الزراعي"
    type: AssociationType
    code: str            # "323925"
    directorate: str     # "الدقهليه"
    administration: str  # "اجا"


@dataclass(frozen=True)
class BasinInfo:
    name: str   # "الباشا"
    code: str   # "6323000003239000005"


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
```

---

## 6. CORE MODULES — CONTRACTS

### core/area.py
```python
FEDDAN_M2 = 4200.833
QIRAT_M2  = FEDDAN_M2 / 24   # 175.0347
SAHM_M2   = QIRAT_M2  / 24   # 7.2931

def calculate_m2(feddan: float, qirat: float, sahm: float) -> float:
    """Returns area in m², rounded to 2 decimal places."""
    ...
```

### core/detector.py
```python
def detect_association(approved_path: Path) -> dict:
    """
    Reads the approved file header rows to extract:
    - association name  (row 13, col 3)
    - association type  (row 13, col 19 → "ائتمان" or "إصلاح")
    - administration    (row 11, col 3)
    - directorate       (row 11, col 19)

    Returns raw dict. Does NOT load codes or validate.
    Raises: FileNotFoundError, ValueError (if type cannot be determined)
    """
    ...
```

### core/codes.py
```python
class CodesDB:
    """
    Loads both code files once on init.
    All lookups are case-insensitive and handle common typos.

    Typo corrections applied automatically:
    - "داير الناصيه**" → "داير الناحيه"
    - any trailing * or whitespace in basin names
    """

    def __init__(self, credit_path: Path, reform_path: Path) -> None: ...

    def find_association(
        self,
        name: str,
        assoc_type: AssociationType,
    ) -> AssociationInfo | None:
        """
        Finds association by name in the correct code table.
        Uses partial match if exact fails.
        Returns None if not found (caller handles the warning).
        """
        ...

    def get_basins(
        self,
        assoc_code: str,
        assoc_type: AssociationType,
    ) -> list[BasinInfo]:
        """Returns all basins for an association, sorted by code."""
        ...

    def find_basin_code(
        self,
        basin_name: str,
        assoc_code: str,
        assoc_type: AssociationType,
    ) -> str:
        """
        Returns basin code or "غير محدد" if not found.
        Applies typo corrections before searching.
        """
        ...
```

### core/parser.py
```python
def parse_registered(path: Path) -> pd.DataFrame:
    """
    Reads the registered parcels file.
    - Data starts at row index 10
    - Removes residual header rows
    - Detects and removes summary rows (holding repeated across ≥13 basins)
    - Normalizes holding numbers: strips leading zeros
    - Fixes basin name typos
    - Returns clean DataFrame with standardized column names
    """
    ...

def parse_approved(path: Path) -> pd.DataFrame:
    """
    Reads the approved holdings file.
    - Data starts at row index 17
    - Removes residual header rows
    - Normalizes holding numbers
    - Returns clean DataFrame with standardized column names
    """
    ...

def normalize_holding(value) -> str:
    """
    '0048', '048', '48' → '48'
    Handles NaN, non-numeric gracefully.
    """
    try:
        return str(int(float(str(value).strip())))
    except (ValueError, TypeError):
        return str(value).strip()
```

### core/merger.py
```python
def merge(
    registered: pd.DataFrame,
    approved: pd.DataFrame,
    codes_db: CodesDB,
    association_info: AssociationInfo,
) -> MergeResult:
    """
    JOIN STRATEGY (critical — do not change without testing):
    Primary key: normalize(holding_number) + "||" + holder_name
    This achieves 100% match rate on test data.

    Fallback for unmatched: holding_number only (logs a warning).

    Area data comes from approved file (registered has mostly zeros).
    Holding-level fields (national_id, unified_id, parcel_count)
    use holding_number key only (first row per holding).

    Returns MergeResult with all parcels and metadata.
    """
    ...
```

---

## 7. EXCEL EXPORT SPEC (core/exporter.py)

### Output Sheets (in order)
1. `كل الحيازات` — all parcels, sorted basin→holding, with dark separator rows
2. One sheet per basin (named by basin name, max 31 chars)
3. `ملخص الأحواض` — summary table

### Column Order (22 columns)
```
[1]  المديرية          header: #1B5E20 (dark green)
[2]  الإدارة           header: #1B5E20
[3]  الجمعية           header: #1B5E20
[4]  نوع الجمعية       header: #1B5E20
[5]  كود الجمعية       header: #1B5E20
[6]  اسم الحوض         header: #004D40 (teal)
[7]  كود الحوض         header: #004D40
[8]  رقم الحيازة       header: #0D47A1 (dark blue)
[9]  الرقم الموحد       header: #0D47A1
[10] رقم الصفحة        header: #0D47A1
[11] الرقم القومي      header: #0D47A1
[12] اسم الحائز        header: #0D47A1
[13] عدد القطع         header: #0D47A1
[14] رقم الأرض         header: #4A148C (purple)
[15] فدان              header: #4A148C
[16] قيراط             header: #4A148C
[17] سهم               header: #4A148C
[18] مساحة القطعة - م² header: #4A148C  cell-fill: #FFF9C4 (yellow)
[19] حد بحري           header: #37474F (dark grey)
[20] حد غربي           header: #37474F
[21] حد قبلي           header: #37474F
[22] حد شرقي           header: #37474F
```

### Border Cell Hyperlinks
```python
def _resolve_border_hyperlink(
    border_text: str,
    name_index: dict[str, list[int]],  # name_fragment → list of df row indices
    basin_name: str,
    row_to_excel: dict[int, int],       # df_index → excel row number
) -> tuple[str | None, bool]:
    """
    Returns (target_excel_ref, is_multi_match).
    target_excel_ref: "#'كل الحيازات'!A{row}" or None
    is_multi_match: True if multiple candidates found (paint yellow)

    Algorithm:
    1. Strip leading "و" / "و." prefix
    2. Return (None, False) if empty/dots/dashes
    3. Exact match in name_index → prefer same-basin match
    4. Partial match (border_text in name OR name in border_text)
    5. Return first match ref; is_multi_match = len(candidates) > 1
    """
    ...
```

### Formatting Rules
- All sheets: `sheet_view.rightToLeft = True`
- All sheets: `freeze_panes = "A2"`
- All sheets: auto-filter on header row
- Header row height: 34
- Data row height: 15
- Font: Arial throughout
- Zero area values: show as empty (None), not "0"
- Numbers format: `#,##0.###` for feddans/qirats/sahms
- m² format: `#,##0.00 "م²"`
- Alternating row colors per basin (use BASIN_ROW_COLORS dict)
- Basin separator rows in `كل الحيازات`: fill `#263238`, white bold text

---

## 8. GUI DESIGN SYSTEM (gui/theme.py)

### Color Palette
```python
# Primary — agricultural green
PRIMARY_900 = "#1B5E20"
PRIMARY_700 = "#388E3C"
PRIMARY_500 = "#66BB6A"
PRIMARY_100 = "#E8F5E9"
PRIMARY_50  = "#F1F8E9"

# Neutral
NEUTRAL_900 = "#212121"
NEUTRAL_700 = "#616161"
NEUTRAL_300 = "#E0E0E0"
NEUTRAL_100 = "#F5F5F5"
NEUTRAL_50  = "#FAFAFA"
WHITE       = "#FFFFFF"

# Semantic
SUCCESS     = "#2E7D32"
WARNING     = "#F57F17"
ERROR       = "#C62828"
INFO        = "#1565C0"

# Accent
ACCENT_GOLD = "#F9A825"   # for m² cells and highlights
```

### Typography
```python
FONT_FAMILY = "Arial"   # available everywhere, supports Arabic

FONT_TITLE   = (FONT_FAMILY, 20, "bold")
FONT_HEADING = (FONT_FAMILY, 14, "bold")
FONT_BODY    = (FONT_FAMILY, 12)
FONT_SMALL   = (FONT_FAMILY, 10)
FONT_MONO    = ("Courier New", 11)   # for codes/IDs
```

### Spacing
```python
PAD_XL  = 32
PAD_L   = 24
PAD_M   = 16
PAD_S   = 8
PAD_XS  = 4

RADIUS_CARD   = 12
RADIUS_BUTTON = 8
RADIUS_BADGE  = 6
```

---

## 9. GUI LAYOUT (gui/app.py)

### Window
```
Title:  دمج بيانات الحيازات الزراعية
Size:   720 × 560 (fixed, not resizable)
Icon:   🌾 (set via CTk if possible)
Theme:  Light, green accent
RTL:    All labels right-aligned
```

### Layout — Two Pages (swap via CTk frame show/hide)

#### Page 1: Home (file selection)
```
┌──────────────────────────────────────────────────┐
│  🌾  دمج بيانات الحيازات الزراعية               │
│  ─────────────────────────────────────────────── │
│                                                  │
│  📄 ملف المسجل (الحيازات الزراعية المسجلة)      │
│  ┌────────────────────────────────┐ [اختر ملف]  │
│  │ اسم_الملف.xlsx                │             │
│  └────────────────────────────────┘             │
│                                                  │
│  📋 ملف المعتمد (حيازات الجمعية المعتمدة)       │
│  ┌────────────────────────────────┐ [اختر ملف]  │
│  │ اسم_الملف.xlsx                │             │
│  └────────────────────────────────┘             │
│                                                  │
│  ┌─ التعرف التلقائي ──────────────────────────┐ │
│  │  ✅ الجمعية:   شنشا-الائتمان الزراعي       │ │
│  │  ✅ النوع:     ائتمان زراعي                │ │
│  │  ✅ الإدارة:   اجا                         │ │
│  │  ✅ المديرية:  الدقهليه                    │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  💾 مكان حفظ الملف الناتج                       │
│  ┌────────────────────────────────┐ [اختر]      │
│  │ شنشا_مدمج.xlsx                │             │
│  └────────────────────────────────┘             │
│                                                  │
│              [  ابدأ الدمج  →  ]               │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### Page 2: Progress + Result
```
┌──────────────────────────────────────────────────┐
│  🌾  دمج بيانات الحيازات الزراعية               │
│  ─────────────────────────────────────────────── │
│                                                  │
│                 [spinning indicator]              │
│                                                  │
│   ████████████████████░░░░  80%                  │
│   جاري ربط البيانات بملف الأكواد...             │
│                                                  │
│  ┌─ سجل العمليات ─────────────────────────────┐ │
│  │  ✅ تم قراءة ملف المسجل — 1,364 صف         │ │
│  │  ✅ تم حذف صف الإجمالي (حيازة 935)         │ │
│  │  ✅ تم قراءة ملف المعتمد — 975 صف          │ │
│  │  ✅ تم التعرف: شنشا-الائتمان (كود 323925)  │ │
│  │  ✅ تم ربط 1,350 قطعة — 0 غير مرتبطة       │ │
│  │  ⏳ جاري كتابة Excel...                     │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│  ┌─ النتيجة ──────────────────────────────────┐ │
│  │  📊 إجمالي القطع:    1,350                 │ │
│  │  🏞️  عدد الأحواض:    13                   │ │
│  │  🔗 نسبة الربط:      100%                  │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
│    [← دمج جديد]         [فتح الملف ↗]          │
│                                                  │
└──────────────────────────────────────────────────┘
```

### UX Rules
- Auto-detect fires immediately when approved file is selected (no button click needed)
- If detection fails → show error badge, allow manual type selection (dropdown)
- Output filename auto-suggested: `{association_name_short}_مدمج.xlsx` in same folder as input
- "ابدأ الدمج" button disabled until both files + output path are set
- Processing runs in `threading.Thread` — never `time.sleep()` on main thread
- Progress updates via `after()` callback queue (thread-safe)
- Log scroll to bottom automatically as entries add
- On success: "فتح الملف" opens file with `os.startfile()` (Windows) / `subprocess.open` (mac/linux)
- On error: show red error card with message + "حاول مرة أخرى" button

---

## 10. DATA PIPELINE — STEP BY STEP

This is exactly what `merger.py` must implement, in this order:

```
Step 1: Parse registered file
        → remove summary rows (holding repeated across ≥13 basins)
        → normalize holding numbers
        → fix basin name typos

Step 2: Parse approved file
        → normalize holding numbers
        → build join_key = normalize(holding) + "||" + holder_name

Step 3: Detect association from approved file header

Step 4: Look up association in codes DB
        → get association code
        → get all basin codes

Step 5: Build area lookup (join_key → {feddan, qirat, sahm})
        → for duplicate join_keys: prefer row with non-zero area

Step 6: Build holding lookup (holding_number → {national_id, unified_id, parcel_count})
        → one row per holding (first occurrence)

Step 7: For each parcel in registered:
        a. Look up area by join_key
        b. Look up holding fields by normalized holding number
        c. Look up basin code from codes DB
        d. Calculate m² from area
        e. Build Parcel dataclass

Step 8: Sort parcels by (basin_order_index, holding_number_int)

Step 9: Export to Excel
        a. Write "كل الحيازات" with separator rows between basins
        b. Write per-basin sheets
        c. Write "ملخص الأحواض"
        d. Apply border hyperlinks (second pass after all rows written)
```

---

## 11. ERROR HANDLING STRATEGY

```python
# Use custom exceptions in core/
class MergerError(Exception): ...
class ParseError(MergerError): ...
class DetectionError(MergerError): ...
class CodeNotFoundError(MergerError): ...

# In GUI: catch MergerError → show user-friendly Arabic message
# In core: let exceptions propagate, log details

# Always log:
import logging
logger = logging.getLogger(__name__)

# Example pattern:
try:
    df = parse_registered(path)
except (FileNotFoundError, PermissionError) as e:
    raise ParseError(f"لا يمكن فتح ملف المسجل: {path.name}") from e
except Exception as e:
    logger.exception("Unexpected error parsing registered file")
    raise ParseError("حدث خطأ غير متوقع أثناء قراءة الملف") from e
```

---

## 12. TESTING RULES

Every `core/` module must have tests. GUI has no tests.

### Test File Rules
- Each test file maps 1:1 to a core module
- Use `pytest` only — no unittest
- No real Excel files in tests — use fixtures with minimal synthetic data
- Test the edge cases, not just the happy path

### Required Test Cases

**test_area.py**
- `calculate_m2(1, 0, 0)` → `4200.833`
- `calculate_m2(0, 24, 0)` → `4200.833` (24 qirats = 1 feddan)
- `calculate_m2(0, 0, 576)` → `4200.833` (576 sahms = 1 feddan)
- `calculate_m2(0, 0, 0)` → `0.0`
- Float precision: result rounded to 2 decimal places

**test_parser.py**
- Summary row detection (holding repeated across 13 basins → removed)
- normalize_holding: `"0048"` → `"48"`, `"048"` → `"48"`, `nan` → `"nan"`
- Empty rows removed
- Typo correction: `"داير الناصيه**"` → `"داير الناحيه"`

**test_merger.py**
- Join by holding + name achieves 100% on synthetic data
- Unmatched parcels: area stays 0, holding fields stay empty, no crash
- Parcel count in output = parcel count in registered (nothing dropped)

**test_codes.py**
- Partial match: `"شنشا"` finds `"شنشا-الائتمان الزراعي"`
- Typo correction in basin lookup
- Missing association → returns None (no exception)

---

## 13. IMPLEMENTATION ORDER

Do not skip phases. Each phase must pass its tests before moving to the next.

```
Phase 1  → core/models.py          (dataclasses, enums — no logic)
Phase 2  → core/area.py            (pure math — simplest module)
Phase 3  → tests/test_area.py      (verify Phase 2)
Phase 4  → core/codes.py           (load reference files)
Phase 5  → tests/test_codes.py     (verify Phase 4)
Phase 6  → core/detector.py        (read approved file header)
Phase 7  → tests/test_detector.py  (verify Phase 6)
Phase 8  → core/parser.py          (read + clean both input files)
Phase 9  → tests/test_parser.py    (verify Phase 8)
Phase 10 → core/merger.py          (join everything together)
Phase 11 → tests/test_merger.py    (verify Phase 10)
Phase 12 → core/exporter.py        (write Excel — longest module)
Phase 13 → gui/theme.py            (constants only — no logic)
Phase 14 → gui/widgets/            (reusable components)
Phase 15 → gui/pages/              (page layouts)
Phase 16 → gui/app.py              (wire everything together)
Phase 17 → main.py                 (entry point)
Phase 18 → Integration test        (run on real شنشا files, verify output)
```

---

## 14. KNOWN DATA QUIRKS — HANDLE THESE

| Quirk | Location | Fix |
|---|---|---|
| Summary row: holding 935 appears once per basin | Registered file | Detect: holding in ≥13 basins → remove |
| `"داير الناصيه**"` typo | Code files + Registered | Normalize before any comparison |
| Registered area columns almost always = 0 | Registered col 0,2,3 | Use approved file for area instead |
| Holding `"0048"`, `"048"`, `"48"` are the same | Both files | Always normalize before join |
| Approved has one row per parcel (not per holding) | Approved file | Join by holding+name, not holding only |
| Duplicate join_keys in approved | Approved file | Take row with non-zero area first |
| Border cells: `"."` `".."` `"___"` `"---"` = empty | Registered | Treat as empty — no hyperlink |
| Border cells: prefix `"و"` / `"و."` | Registered | Strip prefix before name matching |
| رقم الأرض (col 4) = 8-digit land number, NOT national ID | Registered | National ID comes from approved only |
| Unified holding ID structure: `06-3230-00323925-001283` | Approved col 11 | Store as-is, no parsing needed |

---

## 15. REQUIREMENTS.TXT

```
pandas>=2.2
openpyxl>=3.1
customtkinter>=5.2
Pillow>=10.0
pytest>=8.0
pytest-cov>=5.0
```

---

## 16. PYPROJECT.TOML

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts   = "-v --tb=short"

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]
ignore = ["E501"]
```

---

## 17. REFERENCE DATA

### Column indices in raw Excel files (0-based)

**Registered file — data starts row 10:**
| Col | Field |
|---|---|
| 0 | فدان (usually 0) |
| 2 | قيراط (usually 0) |
| 3 | سهم (usually 0) |
| 4 | رقم الأرض (8-digit land number) |
| 6 | حد بحري |
| 7 | حد غربي |
| 8 | حد قبلي |
| 9 | حد شرقي |
| 11 | رقم الصفحة بالسجل |
| 13 | رقم الحيازة |
| 14 | اسم الحائز |
| 18 | اسم الحوض |
| 19 | الجمعية |
| 20 | الإدارة |
| 21 | المديرية |

**Approved file — data starts row 17:**
| Col | Field |
|---|---|
| 2 | عدد القطع بالحيازة |
| 4 | فدان (actual parcel area) |
| 8 | قيراط |
| 9 | سهم |
| 11 | الرقم الموحد للحيازة |
| 17 | رقم الحيازة |
| 21 | الرقم القومي (14 digits) |
| 23 | اسم الحائز |

**Approved file — metadata rows:**
| Row | Col 3 | Col 19 |
|---|---|---|
| 11 | الإدارة | المديرية |
| 13 | اسم الجمعية الكامل | القطاع (ائتمان/إصلاح) |

**Code files — direct headers (row 0):**
| Column name | Field |
|---|---|
| `الجمعية` | Association name |
| `كود \nالجمعية` | Association code |
| `الحوض` | Basin name |
| `كود \nالحوض` | Basin code |
| `الادارة` | Administration |
| `المديرية` | Directorate |

### Test Data Expectations (شنشا)
- Registered: 1,364 raw rows → 1,350 clean (14 summary rows removed)
- Approved: 975 rows
- Association code: `323925`
- Basins: 13 (one basin "داير الناصيه**" is typo of "داير الناحيه")
- Match rate: 100% (0 unmatched)
- Largest basin: العمده (204 parcels)
- Smallest basin: عبيد اول (20 parcels)

---

## 18. FINAL CHECKLIST BEFORE COMMIT

Run this before considering any phase done:

```bash
# All tests pass
pytest tests/ -v

# No import errors
python -c "from core.merger import merge; print('OK')"

# GUI launches without crash
python main.py

# On real test files: output has correct parcel count
# grep or verify 1350 data rows in شنشا_مدمج.xlsx
```

---

*This file is the single source of truth for this project.*
*If PLAN.md and CLAUDE.md conflict → CLAUDE.md wins.*
*Last updated: August 2026*
