"""Resolves border-cell text to hyperlink targets within the merged output."""

import re

_EMPTY_BORDER_PATTERN = re.compile(r"^[\.\-_\s]*$")
_PREFIX_PATTERN = re.compile(r"^و\.?\s*")


def _strip_prefix(text: str) -> str:
    return _PREFIX_PATTERN.sub("", text).strip()


def is_empty_border(border_text: str) -> bool:
    return bool(_EMPTY_BORDER_PATTERN.match(border_text.strip()))


def resolve_border_hyperlink(
    border_text: str,
    name_index: dict[str, list[tuple[int, str]]],
    basin_name: str,
    row_to_excel: dict[int, int],
) -> tuple[str | None, bool]:
    """
    name_index: name_fragment -> list of (df_row_index, basin_name) candidates.
    Returns (target_excel_ref, is_multi_match).
    target_excel_ref: "#'كل الحيازات'!A{row}" or None.
    is_multi_match: True if multiple candidates found (paint yellow).

    Algorithm:
    1. Strip leading "و" / "و." prefix
    2. Return (None, False) if empty/dots/dashes
    3. Exact match in name_index -> prefer same-basin match
    4. Partial match (border_text in name OR name in border_text)
    5. Return first match ref; is_multi_match = len(candidates) > 1
    """
    if border_text is None or is_empty_border(border_text):
        return None, False

    target = _strip_prefix(border_text)
    if not target:
        return None, False

    candidates = _find_candidates(target, name_index)
    if not candidates:
        return None, False

    row_index = _prefer_same_basin(candidates, basin_name)
    excel_row = row_to_excel.get(row_index)
    if excel_row is None:
        return None, False

    ref = f"#'كل الحيازات'!A{excel_row}"
    return ref, len(candidates) > 1


def _find_candidates(
    target: str, name_index: dict[str, list[tuple[int, str]]]
) -> list[tuple[int, str]]:
    exact = name_index.get(target)
    if exact:
        return exact

    candidates: list[tuple[int, str]] = []
    for name, entries in name_index.items():
        if target in name or name in target:
            candidates.extend(entries)
    return candidates


def _prefer_same_basin(candidates: list[tuple[int, str]], basin_name: str) -> int:
    for row_index, candidate_basin in candidates:
        if candidate_basin == basin_name:
            return row_index
    return candidates[0][0]
