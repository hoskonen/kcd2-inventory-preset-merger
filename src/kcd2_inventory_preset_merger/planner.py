from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .conflicts import analyze_presets, build_preset_index
from .models import (
    MergePlan,
    ParseIssue,
    PlannedChild,
    PlannedPreset,
    PresetAnalysis,
    PresetAttributeFinding,
    PresetRecord,
    ScanResult,
)


RUNTIME_SEMANTICS_NOTE = (
    "Runtime test confirmed distinct cross-mod PresetItem additions can coexist: "
    "inventorytest_a added bandage_classic x100, inventorytest_b added "
    "recipe_fevertonicPotion x100, and both appeared simultaneously in the same merchant inventory."
)


def build_merge_plan(scan_result: ScanResult) -> MergePlan:
    index = build_preset_index(scan_result.presets)
    analyses = analyze_presets(index)
    compatibility_presets = tuple(analysis for analysis in analyses if analysis.touched_by_multiple_mods)

    safe_presets: list[PlannedPreset] = []
    runtime_safe_overlaps: list[PlannedPreset] = []
    unresolved_presets: list[PlannedPreset] = []

    for analysis in compatibility_presets:
        planned = _plan_preset(analysis)
        if planned.status == "runtime_safe_additive_overlap":
            runtime_safe_overlaps.append(planned)
        elif planned.status == "safe_generation_candidate":
            safe_presets.append(planned)
        else:
            unresolved_presets.append(planned)

    return MergePlan(
        runtime_semantics_note=RUNTIME_SEMANTICS_NOTE,
        safe_presets=tuple(sorted(safe_presets, key=lambda preset: preset.name.casefold())),
        runtime_safe_additive_overlaps=tuple(sorted(runtime_safe_overlaps, key=lambda preset: preset.name.casefold())),
        unresolved_presets=tuple(sorted(unresolved_presets, key=lambda preset: preset.name.casefold())),
        parse_issues=scan_result.parse_issues,
        recovery_issues=scan_result.recovery_issues,
        path_issues=scan_result.path_issues,
    )


def merge_plan_to_report(plan: MergePlan) -> dict:
    report = _jsonable(asdict(plan))
    report["would_generate_xml"] = merge_plan_to_xml(plan)
    report["generation_blocked"] = bool(plan.parse_issues or plan.unresolved_presets)
    return report


def write_merge_plan_report(plan: MergePlan, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(merge_plan_to_report(plan), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def merge_plan_to_xml(plan: MergePlan) -> str:
    root = ET.Element(
        "database",
        {
            "name": "barbora",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:noNamespaceSchemaLocation": "InventoryPreset.xsd",
        },
    )
    presets_element = ET.SubElement(root, "InventoryPresets", {"version": "2"})

    for preset in plan.safe_presets:
        preset_element = ET.SubElement(presets_element, "InventoryPreset", dict(preset.attributes))
        for child in preset.children:
            ET.SubElement(preset_element, child.tag, dict(child.attributes))

    ET.indent(root, space="    ")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def _plan_preset(analysis: PresetAnalysis) -> PlannedPreset:
    contributions = tuple(sorted(analysis.contributions, key=_contribution_sort_key))
    unresolved_reasons: list[str] = []
    diagnostics: list[str] = []

    if analysis.preset_attribute_conflicts:
        unresolved_reasons.extend(_format_attribute_conflict(finding) for finding in analysis.preset_attribute_conflicts)

    for finding in analysis.preset_attribute_omissions:
        diagnostics.append(_format_attribute_omission(finding))

    unsupported = [
        (preset, child)
        for preset in contributions
        for child in preset.unsupported_children
    ]
    if unsupported:
        tags = sorted({child.tag for _preset, child in unsupported}, key=str.casefold)
        unresolved_reasons.append(
            "unsupported child elements in multi-mod preset: " + ", ".join(tags)
        )

    duplicate_messages, duplicate_blockers = _classify_duplicate_children(contributions)
    diagnostics.extend(duplicate_messages)
    unresolved_reasons.extend(duplicate_blockers)

    same_name_diagnostics, same_name_blockers = _same_analysis_key_differing_attributes(contributions)
    diagnostics.extend(same_name_diagnostics)
    unresolved_reasons.extend(same_name_blockers)

    attributes = _resolved_preset_attributes(contributions)
    children = tuple(
        PlannedChild(
            tag=child.tag,
            attributes=_ordered_attributes(child.attributes),
            source_mod=preset.source.mod_name,
            source_file=preset.source.relative_path,
            source_preset_index=preset.source_preset_index,
            source_child_index=child.source_child_index,
        )
        for preset in contributions
        for child in sorted(preset.children, key=lambda item: item.source_child_index)
    )

    status = _planned_status(unresolved_reasons, children)
    return PlannedPreset(
        name=analysis.preset_name,
        status=status,
        attributes=attributes,
        children=() if unresolved_reasons else children,
        source_mods=tuple(sorted({preset.source.mod_name for preset in contributions}, key=str.casefold)),
        unresolved_reasons=tuple(sorted(set(unresolved_reasons), key=str.casefold)),
        diagnostics=tuple(sorted(set(diagnostics), key=str.casefold)),
    )


def _planned_status(unresolved_reasons: list[str], children: tuple[PlannedChild, ...]) -> str:
    if unresolved_reasons:
        return "unresolved"
    if children:
        return "runtime_safe_additive_overlap"
    return "safe_generation_candidate"


def _resolved_preset_attributes(contributions: tuple[PresetRecord, ...]) -> tuple[tuple[str, str], ...]:
    values: dict[str, str] = {}
    for preset in contributions:
        for key, value in preset.attributes.items():
            values.setdefault(key, value)
    values["Name"] = contributions[0].name
    return _ordered_attributes(values)


def _classify_duplicate_children(contributions: tuple[PresetRecord, ...]) -> tuple[list[str], list[str]]:
    by_full_signature: dict[tuple[str, tuple[tuple[str, str], ...]], list[tuple[PresetRecord, int]]] = defaultdict(list)
    for preset in contributions:
        for child in preset.children:
            by_full_signature[(child.tag, _ordered_attributes(child.attributes))].append((preset, child.source_child_index))

    diagnostics: list[str] = []
    blockers: list[str] = []
    for (tag, attributes), entries in sorted(by_full_signature.items(), key=lambda item: _signature_sort_key(item[0])):
        if len(entries) < 2:
            continue
        mods = {preset.source.mod_name for preset, _index in entries}
        description = f"{tag} {_format_attributes(attributes)}"
        if len(mods) > 1:
            blockers.append(
                "ambiguous identical child independently contributed by multiple mods: "
                f"{description} [{', '.join(sorted(mods, key=str.casefold))}]"
            )
        else:
            preset = entries[0][0]
            diagnostics.append(
                "duplicate child within one source contribution preserved for preview: "
                f"{description} [{preset.source.mod_name}:{preset.source.relative_path.as_posix()}]"
            )
    return diagnostics, blockers


def _same_analysis_key_differing_attributes(contributions: tuple[PresetRecord, ...]) -> tuple[list[str], list[str]]:
    by_analysis_key: dict[tuple[str, str | None], list[tuple[PresetRecord, tuple[tuple[str, str], ...]]]] = defaultdict(list)
    for preset in contributions:
        for child in preset.children:
            by_analysis_key[(child.tag, child.name)].append((preset, _ordered_attributes(child.attributes)))

    diagnostics: list[str] = []
    blockers: list[str] = []
    for (tag, name), entries in sorted(by_analysis_key.items(), key=lambda item: (item[0][0].casefold(), item[0][1] or "")):
        variants = {attributes for _preset, attributes in entries}
        if len(variants) > 1:
            mods = {preset.source.mod_name for preset, _attributes in entries}
            message = f"same logical child has differing attributes: {tag} Name={name or '<missing Name>'}"
            if len(mods) > 1:
                blockers.append(message + f" [{', '.join(sorted(mods, key=str.casefold))}]")
            else:
                diagnostics.append(message + " within one mod; preserved for analysis")
    return diagnostics, blockers


def _format_attribute_conflict(finding: PresetAttributeFinding) -> str:
    explicit = ", ".join(
        f'{value} [{", ".join(mods)}]'
        for value, mods in finding.explicit_values
    )
    return f"conflicting explicit preset attribute {finding.attribute}: {explicit}"


def _format_attribute_omission(finding: PresetAttributeFinding) -> str:
    explicit = ", ".join(
        f'{value} [{", ".join(mods)}]'
        for value, mods in finding.explicit_values
    )
    omitted = ", ".join(finding.omitted_by_mods)
    return f"compatible preset attribute omission {finding.attribute}: explicit {explicit}; omitted by {omitted}"


def _ordered_attributes(attributes: dict[str, str] | tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    items = dict(attributes).items()
    return tuple(sorted(items, key=lambda item: (0 if item[0] == "Name" else 1, item[0].casefold())))


def _format_attributes(attributes: tuple[tuple[str, str], ...]) -> str:
    return " ".join(f'{key}="{value}"' for key, value in attributes)


def _signature_sort_key(signature: tuple[str, tuple[tuple[str, str], ...]]) -> tuple[str, str]:
    tag, attributes = signature
    return (tag.casefold(), _format_attributes(attributes).casefold())


def _contribution_sort_key(preset: PresetRecord) -> tuple[str, str, int]:
    return (
        preset.source.mod_name.casefold(),
        str(preset.source.relative_path).casefold(),
        preset.source_preset_index,
    )


def _jsonable(value):
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value
