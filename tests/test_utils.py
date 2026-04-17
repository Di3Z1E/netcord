import unittest
from src.netcord.utils import validate_ip, validate_prefix, prefix_to_mask, mask_to_prefix

class TestUtils(unittest.TestCase):
    def test_validate_ip(self):
        self.assertTrue(validate_ip("192.168.1.1"))
        self.assertTrue(validate_ip("0.0.0.0"))
        self.assertTrue(validate_ip("255.255.255.255"))
        self.assertFalse(validate_ip("256.1.1.1"))
        self.assertFalse(validate_ip("1.1.1"))
        self.assertFalse(validate_ip("a.b.c.d"))

    def test_validate_prefix(self):
        self.assertTrue(validate_prefix("0"))
        self.assertTrue(validate_prefix("24"))
        self.assertTrue(validate_prefix("32"))
        self.assertFalse(validate_prefix("-1"))
        self.assertFalse(validate_prefix("33"))
        self.assertFalse(validate_prefix("abc"))

    def test_prefix_to_mask(self):
        self.assertEqual(prefix_to_mask(24), "255.255.255.0")
        self.assertEqual(prefix_to_mask(8), "255.0.0.0")
        self.assertEqual(prefix_to_mask(32), "255.255.255.255")

    def test_mask_to_prefix(self):
        self.assertEqual(mask_to_prefix("255.255.255.0"), 24)
        self.assertEqual(mask_to_prefix("255.0.0.0"), 8)
        self.assertEqual(mask_to_prefix("255.255.255.255"), 32)
        self.assertIsNone(mask_to_prefix("invalid"))

if __name__ == "__main__":
    unittest.main()
