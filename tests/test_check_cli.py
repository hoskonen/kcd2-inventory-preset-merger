from contextlib import redirect_stdout
from io import StringIO
import unittest

from kcd2_inventory_preset_merger.main import main


class CheckCliTests(unittest.TestCase):
    def test_check_reports_safe_additive_overlap_without_conflict(self):
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["check", "--mods-path", "fixtures/check_safe"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("InventoryPreset conflict check", output)
        self.assertIn("1 runtime-safe additive overlaps", output)
        self.assertIn("0 warnings", output)
        self.assertIn("0 conflicts", output)
        self.assertIn("SAFE runtime_safe_additive_overlap", output)
        self.assertIn("Preset: inventory_check_safe", output)
        self.assertIn("  Mod: mod_check_a", output)
        self.assertIn("    Child: PresetItem bandage_classic", output)
        self.assertIn("No action required.", output)
        self.assertIn("No InventoryPreset conflicts requiring action were detected.", output)

    def test_check_verbose_shows_full_provenance(self):
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["check", "--mods-path", "fixtures/check_safe", "--verbose"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Source: mod_check_a/Data/Libs/Tables/item/InventoryPreset__check_a.xml", output)
        self.assertIn("Source indexes: preset=0; child=0", output)

    def test_check_returns_nonzero_for_parse_errors(self):
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["check", "--mods-path", "fixtures/mods"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("parse errors", output)
        self.assertIn("ERROR parse_error", output)
        self.assertIn("InventoryPreset interactions requiring attention were detected.", output)


if __name__ == "__main__":
    unittest.main()
