from pathlib import Path
import unittest

from kcd2_inventory_preset_merger.models import InventoryPresetFile
from kcd2_inventory_preset_merger.parser import parse_inventory_preset_file


class ParserTests(unittest.TestCase):
    def test_parse_preserves_preset_and_supported_child_attributes(self):
        source = InventoryPresetFile(
            mod_name="mod_a",
            path=Path("fixtures/mods/mod_a/Data/Libs/Tables/item/InventoryPreset__mod_a.xml"),
            relative_path=Path("mod_a/Data/Libs/Tables/item/InventoryPreset__mod_a.xml"),
        )

        records = parse_inventory_preset_file(source)

        merchant = next(record for record in records if record.name == "inventory_shop_commonMerchant")
        self.assertEqual(merchant.attributes, {"Name": "inventory_shop_commonMerchant", "Mode": "All", "Health": "1"})
        self.assertEqual(len(merchant.children), 2)
        self.assertEqual(merchant.children[0].tag, "PresetItem")
        self.assertEqual(merchant.children[0].name, "apple")
        self.assertEqual(merchant.children[0].attributes, {"Name": "apple", "Amount": "1", "Quality": "2"})
        self.assertEqual(merchant.children[1].tag, "InventoryPresetRef")
        self.assertEqual(merchant.children[1].attributes, {"Name": "inventory_lantern_old_merchant"})

    def test_parse_preserves_repeated_presets_in_same_file(self):
        source = InventoryPresetFile(
            mod_name="mod_duplicate",
            path=Path("fixtures/mods/mod_duplicate/Data/Libs/Tables/item/InventoryPreset__duplicate.xml"),
            relative_path=Path("mod_duplicate/Data/Libs/Tables/item/InventoryPreset__duplicate.xml"),
        )

        records = parse_inventory_preset_file(source)

        repeated = [record for record in records if record.name == "inventory_repeated"]
        self.assertEqual(len(repeated), 2)
        self.assertEqual([record.children[0].name for record in repeated], ["first_item", "second_item"])


if __name__ == "__main__":
    unittest.main()
