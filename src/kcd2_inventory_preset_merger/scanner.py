from __future__ import annotations

from pathlib import Path

from .models import InventoryPresetFile, ParseIssue, PresetRecord, ScanResult
from .parser import InventoryPresetParseError, parse_inventory_preset_file


INVENTORY_PRESET_PATTERN = "InventoryPreset__*.xml"


def discover_inventory_preset_files(mods_path: Path) -> tuple[InventoryPresetFile, ...]:
    mods_path = mods_path.expanduser().resolve()
    files: list[InventoryPresetFile] = []

    for path in sorted(mods_path.rglob(INVENTORY_PRESET_PATTERN), key=_path_sort_key):
        if not path.is_file():
            continue
        relative_path = path.relative_to(mods_path)
        mod_name = relative_path.parts[0] if relative_path.parts else path.stem
        files.append(
            InventoryPresetFile(
                mod_name=mod_name,
                path=path,
                relative_path=relative_path,
            )
        )

    return tuple(files)


def scan_mods(mods_path: Path) -> ScanResult:
    files = discover_inventory_preset_files(mods_path)
    presets: list[PresetRecord] = []
    parse_issues: list[ParseIssue] = []

    for file in files:
        try:
            presets.extend(parse_inventory_preset_file(file))
        except InventoryPresetParseError as exc:
            parse_issues.append(ParseIssue(path=file.path, error=str(exc)))

    return ScanResult(
        files=files,
        presets=tuple(presets),
        parse_issues=tuple(sorted(parse_issues, key=lambda issue: _path_sort_key(issue.path))),
    )


def _path_sort_key(path: Path) -> str:
    return str(path).casefold()
