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
    source_child_index: int = 0

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
    unsupported_children: tuple[PresetChild, ...]
    source: InventoryPresetFile
    source_preset_index: int = 0


@dataclass(frozen=True)
class ParseIssue:
    path: Path
    error: str


@dataclass(frozen=True)
class ScanResult:
    files: tuple[InventoryPresetFile, ...]
    presets: tuple[PresetRecord, ...]
    parse_issues: tuple[ParseIssue, ...]
    recovery_issues: tuple[ParseIssue, ...] = ()
    path_issues: tuple[ParseIssue, ...] = ()


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


@dataclass(frozen=True)
class PlannedChild:
    tag: str
    attributes: tuple[tuple[str, str], ...]
    source_mod: str
    source_file: Path
    source_preset_index: int
    source_child_index: int


@dataclass(frozen=True)
class LogicalChildVariant:
    tag: str
    name: str | None
    attributes: tuple[tuple[str, str], ...]
    source_mod: str
    source_file: Path
    source_preset_index: int
    source_child_index: int


@dataclass(frozen=True)
class PlannedPreset:
    name: str
    status: str
    attributes: tuple[tuple[str, str], ...]
    children: tuple[PlannedChild, ...]
    source_mods: tuple[str, ...]
    unresolved_reasons: tuple[str, ...]
    diagnostics: tuple[str, ...]
    logical_child_variants: tuple[LogicalChildVariant, ...] = ()


@dataclass(frozen=True)
class MergePlan:
    runtime_semantics_note: str
    safe_presets: tuple[PlannedPreset, ...]
    runtime_safe_additive_overlaps: tuple[PlannedPreset, ...]
    unresolved_presets: tuple[PlannedPreset, ...]
    parse_issues: tuple[ParseIssue, ...]
    recovery_issues: tuple[ParseIssue, ...]
    path_issues: tuple[ParseIssue, ...]
