"""Runs the merge pipeline on a background thread, reporting progress via callback."""

import threading
from collections.abc import Callable
from pathlib import Path

from core.codes import CodesDB
from core.exceptions import MergerError
from core.exporter import export
from core.merger import PersonKey, apply_manual_basin_codes, apply_manual_national_ids, merge
from core.models import BasinInfo
from core.models import AssociationType, MergeResult
from core.parser import parse_approved, parse_registered

ProgressCallback = Callable[[float, str], None]


class MergeRunner:
    def __init__(self, codes_db: CodesDB) -> None:
        self._codes_db = codes_db

    def run_async(
        self,
        registered_path: Path,
        approved_path: Path,
        output_path: Path,
        detected_info: dict,
        on_progress: ProgressCallback,
        on_done: Callable[[dict | None, Exception | None], None],
    ) -> None:
        thread = threading.Thread(
            target=self._run,
            args=(registered_path, approved_path, output_path, detected_info, on_progress, on_done),
            daemon=True,
        )
        thread.start()

    def save_manual_ids_async(
        self,
        result: MergeResult,
        output_path: Path,
        updates: dict[PersonKey, str],
        basin_updates: dict[str, BasinInfo],
        on_done: Callable[[dict | None, Exception | None], None],
    ) -> None:
        thread = threading.Thread(
            target=self._save_manual_ids,
            args=(result, output_path, updates, basin_updates, on_done),
            daemon=True,
        )
        thread.start()

    def _run(
        self,
        registered_path: Path,
        approved_path: Path,
        output_path: Path,
        detected_info: dict,
        on_progress: ProgressCallback,
        on_done: Callable[[dict | None, Exception | None], None],
    ) -> None:
        try:
            on_progress(0.1, "جاري قراءة ملف المسجل...")
            registered = parse_registered(registered_path)

            on_progress(0.3, "جاري قراءة ملف المعتمد...")
            approved = parse_approved(approved_path)

            on_progress(0.5, "جاري البحث عن كود الجمعية...")
            assoc_type = (
                AssociationType.CREDIT
                if detected_info["association_type"] == "credit"
                else AssociationType.REFORM
            )
            association_info = self._codes_db.find_association(
                detected_info["association_name"], assoc_type
            )
            if association_info is None:
                raise MergerError("تعذر العثور على كود الجمعية في ملفات الأكواد")

            on_progress(0.65, "جاري ربط البيانات...")
            result = merge(registered, approved, self._codes_db, association_info)

            on_progress(0.85, "جاري كتابة ملف Excel...")
            export(result, output_path)

            on_progress(1.0, "تم الانتهاء بنجاح")
            summary = {
                "output_path": output_path,
                "result": result,
                "parcel_count": len(result.parcels),
                "basin_count": len(result.basins),
                "unmatched_count": result.unmatched_count,
                "warnings": result.warnings,
            }
            on_done(summary, None)
        except MergerError as e:
            on_done(None, e)
        except Exception as e:  # noqa: BLE001
            on_done(None, MergerError(f"حدث خطأ غير متوقع: {e}"))

    def _save_manual_ids(
        self,
        result: MergeResult,
        output_path: Path,
        updates: dict[PersonKey, str],
        basin_updates: dict[str, BasinInfo],
        on_done: Callable[[dict | None, Exception | None], None],
    ) -> None:
        try:
            applied = apply_manual_national_ids(result, updates)
            basins_applied = apply_manual_basin_codes(result, basin_updates)
            export(result, output_path)
            remaining = sum(
                parcel.national_id == "11111111111111" for parcel in result.parcels
            )
            on_done({"applied": applied, "people_saved": len(updates), "basins_applied": basins_applied, "remaining": remaining}, None)
        except (MergerError, OSError, ValueError) as error:
            on_done(None, MergerError(f"تعذر حفظ التصحيحات اليدوية: {error}"))
