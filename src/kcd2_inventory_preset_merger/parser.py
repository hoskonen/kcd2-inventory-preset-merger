from __future__ import annotations

import xml.etree.ElementTree as ET
import re

from .models import InventoryPresetFile, PresetChild, PresetRecord


SUPPORTED_CHILD_TAGS = frozenset({"PresetItem", "InventoryPresetRef"})
ASCII_DECLARATION_RE = re.compile(br"<\?xml[^>]*encoding\s*=\s*['\"]us-ascii['\"][^>]*\?>", re.IGNORECASE)
ENCODING_DECLARATION_RE = re.compile(br"(encoding\s*=\s*['\"])us-ascii(['\"])", re.IGNORECASE)


class InventoryPresetParseError(Exception):
    pass


def parse_inventory_preset_file(
    source: InventoryPresetFile,
    recovery_issues: list[str] | None = None,
) -> tuple[PresetRecord, ...]:
    try:
        tree = ET.parse(source.path)
    except ET.ParseError as exc:
        tree = _retry_ascii_declared_utf8(source, exc, recovery_issues)
    except OSError as exc:
        raise InventoryPresetParseError(f"unable to read file: {exc}") from exc

    return _parse_tree(source, tree)


def _retry_ascii_declared_utf8(
    source: InventoryPresetFile,
    original_error: ET.ParseError,
    recovery_issues: list[str] | None,
) -> ET.ElementTree:
    try:
        raw = source.path.read_bytes()
    except OSError as exc:
        raise InventoryPresetParseError(f"unable to read file after XML parse error: {exc}") from exc

    if not ASCII_DECLARATION_RE.search(raw[:256]) or not _contains_non_ascii(raw):
        raise InventoryPresetParseError(f"XML parse error: {original_error}") from original_error

    repaired = ENCODING_DECLARATION_RE.sub(br"\1utf-8\2", raw, count=1)
    try:
        root = ET.fromstring(repaired)
    except ET.ParseError:
        raise InventoryPresetParseError(f"XML parse error: {original_error}") from original_error

    if recovery_issues is not None:
        recovery_issues.append(
            "encoding_mismatch_recovered: declared us-ascii but contained non-ASCII bytes; parsed as UTF-8 in memory"
        )
    return ET.ElementTree(root)


def _parse_tree(source: InventoryPresetFile, tree: ET.ElementTree) -> tuple[PresetRecord, ...]:
    records: list[PresetRecord] = []
    for element in tree.getroot().iter():
        if _local_name(element.tag) != "InventoryPreset":
            continue

        name = element.attrib.get("Name")
        if not name:
            continue

        children = tuple(
            PresetChild(
                tag=_local_name(child.tag),
                name=child.attrib.get("Name"),
                attributes=dict(child.attrib),
            )
            for child in list(element)
            if _local_name(child.tag) in SUPPORTED_CHILD_TAGS
        )

        records.append(
            PresetRecord(
                name=name,
                attributes=dict(element.attrib),
                children=children,
                source=source,
            )
        )

    return tuple(records)


def _contains_non_ascii(raw: bytes) -> bool:
    return any(byte > 0x7F for byte in raw)


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
