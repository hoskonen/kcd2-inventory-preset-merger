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
                ("mod_invalid", "mod_invalid/Data/Libs/Tables/item/InventoryPreset__broken.xml"),
            ],
        )

    def test_scan_reports_parse_errors_without_discarding_valid_files(self):
        result = scan_mods(Path("fixtures/mods"))

        self.assertEqual(len(result.files), 4)
        self.assertEqual(len(result.parse_issues), 1)
        self.assertIn("InventoryPreset__broken.xml", str(result.parse_issues[0].path))
        self.assertIn("XML parse error", result.parse_issues[0].error)
        self.assertTrue(any(preset.name == "inventory_shop_commonMerchant" for preset in result.presets))


if __name__ == "__main__":
    unittest.main()
