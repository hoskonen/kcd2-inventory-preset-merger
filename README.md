# kcd2-inventory-preset-merger

Initial scanner/analyzer for Kingdom Come: Deliverance II `InventoryPreset__*.xml` mod patch files.

## Safety

Source mod files are read-only inputs. This milestone does not generate merged XML, rewrite source files, pack PAKs, or modify installed mods.

## Usage

```powershell
python -m kcd2_inventory_preset_merger scan --mods-path fixtures/mods
```

By default, the CLI reads `config.json`:

```json
{
  "mods_path": "path/to/KCD2/Mods",
  "output_path": "./output",
  "generated_mod_name": "InventoryPresetMerge"
}
```

`--mods-path` overrides the configured Mods directory.

## Current Scope

The scanner recursively discovers `InventoryPreset__*.xml`, identifies the top-level mod folder for each file, parses `InventoryPreset` records, and reports presets touched by more than one mod.

The analyzer distinguishes additive overlaps from likely conflicts. It currently tracks:

- preset seen in only one mod
- preset modified by multiple mods
- identical duplicate children
- additive children from different mods
- same child `Name` with differing attributes
- differing attributes on the `InventoryPreset` itself

Supported child element types for this milestone:

- `PresetItem`
- `InventoryPresetRef`

## Runtime Validation

Before merge generation is implemented, runtime PTF merge behavior must be validated in-game. See [docs/runtime-ptf-merge-semantics.md](docs/runtime-ptf-merge-semantics.md).
