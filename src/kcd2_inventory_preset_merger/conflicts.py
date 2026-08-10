from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .models import ChildFinding, ChildIdentity, PresetAnalysis, PresetAttributeFinding, PresetRecord


def build_preset_index(presets: tuple[PresetRecord, ...]) -> dict[str, tuple[PresetRecord, ...]]:
    grouped: dict[str, list[PresetRecord]] = defaultdict(list)
    for preset in sorted(presets, key=_preset_sort_key):
        grouped[preset.name].append(preset)
    return {name: tuple(grouped[name]) for name in sorted(grouped, key=str.casefold)}


def analyze_presets(index: dict[str, tuple[PresetRecord, ...]]) -> tuple[PresetAnalysis, ...]:
    return tuple(_analyze_preset(name, index[name]) for name in sorted(index, key=str.casefold))


def _analyze_preset(name: str, contributions: tuple[PresetRecord, ...]) -> PresetAnalysis:
    mods = {preset.source.mod_name for preset in contributions}
    preset_attribute_conflicts, preset_attribute_omissions = _analyze_preset_attributes(contributions)

    by_child_identity: dict[ChildIdentity, list[tuple[PresetRecord, tuple[tuple[str, str], ...]]]] = defaultdict(list)
    for preset in contributions:
        for child in preset.children:
            by_child_identity[child.identity].append((preset, _attributes_key(child.attributes)))

    identical_duplicates: list[ChildFinding] = []
    additive_children: list[ChildFinding] = []
    differing_child_attributes: list[ChildFinding] = []

    for identity in sorted(by_child_identity, key=_child_identity_sort_key):
        entries = by_child_identity[identity]
        mods_for_identity = {preset.source.mod_name for preset, _attrs in entries}
        attr_sets = sorted({_attrs for _preset, _attrs in entries})

        if len(attr_sets) > 1:
            differing_child_attributes.append(
                ChildFinding(
                    identity=identity,
                    attributes=None,
                    mods=_sorted_mods(mods_for_identity),
                    files=_sorted_paths(preset.source.relative_path for preset, _attrs in entries),
                )
            )
            continue

        if len(mods_for_identity) > 1 or len(entries) > 1:
            identical_duplicates.append(
                ChildFinding(
                    identity=identity,
                    attributes=attr_sets[0],
                    mods=_sorted_mods(mods_for_identity),
                    files=_sorted_paths(preset.source.relative_path for preset, _attrs in entries),
                )
            )
        elif len(mods) > 1:
            additive_children.append(
                ChildFinding(
                    identity=identity,
                    attributes=attr_sets[0],
                    mods=_sorted_mods(mods_for_identity),
                    files=_sorted_paths(preset.source.relative_path for preset, _attrs in entries),
                )
            )

    return PresetAnalysis(
        preset_name=name,
        contributions=tuple(sorted(contributions, key=_preset_sort_key)),
        touched_by_multiple_mods=len(mods) > 1,
        preset_attribute_conflicts=preset_attribute_conflicts,
        preset_attribute_omissions=preset_attribute_omissions,
        identical_duplicate_children=tuple(identical_duplicates),
        additive_children=tuple(additive_children),
        same_child_name_different_attributes=tuple(differing_child_attributes),
    )


def _analyze_preset_attributes(
    contributions: tuple[PresetRecord, ...],
) -> tuple[tuple[PresetAttributeFinding, ...], tuple[PresetAttributeFinding, ...]]:
    attributes = sorted(
        {attribute for preset in contributions for attribute in preset.attributes},
        key=str.casefold,
    )
    conflicts: list[PresetAttributeFinding] = []
    omissions: list[PresetAttributeFinding] = []

    for attribute in attributes:
        values_by_mod: dict[str, set[str]] = defaultdict(set)
        omitted_by_mods: set[str] = set()

        for preset in contributions:
            if attribute in preset.attributes:
                values_by_mod[preset.attributes[attribute]].add(preset.source.mod_name)
            else:
                omitted_by_mods.add(preset.source.mod_name)

        explicit_values = tuple(
            (value, _sorted_mods(mods))
            for value, mods in sorted(values_by_mod.items(), key=lambda item: item[0].casefold())
        )
        finding = PresetAttributeFinding(
            attribute=attribute,
            explicit_values=explicit_values,
            omitted_by_mods=_sorted_mods(omitted_by_mods),
        )

        if len(values_by_mod) > 1:
            conflicts.append(finding)
        elif omitted_by_mods and values_by_mod:
            omissions.append(finding)

    return tuple(conflicts), tuple(omissions)


def _attributes_key(attributes: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(attributes.items()))


def _preset_sort_key(preset: PresetRecord) -> tuple[str, str, str]:
    return (
        preset.name.casefold(),
        preset.source.mod_name.casefold(),
        str(preset.source.relative_path).casefold(),
    )


def _child_identity_sort_key(identity: ChildIdentity) -> tuple[str, str]:
    return (identity.tag.casefold(), identity.name.casefold() if identity.name else "")


def _sorted_mods(mods: set[str]) -> tuple[str, ...]:
    return tuple(sorted(mods, key=str.casefold))


def _sorted_paths(paths) -> tuple[Path, ...]:
    return tuple(sorted(set(paths), key=lambda path: str(path).casefold()))
