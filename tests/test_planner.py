from pathlib import Path
import unittest

from kcd2_inventory_preset_merger.planner import build_merge_plan, merge_plan_to_report, merge_plan_to_xml
from kcd2_inventory_preset_merger.scanner import scan_mods


class PlannerTests(unittest.TestCase):
    def test_build_merge_plan_classifies_safe_and_unresolved_presets(self):
        plan = build_merge_plan(scan_mods(Path("fixtures/mods")))

        safe_names = {preset.name for preset in plan.safe_presets}
        unresolved_names = {preset.name for preset in plan.unresolved_presets}

        self.assertIn("inventory_shop_commonMerchant", safe_names)
        self.assertIn("inventory_shop_armorerKHVinna", unresolved_names)
        self.assertIn("inventory_shop_commonBlacksmith", unresolved_names)

    def test_safe_plan_resolves_compatible_omitted_attributes(self):
        plan = build_merge_plan(scan_mods(Path("fixtures/mods")))
        merchant = next(preset for preset in plan.safe_presets if preset.name == "inventory_shop_commonMerchant")

        self.assertEqual(
            merchant.attributes,
            (("Name", "inventory_shop_commonMerchant"), ("Health", "1"), ("Mode", "All")),
        )
        self.assertEqual(
            [(child.tag, dict(child.attributes)["Name"], child.source_mod) for child in merchant.children],
            [
                ("PresetItem", "apple", "mod_a"),
                ("InventoryPresetRef", "inventory_lantern_old_merchant", "mod_a"),
                ("PresetItem", "bread", "mod_b"),
                ("InventoryPresetRef", "inventory_outer_garments_ref", "mod_b"),
            ],
        )

    def test_plan_blocks_cross_mod_identical_children_without_deduplicating(self):
        plan = build_merge_plan(scan_mods(Path("fixtures/mods")))
        blacksmith = next(preset for preset in plan.unresolved_presets if preset.name == "inventory_shop_commonBlacksmith")

        reasons = " ".join(blacksmith.unresolved_reasons)
        self.assertIn("ambiguous identical child independently contributed by multiple mods", reasons)
        self.assertFalse(blacksmith.children)

    def test_report_includes_xml_preview_and_runtime_warning(self):
        plan = build_merge_plan(scan_mods(Path("fixtures/mods")))
        report = merge_plan_to_report(plan)
        xml_preview = merge_plan_to_xml(plan)

        self.assertIn("Cross-mod KCD2 PTF runtime behavior", report["runtime_semantics_warning"])
        self.assertEqual(report["would_generate_xml"], xml_preview)
        self.assertIn("inventory_shop_commonMerchant", xml_preview)
        self.assertNotIn("inventory_shop_armorerKHVinna", xml_preview)


if __name__ == "__main__":
    unittest.main()
