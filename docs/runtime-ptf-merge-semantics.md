# Runtime PTF Merge Semantics Evidence

This manual experiment checked how KCD2 handles two enabled mods that patch the same vanilla `InventoryPreset`.

Do not use a real save you care about. These are test mods only.

## Fixture Mods

The loose-file test mods live in:

```text
fixtures/runtime_ptf_merge_semantics/
```

They are intentionally small:

- `kcd2_ipm_ptf_a` patches `inventory_shop_commonInnkeeper` with `InventoryPresetRef Name="kcd2_ipm_runtime_a_money_ref"`
- `kcd2_ipm_ptf_b` patches `inventory_shop_commonInnkeeper` with `InventoryPresetRef Name="kcd2_ipm_runtime_b_money_ref"`
- `kcd2_ipm_ptf_ab_loadlast` simulates the future generated compatibility patch by adding both refs to the same vanilla preset

The ref targets are custom presets in the same source test mods and contain distinctive known `money` amounts:

- Mod A: `111`
- Mod B: `222`
- expected combined signal if both apply once: `333`

## Output Layout Target For Milestone 2

The future generated compatibility mod should use this layout:

```text
InventoryPresetMerge/
  mod.manifest
  InventoryPreset__merged.report.json
  Data/
    inventorypresetmerge/
      Libs/
        Tables/
          item/
            InventoryPreset__merged.xml
```

The default mod id/path should be deterministic: `inventorypresetmerge`. It can be configurable later.

## Confirmed Result

Runtime testing confirmed that two separate enabled mods can patch the same `InventoryPreset` and both distinct `PresetItem` additions can appear simultaneously in-game.

```text
inventorytest_a added PresetItem Name="bandage_classic" Amount="100"
inventorytest_b added PresetItem Name="recipe_fevertonicPotion" Amount="100"
```

Both appeared simultaneously in the same merchant inventory with both mods enabled.

Therefore, purely additive overlaps with distinct child contributions are classified as:

```text
runtime_safe_additive_overlap
```

The tool should not generate a compatibility patch for purely additive overlaps by default.

## Still Ambiguous

The runtime behavior for ambiguous/repeated child structures is not yet established. Merge generation should still fail closed for:

- conflicting explicit preset-level attributes
- identical child contributions across mods where duplicate semantics are uncertain
- same logical child modified differently across mods
- unsupported/unknown child structures

Writing a load-last patch for a purely additive overlap could duplicate entries that the game already combines correctly.
