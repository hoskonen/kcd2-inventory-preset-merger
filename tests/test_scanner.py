from pathlib import Path
import unittest

from kcd2_inventory_preset_merger.scanner import discover_inventory_preset_files, scan_mods


class ScannerTests(unittest.TestCase):
    def test_discover_inventory_preset_files_identifies_top_level_mods(self):
        files = discover_inventory_preset_files(Path("fixtures/mods"))

        names = [(file.mod_name, file.relative_path.as_posix()) for file in files]
        self.assertEqual(
            names,
            [
                ("mod_a", "mod_a/Data/Libs/Tables/item/InventoryPreset__mod_a.xml"),
                ("mod_b", "mod_b/Data/Libs/Tables/item/InventoryPreset__mod_b.xml"),
                ("mod_duplicate", "mod_duplicate/Data/Libs/Tables/item/InventoryPreset__duplicate.xml"),
                ("mod_encoding", "mod_encoding/Data/Libs/Tables/item/InventoryPreset__encoding.xml"),
                ("mod_invalid", "mod_invalid/Data/Libs/Tables/item/InventoryPreset__broken.xml"),
                ("mod_modid_layout", "mod_modid_layout/Data/mod_modid_layout/Libs/Tables/Item/InventoryPreset__modid_layout.xml"),
                ("mod_suspicious", "mod_suspicious/Data/SomewhereElse/item/InventoryPreset__suspicious.xml"),
            ],
        )

    def test_scan_reports_parse_errors_without_discarding_valid_files(self):
        result = scan_mods(Path("fixtures/mods"))

        self.assertEqual(len(result.files), 7)
        self.assertEqual(len(result.parse_issues), 1)
        self.assertIn("InventoryPreset__broken.xml", str(result.parse_issues[0].path))
        self.assertIn("XML parse error", result.parse_issues[0].error)
        self.assertEqual(len(result.recovery_issues), 1)
        self.assertIn("InventoryPreset__encoding.xml", str(result.recovery_issues[0].path))
        self.assertIn("encoding_mismatch_recovered", result.recovery_issues[0].error)
        self.assertTrue(any(preset.name == "inventory_shop_commonMerchant" for preset in result.presets))

    def test_scan_reports_suspicious_inventory_preset_paths(self):
        result = scan_mods(Path("fixtures/mods"))

        suspicious_paths = {issue.path.name for issue in result.path_issues}
        self.assertEqual(suspicious_paths, {"InventoryPreset__suspicious.xml"})
        self.assertTrue(all("suspicious_inventory_preset_path" in issue.error for issue in result.path_issues))
        self.assertTrue(all("not evidence that a mod will not load" in issue.error for issue in result.path_issues))


if __name__ == "__main__":
    unittest.main()
