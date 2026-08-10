from __future__ import annotations

import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from .models import InventoryPresetFile, MergePlan
from .planner import merge_plan_to_report, merge_plan_to_xml


DEFAULT_GENERATED_MOD_NAME = "InventoryPresetMerge"
DEFAULT_GENERATED_MOD_ID = "inventorypresetmerge"


class GenerationBlocked(Exception):
    pass


def generate_compatibility_mod(
    plan: MergePlan,
    *,
    output_path: Path,
    generated_mod_name: str = DEFAULT_GENERATED_MOD_NAME,
    generated_mod_id: str = DEFAULT_GENERATED_MOD_ID,
    source_mod_paths: tuple[Path, ...] = (),
) -> Path | None:
    if plan.parse_issues:
        raise GenerationBlocked("parse errors exist; refusing to generate compatibility mod")
    if plan.unresolved_presets:
        raise GenerationBlocked("unresolved InventoryPreset interactions exist; refusing to generate compatibility mod")
    if not plan.safe_presets:
        return None

    mod_root = output_path / generated_mod_name
    _ensure_not_inside_source_mod(mod_root.resolve(), source_mod_paths)
    if mod_root.exists():
        shutil.rmtree(mod_root)

    xml_path = mod_root / "Data" / generated_mod_id / "Libs" / "Tables" / "item" / "InventoryPreset__merged.xml"
    report_path = mod_root / "merge-report.json"
    manifest_path = mod_root / "mod.manifest"

    xml_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(_manifest_xml(generated_mod_id, generated_mod_name), encoding="utf-8")
    xml_path.write_text(merge_plan_to_xml(plan), encoding="utf-8")
    report_path.write_text(
        json.dumps(_generation_report(plan, generated_mod_name, generated_mod_id), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    validate_generated_mod(mod_root, generated_mod_id=generated_mod_id)
    return mod_root


def _generation_report(plan: MergePlan, generated_mod_name: str, generated_mod_id: str) -> dict:
    report = merge_plan_to_report(plan)
    report["generated_mod_name"] = generated_mod_name
    report["generated_mod_id"] = generated_mod_id
    report["generated_layout"] = {
        "manifest": "mod.manifest",
        "report": "merge-report.json",
        "xml": f"Data/{generated_mod_id}/Libs/Tables/item/InventoryPreset__merged.xml",
    }
    return report


def validate_generated_mod(mod_root: Path, *, generated_mod_id: str = DEFAULT_GENERATED_MOD_ID) -> None:
    expected_relative_files = {
        Path("mod.manifest"),
        Path("merge-report.json"),
        Path("Data") / generated_mod_id / "Libs" / "Tables" / "item" / "InventoryPreset__merged.xml",
    }
    actual_relative_files = {
        path.relative_to(mod_root)
        for path in mod_root.rglob("*")
        if path.is_file()
    }
    if actual_relative_files != expected_relative_files:
        raise GenerationBlocked(
            "generated mod directory is not self-contained or contains unexpected files: "
            + ", ".join(str(path).replace("\\", "/") for path in sorted(actual_relative_files))
        )

    manifest_path = mod_root / "mod.manifest"
    report_path = mod_root / "merge-report.json"
    xml_path = mod_root / "Data" / generated_mod_id / "Libs" / "Tables" / "item" / "InventoryPreset__merged.xml"

    manifest_root = ET.parse(manifest_path).getroot()
    mod_id = manifest_root.findtext("./info/modid")
    if mod_id != generated_mod_id:
        raise GenerationBlocked(
            f"generated mod id mismatch: manifest modid {mod_id!r} does not match Data namespace {generated_mod_id!r}"
        )

    ET.parse(xml_path)
    with report_path.open("r", encoding="utf-8") as handle:
        json.load(handle)


def _ensure_not_inside_source_mod(output_mod_root: Path, source_mod_paths: tuple[Path, ...]) -> None:
    for source_mod_path in source_mod_paths:
        source_mod_path = source_mod_path.resolve()
        if output_mod_root == source_mod_path or _is_relative_to(output_mod_root, source_mod_path):
            raise GenerationBlocked(f"refusing to write inside source mod directory: {source_mod_path}")


def _manifest_xml(generated_mod_id: str, generated_mod_name: str) -> str:
    mod_id = escape(generated_mod_id)
    mod_name = escape(generated_mod_name)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<kcd_mod>
  <info>
    <modid>{mod_id}</modid>
    <name>{mod_name}</name>
    <description>Generated InventoryPreset compatibility mod.</description>
    <author>kcd2-inventory-preset-merger</author>
    <version>0.1</version>
    <created_on>2026-08-10</created_on>
  </info>
  <supports>
    <kcd_version>1.*</kcd_version>
  </supports>
</kcd_mod>
"""


def source_mod_roots(mods_path: Path, files: tuple[InventoryPresetFile, ...]) -> tuple[Path, ...]:
    roots = {
        mods_path / file.relative_path.parts[0]
        for file in files
        if getattr(file, "relative_path", None) is not None and file.relative_path.parts
    }
    return tuple(sorted(roots, key=lambda path: str(path).casefold()))


def _is_relative_to(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
    except ValueError:
        return False
    return True
