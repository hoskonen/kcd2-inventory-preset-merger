from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import unittest

from kcd2_inventory_preset_merger.generator import GenerationBlocked, generate_compatibility_mod, validate_generated_mod
from kcd2_inventory_preset_merger.main import main
from kcd2_inventory_preset_merger.models import MergePlan, PlannedChild, PlannedPreset


TEST_OUTPUT_ROOT = Path(".test_output")


class GeneratorTests(unittest.TestCase):
    def tearDown(self):
        if TEST_OUTPUT_ROOT.exists():
            shutil.rmtree(TEST_OUTPUT_ROOT)

    def test_generate_command_skips_runtime_safe_additive_only_plan(self):
        output_path = TEST_OUTPUT_ROOT / "runtime_safe"
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["generate", "--mods-path", "fixtures/check_safe", "--output-path", str(output_path)])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("No InventoryPreset compatibility mod generated.", output)
        self.assertFalse((output_path / "InventoryPresetMerge").exists())

    def test_generate_command_blocks_unresolved_or_parse_error_plan(self):
        output_path = TEST_OUTPUT_ROOT / "blocked"
        stdout = StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["generate", "--mods-path", "fixtures/mods", "--output-path", str(output_path)])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 1)
        self.assertIn("InventoryPreset compatibility generation blocked.", output)
        self.assertFalse((output_path / "InventoryPresetMerge").exists())

    def test_generate_compatibility_mod_writes_expected_layout_for_safe_plan(self):
        plan = _safe_plan()
        output_path = TEST_OUTPUT_ROOT / "safe_plan"
        mod_root = generate_compatibility_mod(plan, output_path=output_path)

        self.assertIsNotNone(mod_root)
        assert mod_root is not None
        self.assertTrue((mod_root / "mod.manifest").exists())
        self.assertTrue((mod_root / "merge-report.json").exists())
        xml_path = (
            mod_root
            / "Data"
            / "inventorypresetmerge"
            / "Libs"
            / "Tables"
            / "item"
            / "InventoryPreset__merged.xml"
        )
        self.assertTrue(xml_path.exists())
        self.assertIn("inventory_generated", xml_path.read_text(encoding="utf-8"))
        validate_generated_mod(mod_root)

    def test_generated_mod_validation_rejects_unexpected_files(self):
        plan = _safe_plan()
        output_path = TEST_OUTPUT_ROOT / "unexpected_file"
        mod_root = generate_compatibility_mod(plan, output_path=output_path)
        assert mod_root is not None
        extra_file = mod_root / "Data" / "source_mod_file_should_not_be_here.xml"
        extra_file.write_text("<unexpected/>", encoding="utf-8")

        with self.assertRaises(GenerationBlocked):
            validate_generated_mod(mod_root)

    def test_generate_compatibility_mod_overwrites_stale_generated_files(self):
        plan = _safe_plan()
        output_path = TEST_OUTPUT_ROOT / "overwrite"
        mod_root = generate_compatibility_mod(plan, output_path=output_path)
        assert mod_root is not None
        stale_file = mod_root / "stale.txt"
        stale_file.write_text("old", encoding="utf-8")

        mod_root = generate_compatibility_mod(plan, output_path=output_path)

        assert mod_root is not None
        self.assertFalse(stale_file.exists())
        validate_generated_mod(mod_root)


def _safe_plan() -> MergePlan:
    return MergePlan(
        runtime_semantics_note="test",
        safe_presets=(
            PlannedPreset(
                name="inventory_generated",
                status="safe_generation_candidate",
                attributes=(("Name", "inventory_generated"), ("Mode", "All")),
                children=(
                    PlannedChild(
                        tag="InventoryPresetRef",
                        attributes=(("Name", "custom_ref"),),
                        source_mod="mod_a",
                        source_file=Path("mod_a/Data/Libs/Tables/item/InventoryPreset__mod_a.xml"),
                        source_preset_index=0,
                        source_child_index=0,
                    ),
                ),
                source_mods=("mod_a",),
                unresolved_reasons=(),
                diagnostics=(),
            ),
        ),
        runtime_safe_additive_overlaps=(),
        unresolved_presets=(),
        parse_issues=(),
        recovery_issues=(),
        path_issues=(),
    )


if __name__ == "__main__":
    unittest.main()
