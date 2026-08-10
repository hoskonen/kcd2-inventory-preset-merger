from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class InventoryPresetFile:
    mod_name: str
    path: Path
    relative_path: Path


@dataclass(frozen=True)
class ChildIdentity:
    tag: str
    name: str | None
    attributes: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @classmethod
    def from_child(
        cls,
        child: "PresetChild",
        *,
        include_attributes: bool = False,
    ) -> "ChildIdentity":
        return cls(
            tag=child.tag,
            name=child.name,
            attributes=tuple(sorted(child.attributes.items())) if include_attributes else (),
        )


@dataclass(frozen=True)
class PresetChild:
    tag: str
    name: str | None
    attributes: dict[str, str]

    @property
    def identity(self) -> ChildIdentity:
        return ChildIdentity.from_child(self)

    @property
    def full_identity(self) -> ChildIdentity:
        return ChildIdentity.from_child(self, include_attributes=True)


@dataclass(frozen=True)
class PresetRecord:
    name: str
    attributes: dict[str, str]
    children: tuple[PresetChild, ...]
    source: InventoryPresetFile


@dataclass(frozen=True)
class ParseIssue:
    path: Path
    error: str


@dataclass(frozen=True)
class ScanResult:
    files: tuple[InventoryPresetFile, ...]
    presets: tuple[PresetRecord, ...]
    parse_issues: tuple[ParseIssue, ...]


@dataclass(frozen=True)
class ChildFinding:
    identity: ChildIdentity
    attributes: tuple[tuple[str, str], ...] | None
    mods: tuple[str, ...]
    files: tuple[Path, ...]


@dataclass(frozen=True)
class PresetAttributeFinding:
    attribute: str
    explicit_values: tuple[tuple[str, tuple[str, ...]], ...]
    omitted_by_mods: tuple[str, ...]


@dataclass(frozen=True)
class PresetAnalysis:
    preset_name: str
    contributions: tuple[PresetRecord, ...]
    touched_by_multiple_mods: bool
    preset_attribute_conflicts: tuple[PresetAttributeFinding, ...]
    preset_attribute_omissions: tuple[PresetAttributeFinding, ...]
    identical_duplicate_children: tuple[ChildFinding, ...]
    additive_children: tuple[ChildFinding, ...]
    same_child_name_different_attributes: tuple[ChildFinding, ...]
