from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .checker import CheckSummary, check_mods
from .conflicts import analyze_presets, build_preset_index
from .generator import (
    DEFAULT_GENERATED_MOD_ID,
    DEFAULT_GENERATED_MOD_NAME,
    GenerationBlocked,
    generate_compatibility_mod,
    source_mod_roots,
)
from .models import ChildFinding, PlannedChild, PlannedPreset, PresetAnalysis, PresetAttributeFinding
from .planner import build_merge_plan, merge_plan_to_report, write_merge_plan_report
from .scanner import scan_mods


DEFAULT_CONFIG_PATH = Path("config.json")


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return _scan_command(args)
    if args.command == "preview":
        return _preview_command(args)
    if args.command == "check":
        return _check_command(args)
    if args.command == "generate":
        return _generate_command(args)

    parser.print_help()
    return 2


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kcd2-inventory-preset-merger",
        description="Analyze KCD2 InventoryPreset mod patch files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan InventoryPreset patch files.")
    scan_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to JSON config file. Defaults to ./config.json.",
    )
    scan_parser.add_argument(
        "--mods-path",
        type=Path,
        help="Override the Mods directory from config.",
    )

    preview_parser = subparsers.add_parser("preview", help="Build a read-only merge preview plan.")
    preview_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to JSON config file. Defaults to ./config.json.",
    )
    preview_parser.add_argument(
        "--mods-path",
        type=Path,
        help="Override the Mods directory from config.",
    )
    preview_parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("output/merge_preview.report.json"),
        help="Where to write the JSON preview report. Defaults to ./output/merge_preview.report.json.",
    )

    check_parser = subparsers.add_parser("check", help="Check InventoryPreset interactions for conflicts.")
    check_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to JSON config file. Defaults to ./config.json.",
    )
    check_parser.add_argument(
        "--mods-path",
        type=Path,
        help="Override the Mods directory from config.",
    )
    check_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show safe overlaps and full child provenance.",
    )

    generate_parser = subparsers.add_parser("generate", help="Generate a separate InventoryPreset compatibility mod.")
    generate_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to JSON config file. Defaults to ./config.json.",
    )
    generate_parser.add_argument(
        "--mods-path",
        type=Path,
        help="Override the Mods directory from config.",
    )
    generate_parser.add_argument(
        "--output-path",
        type=Path,
        help="Directory where the generated mod folder should be written. Defaults to config output_path or ./output.",
    )
    generate_parser.add_argument(
        "--generated-mod-name",
        default=None,
        help=f"Generated mod folder/display name. Defaults to config generated_mod_name or {DEFAULT_GENERATED_MOD_NAME}.",
    )
    generate_parser.add_argument(
        "--generated-mod-id",
        default=None,
        help=f"Generated mod id and Data subfolder. Defaults to config generated_mod_id or {DEFAULT_GENERATED_MOD_ID}.",
    )

    return parser


def _scan_command(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    mods_path = args.mods_path or _config_path(config, "mods_path")
    if mods_path is None:
        print("No mods_path provided. Set it in config.json or pass --mods-path.")
        return 2

    result = scan_mods(mods_path)
    index = build_preset_index(result.presets)
    analyses = analyze_presets(index)
    overlaps = tuple(analysis for analysis in analyses if analysis.touched_by_multiple_mods)
    single_mod_presets = tuple(analysis for analysis in analyses if not analysis.touched_by_multiple_mods)

    print(f"Found {len(result.files)} InventoryPreset files")
    print(f"Found {len(index)} unique presets")
    print(f"{len(single_mod_presets)} presets seen in only one mod")
    print(f"{len(overlaps)} presets touched by multiple mods")

    if result.parse_issues:
        print("")
        print(f"Encountered {len(result.parse_issues)} XML parse errors:")
        for issue in result.parse_issues:
            print(f"- {issue.path}: {issue.error}")

    if result.recovery_issues:
        print("")
        print(f"Recovered {len(result.recovery_issues)} XML encoding mismatches:")
        for issue in result.recovery_issues:
            print(f"- {issue.path}: {issue.error}")

    if result.path_issues:
        print("")
        print(f"Found {len(result.path_issues)} suspicious InventoryPreset paths:")
        for issue in result.path_issues:
            print(f"- {issue.path}: {issue.error}")

    if overlaps:
        print("")
        print("Overlaps:")
        for analysis in overlaps:
            _print_overlap(analysis)

    return 0


def _preview_command(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    mods_path = args.mods_path or _config_path(config, "mods_path")
    if mods_path is None:
        print("No mods_path provided. Set it in config.json or pass --mods-path.")
        return 2

    mods_path = mods_path.expanduser().resolve()
    report_path = args.report_path.expanduser().resolve()
    if _is_relative_to(report_path, mods_path):
        print("Refusing to write preview report inside the scanned KCD2 Mods directory.")
        return 2

    result = scan_mods(mods_path)
    plan = build_merge_plan(result)
    report = merge_plan_to_report(plan)
    write_merge_plan_report(plan, report_path)

    print("Merge preview only. No KCD2 mod files were installed or modified.")
    print(plan.runtime_semantics_note)
    print(f"Found {len(plan.runtime_safe_additive_overlaps)} runtime-safe additive overlaps")
    print(f"Found {len(plan.safe_presets)} safe generation candidate presets")
    print(f"Found {len(plan.unresolved_presets)} unresolved presets")
    print(f"Found {len(plan.parse_issues)} parse errors")
    print(f"Found {len(plan.path_issues)} suspicious InventoryPreset paths")
    print(f"Wrote JSON preview report: {report_path}")
    if plan.safe_presets:
        print("")
        print("XML preview:")
        print(report["would_generate_xml"])
    else:
        print("No generation candidates; XML preview omitted.")

    if plan.unresolved_presets or plan.parse_issues:
        return 1
    return 0


def _check_command(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    mods_path = args.mods_path or _config_path(config, "mods_path")
    if mods_path is None:
        print("No mods_path provided. Set it in config.json or pass --mods-path.")
        return 2

    summary = check_mods(mods_path)
    _print_check_summary(summary, verbose=args.verbose)
    return 1 if summary.conflict_count or summary.parse_error_count else 0


def _generate_command(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    mods_path = args.mods_path or _config_path(config, "mods_path")
    if mods_path is None:
        print("No mods_path provided. Set it in config.json or pass --mods-path.")
        return 2

    mods_path = mods_path.expanduser().resolve()
    output_path = (args.output_path or _config_path(config, "output_path") or Path("output")).expanduser().resolve()
    generated_mod_name = args.generated_mod_name or config.get("generated_mod_name") or DEFAULT_GENERATED_MOD_NAME
    generated_mod_id = args.generated_mod_id or config.get("generated_mod_id") or DEFAULT_GENERATED_MOD_ID

    scan_result = scan_mods(mods_path)
    plan = build_merge_plan(scan_result)

    try:
        mod_root = generate_compatibility_mod(
            plan,
            output_path=output_path,
            generated_mod_name=generated_mod_name,
            generated_mod_id=generated_mod_id,
            source_mod_paths=source_mod_roots(mods_path, scan_result.files),
        )
    except GenerationBlocked as exc:
        print("InventoryPreset compatibility generation blocked.")
        print(str(exc))
        print("No compatibility mod was written.")
        return 1

    if mod_root is None:
        print("No InventoryPreset compatibility mod generated.")
        print("No mechanically safe generation candidates were found.")
        print("Runtime-safe additive overlaps are intentionally not generated.")
        return 0

    print("Generated InventoryPreset compatibility mod.")
    print(f"Output: {mod_root}")
    print(f"XML: {mod_root / 'Data' / generated_mod_id / 'Libs' / 'Tables' / 'item' / 'InventoryPreset__merged.xml'}")
    print(f"Report: {mod_root / 'merge-report.json'}")
    return 0


def _load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _config_path(config: dict[str, Any], key: str) -> Path | None:
    value = config.get(key)
    if not value:
        return None
    return Path(value)


def _is_relative_to(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
    except ValueError:
        return False
    return True


def _print_check_summary(summary: CheckSummary, *, verbose: bool) -> None:
    plan = summary.plan
    print("InventoryPreset conflict check")
    print("")
    print(f"{len(plan.runtime_safe_additive_overlaps)} runtime-safe additive overlaps")
    print(f"{summary.warning_count} warnings")
    print(f"{summary.conflict_count} conflicts")
    print(f"{summary.parse_error_count} parse errors")

    if plan.recovery_issues:
        print(f"{len(plan.recovery_issues)} non-blocking XML encoding warnings")
    if plan.path_issues:
        print(f"{len(plan.path_issues)} suspicious InventoryPreset paths")

    _print_check_category("WARNING same_logical_child_different_attributes", summary.same_logical_child_different_attributes)
    _print_check_category("WARNING identical_cross_mod_child", summary.identical_cross_mod_child)
    _print_check_category("CONFLICT preset_attribute_conflict", summary.preset_attribute_conflict)
    _print_check_category("UNRESOLVED unsupported_structure", summary.unsupported_structure)

    if plan.parse_issues:
        print("")
        print("ERROR parse_error")
        for issue in plan.parse_issues:
            print(f"{issue.path}")
            print(f"  {issue.error}")

    if verbose or not (summary.warning_count or summary.conflict_count or summary.parse_error_count):
        _print_safe_overlaps(plan.runtime_safe_additive_overlaps, verbose=verbose)

    if summary.warning_count or summary.conflict_count or summary.parse_error_count:
        print("")
        print("InventoryPreset interactions requiring attention were detected.")
    else:
        print("")
        print("No action required.")


def _print_check_category(label: str, presets: tuple[PlannedPreset, ...]) -> None:
    if not presets:
        return
    print("")
    print(label)
    for preset in presets:
        print(f"Preset: {preset.name}")
        for reason in preset.unresolved_reasons:
            print(f"  Reason: {reason}")


def _print_safe_overlaps(presets: tuple[PlannedPreset, ...], *, verbose: bool) -> None:
    if not presets:
        return
    print("")
    print("SAFE runtime_safe_additive_overlap")
    for preset in presets:
        print(f"Preset: {preset.name}")
        for mod in preset.source_mods:
            print(f"  Mod: {mod}")
            for child in _children_for_mod(preset, mod):
                print(f"    Child: {_format_planned_child(child)}")
                if verbose:
                    print(f"      Source: {child.source_file.as_posix()}")
                    print(f"      Source indexes: preset={child.source_preset_index}; child={child.source_child_index}")
        if verbose and preset.diagnostics:
            print("  Diagnostics:")
            for diagnostic in preset.diagnostics:
                print(f"    - {diagnostic}")


def _children_for_mod(preset: PlannedPreset, mod: str) -> tuple[PlannedChild, ...]:
    return tuple(child for child in preset.children if child.source_mod == mod)


def _format_planned_child(child: PlannedChild) -> str:
    attributes = dict(child.attributes)
    name = attributes.get("Name", "<missing Name>")
    rest = " ".join(f'{key}="{value}"' for key, value in child.attributes if key != "Name")
    return f"{child.tag} {name}" + (f" {rest}" if rest else "")


def _print_overlap(analysis: PresetAnalysis) -> None:
    mods = ", ".join(sorted({preset.source.mod_name for preset in analysis.contributions}, key=str.casefold))
    print(f"- {analysis.preset_name}")
    print(f"  Mods: {mods}")
    for preset in analysis.contributions:
        print(f"  - {preset.source.mod_name}: {preset.source.relative_path.as_posix()}")

    labels: list[str] = []
    if analysis.preset_attribute_conflicts:
        labels.append("preset attribute conflicts")
    if analysis.preset_attribute_omissions:
        labels.append("compatible preset attribute omissions")
    if analysis.identical_duplicate_children:
        labels.append("identical duplicate children")
    if analysis.additive_children:
        labels.append("additive children")
    if analysis.same_child_name_different_attributes:
        labels.append("same child Name with differing attributes")
    print(f"  Findings: {', '.join(labels) if labels else 'none'}")

    _print_child_findings("  Identical duplicates", analysis.identical_duplicate_children)
    _print_child_findings("  Additive children", analysis.additive_children)
    _print_child_findings("  Differing child attributes", analysis.same_child_name_different_attributes)

    _print_attribute_findings("  Preset attribute conflicts", analysis.preset_attribute_conflicts)
    _print_attribute_findings("  Compatible preset attribute omissions", analysis.preset_attribute_omissions)


def _print_child_findings(label: str, findings: tuple[ChildFinding, ...]) -> None:
    if not findings:
        return
    print(f"{label}:")
    for finding in findings:
        name = finding.identity.name if finding.identity.name is not None else "<missing Name>"
        mods = ", ".join(finding.mods)
        attrs = f" {_format_attributes(finding.attributes)}" if finding.attributes is not None else ""
        print(f"  - {finding.identity.tag} Name={name}{attrs} [{mods}]")


def _format_attributes(attributes: tuple[tuple[str, str], ...] | None) -> str:
    if attributes is None:
        return ""
    return " ".join(f'{key}="{value}"' for key, value in attributes)


def _print_attribute_findings(label: str, findings: tuple[PresetAttributeFinding, ...]) -> None:
    if not findings:
        return
    print(f"{label}:")
    for finding in findings:
        explicit = ", ".join(
            f'{value} [{", ".join(mods)}]'
            for value, mods in finding.explicit_values
        )
        omitted = ", ".join(finding.omitted_by_mods) if finding.omitted_by_mods else "none"
        print(f"  - {finding.attribute}: explicit {explicit}; omitted by {omitted}")


if __name__ == "__main__":
    raise SystemExit(main())
