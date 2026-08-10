from __future__ import annotations

import xml.etree.ElementTree as ET

from .models import InventoryPresetFile, PresetChild, PresetRecord


SUPPORTED_CHILD_TAGS = frozenset({"PresetItem", "InventoryPresetRef"})


class InventoryPresetParseError(Exception):
    pass


def parse_inventory_preset_file(source: InventoryPresetFile) -> tuple[PresetRecord, ...]:
    try:
        tree = ET.parse(source.path)
    except ET.ParseError as exc:
        raise InventoryPresetParseError(f"XML parse error: {exc}") from exc
    except OSError as exc:
        raise InventoryPresetParseError(f"unable to read file: {exc}") from exc

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


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag
