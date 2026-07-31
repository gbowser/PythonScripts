import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("dell_outlet_monitor.py")
SPEC = importlib.util.spec_from_file_location("dell_outlet_monitor", MODULE_PATH)
monitor = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = monitor
SPEC.loader.exec_module(monitor)


class PriceMatchingTests(unittest.TestCase):
    def test_accepts_common_exact_formats(self):
        for text in ("£3024", "£ 3024", "£3,024.00", "Price: £\xa03,024"):
            with self.subTest(text=text):
                self.assertTrue(monitor.price_matches(text, 302_400))

    def test_rejects_nearby_prices(self):
        for text in ("£302.40", "£3,024.99", "£30,240", "£2,999.00"):
            with self.subTest(text=text):
                self.assertFalse(monitor.price_matches(text, 302_400))

    def test_state_round_trip(self):
        listing = monitor.Listing(302_400, "Dell workstation", "https://example.test/1")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            monitor.save_state(path, [listing])
            self.assertEqual(monitor.load_active_fingerprints(path), {listing.fingerprint})


if __name__ == "__main__":
    unittest.main()
