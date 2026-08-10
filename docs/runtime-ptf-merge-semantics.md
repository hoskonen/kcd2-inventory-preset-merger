# Runtime PTF Merge Semantics Experiment

This manual experiment checks how KCD2 handles two enabled mods that patch the same vanilla `InventoryPreset`.

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

## Test 1: Two Source Mods, No Compatibility Patch

1. Copy only these two folders into the game `Mods` directory:

```text
fixtures/runtime_ptf_merge_semantics/kcd2_ipm_ptf_a
fixtures/runtime_ptf_merge_semantics/kcd2_ipm_ptf_b
```

2. Start the game and inspect an innkeeper whose inventory uses `inventory_shop_commonInnkeeper`.

3. Record whether the test money/ref signal shows:

```text
A only: likely Mod A survived and Mod B did not
B only: likely Mod B survived and Mod A did not
A + B once each: both source patches coexist
neither: path, preset, item/ref, or test observation method is wrong
other/duplicated: runtime behavior needs closer inspection
```

4. Swap load order if your mod manager supports it, then repeat.

This determines whether the base PTF behavior is additive, last-wins, load-order-dependent, or something else.

## Test 2: Add Simulated Load-Last Compatibility Patch

1. Keep Mod A and Mod B enabled.

2. Also copy/enable:

```text
fixtures/runtime_ptf_merge_semantics/kcd2_ipm_ptf_ab_loadlast
```

3. Make sure it loads after both source mods.

4. Inspect the same innkeeper again.

Record whether the test signal shows:

```text
333 total: compatibility patch restored a missing additive result without duplication
666 total or visibly doubled: emitting both children again duplicates already-applied changes
111 or 222: load-last patch did not combine as expected
other: runtime behavior needs closer inspection
```

## Why This Blocks Production Generation

Milestone 2 must not assume that writing both source children into a load-last patch is safe. If KCD2 already applies both source patches additively, a generated patch may duplicate the same selection sources. If KCD2 is last-wins, a generated patch may be necessary. This experiment tells us which behavior we are actually targeting.

