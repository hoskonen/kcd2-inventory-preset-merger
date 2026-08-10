from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .conflicts import analyze_presets, build_preset_index
from .models import ChildFinding, PresetAnalysis
from .scanner import scan_mods


DEFAULT_CONFIG_PATH = Path("config.json")


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return _scan_command(args)

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

    if overlaps:
        print("")
        print("Overlaps:")
        for analysis in overlaps:
            _print_overlap(analysis)

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


def _print_overlap(analysis: PresetAnalysis) -> None:
    mods = ", ".join(sorted({preset.source.mod_name for preset in analysis.contributions}, key=str.casefold))
    print(f"- {analysis.preset_name}")
    print(f"  Mods: {mods}")
    for preset in analysis.contributions:
        print(f"  - {preset.source.mod_name}: {preset.source.relative_path.as_posix()}")

    labels: list[str] = []
    if analysis.preset_attribute_differences:
        labels.append("preset attribute differences")
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

    if analysis.preset_attribute_differences:
        print("  Preset attribute variants:")
        for attributes in analysis.preset_attribute_differences:
            print(f"  - {_format_attributes(attributes)}")


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


if __name__ == "__main__":
    raise SystemExit(main())
