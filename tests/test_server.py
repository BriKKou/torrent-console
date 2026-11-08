import unittest

from server import watches_interval_s


class WatchesIntervalTest(unittest.TestCase):
    def test_defaults_to_30_minutes(self):
        self.assertEqual(watches_interval_s({}), 30 * 60)

    def test_reads_the_configured_minutes(self):
        self.assertEqual(watches_interval_s({"watches": {"interval_minutes": 15}}), 15 * 60)

    def test_rejects_too_frequent_or_invalid_values(self):
        for minutes in (2, 0, "15", 7.5):
            with self.assertRaises(ValueError):
                watches_interval_s({"watches": {"interval_minutes": minutes}})


if __name__ == "__main__":
    unittest.main()
