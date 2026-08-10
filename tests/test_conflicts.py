from pathlib import Path
import unittest

from kcd2_inventory_preset_merger.conflicts import analyze_presets, build_preset_index
from kcd2_inventory_preset_merger.scanner import scan_mods


def _analysis_by_name():
    result = scan_mods(Path("fixtures/mods"))
    index = build_preset_index(result.presets)
    return {analysis.preset_name: analysis for analysis in analyze_presets(index)}


class ConflictTests(unittest.TestCase):
    def test_build_index_preserves_same_preset_repeated_in_same_file(self):
        result = scan_mods(Path("fixtures/mods"))
        index = build_preset_index(result.presets)

        self.assertEqual(len(index["inventory_repeated"]), 2)

    def test_additive_children_are_not_treated_as_differing_child_attributes(self):
        analysis = _analysis_by_name()["inventory_shop_commonMerchant"]

        self.assertTrue(analysis.touched_by_multiple_mods)
        additive_names = {finding.identity.name for finding in analysis.additive_children}
        self.assertLessEqual(
            {"apple", "bread", "inventory_lantern_old_merchant", "inventory_outer_garments_ref"},
            additive_names,
        )
        self.assertFalse(analysis.same_child_name_different_attributes)
        self.assertFalse(analysis.preset_attribute_conflicts)

    def test_identical_duplicate_children_are_reported(self):
        analysis = _analysis_by_name()["inventory_shop_commonBlacksmith"]

        duplicate_names = {finding.identity.name for finding in analysis.identical_duplicate_children}
        self.assertIn("hammer", duplicate_names)

    def test_same_child_name_with_differing_attributes_is_reported(self):
        analysis = _analysis_by_name()["inventory_shop_armorerKHVinna"]

        differing_names = {finding.identity.name for finding in analysis.same_child_name_different_attributes}
        self.assertIn("money", differing_names)

    def test_preset_attribute_conflicts_require_different_explicit_values(self):
        analysis = _analysis_by_name()["inventory_shop_armorerKHVinna"]

        conflict_attributes = {finding.attribute for finding in analysis.preset_attribute_conflicts}
        self.assertIn("Mode", conflict_attributes)

    def test_preset_attribute_omissions_are_diagnostic_not_conflicts(self):
        analysis = _analysis_by_name()["inventory_shop_commonMerchant"]

        omission_attributes = {finding.attribute for finding in analysis.preset_attribute_omissions}
        self.assertLessEqual({"Mode", "Health"}, omission_attributes)
        self.assertFalse(analysis.preset_attribute_conflicts)


if __name__ == "__main__":
    unittest.main()
