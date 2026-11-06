import os
import tempfile
import unittest
from unittest import mock

import bitrates
from bitrates import BitrateCache
from models import ProviderPage
from providers import load, provider_class
from providers.base import Provider
from providers.internet_archive import InternetArchive


class CountingProvider(Provider):
    key = "counting"
    label = "Counting"
    native_filters = frozenset()

    def __init__(self):
        self.calls = 0

    def search(self, query, page):
        return ProviderPage([], last=True)

    def download(self, release_id):
        return b""

    def video_bitrate(self, release_id):
        self.calls += 1
        return None if release_id == "inconnu" else 5000


class RegistryTest(unittest.TestCase):
    def test_configured_providers_are_loaded_in_order(self):
        providers = load({"internet_archive": {}})
        self.assertIsInstance(providers[0], InternetArchive)

    def test_unknown_or_invalid_provider_is_reported(self):
        with self.assertRaises(ValueError):
            provider_class("introuvable")
        with self.assertRaises(ValueError):
            provider_class("../base")

    def test_optional_features(self):
        self.assertEqual(InternetArchive().features(), [])
        self.assertEqual(CountingProvider().features(), ["video_bitrate"])


class InternetArchiveTest(unittest.TestCase):
    def test_release_from_search_result(self):
        release = InternetArchive()._release({
            "identifier": "Night.Of.The.Living.Dead_1080p",
            "title": "Night of the Living Dead (1968) - restored",
            "year": 1968,
            "item_size": 4843135391,
            "publicdate": "2009-04-15T05:49:36Z",
            "collection": ["film_scifi", "feature_films"],
        })
        self.assertEqual((release.name, release.year, release.kind), ("Night of the Living Dead", "1968", "movie"))
        self.assertEqual(release.resolution, "1080p")
        self.assertIsNone(release.seeders)
        self.assertEqual(release.url, "https://archive.org/details/Night.Of.The.Living.Dead_1080p")

    def test_tv_and_single_values(self):
        release = InternetArchive()._release({"identifier": "Bonanza_pd", "title": ["Bonanza"], "collection": "classic_tv"})
        self.assertEqual((release.name, release.kind, release.year, release.size), ("Bonanza", "tv", "", 0))


class BitrateCacheTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "bitrates.json")
        self.provider = CountingProvider()

    def test_known_and_unknown_bitrates_are_kept_on_disk(self):
        BitrateCache(self.path).get(self.provider, "a")
        BitrateCache(self.path).get(self.provider, "inconnu")
        cache = BitrateCache(self.path)
        self.assertEqual((cache.get(self.provider, "a"), cache.get(self.provider, "inconnu")), (5000, None))
        self.assertEqual(self.provider.calls, 2)

    def test_least_recently_used_entries_go_first(self):
        cache = BitrateCache(self.path)
        with mock.patch.object(bitrates, "MAX_ENTRIES", 2):
            cache.get(self.provider, "a")
            cache.get(self.provider, "b")
            cache.get(self.provider, "a")  # « a » redevient le plus récent
            cache.get(self.provider, "c")  # « b » est oublié
            calls = self.provider.calls
            cache.get(self.provider, "a")
            self.assertEqual(self.provider.calls, calls)
            cache.get(self.provider, "b")
            self.assertEqual(self.provider.calls, calls + 1)


if __name__ == "__main__":
    unittest.main()
