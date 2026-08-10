from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import MergePlan, PlannedPreset
from .planner import build_merge_plan
from .scanner import scan_mods


@dataclass(frozen=True)
class CheckSummary:
    plan: MergePlan
    same_logical_child_different_attributes: tuple[PlannedPreset, ...]
    identical_cross_mod_child: tuple[PlannedPreset, ...]
    preset_attribute_conflict: tuple[PlannedPreset, ...]
    unsupported_structure: tuple[PlannedPreset, ...]

    @property
    def warning_count(self) -> int:
        return len(self.same_logical_child_different_attributes) + len(self.identical_cross_mod_child)

    @property
    def conflict_count(self) -> int:
        return len(self.preset_attribute_conflict) + len(self.unsupported_structure)

    @property
    def parse_error_count(self) -> int:
        return len(self.plan.parse_issues)


def check_mods(mods_path: Path) -> CheckSummary:
    plan = build_merge_plan(scan_mods(mods_path))
    same_logical: list[PlannedPreset] = []
    identical: list[PlannedPreset] = []
    attribute_conflicts: list[PlannedPreset] = []
    unsupported: list[PlannedPreset] = []

    for preset in plan.unresolved_presets:
        reasons = " ".join(preset.unresolved_reasons)
        if "same logical child has differing attributes" in reasons:
            same_logical.append(preset)
        if "ambiguous identical child independently contributed by multiple mods" in reasons:
            identical.append(preset)
        if "conflicting explicit preset attribute" in reasons:
            attribute_conflicts.append(preset)
        if "unsupported child elements" in reasons:
            unsupported.append(preset)

    return CheckSummary(
        plan=plan,
        same_logical_child_different_attributes=tuple(same_logical),
        identical_cross_mod_child=tuple(identical),
        preset_attribute_conflict=tuple(attribute_conflicts),
        unsupported_structure=tuple(unsupported),
    )
