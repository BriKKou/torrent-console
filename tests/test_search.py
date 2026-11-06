import unittest

from errors import RateLimited
from models import Account, ProviderPage, Query, Release
from providers.base import Provider
from search import SearchService


def release(n: int, *, size_gb: float = 1, source: str = "WEB-DL", langs=("MULTI",)) -> Release:
    return Release(id=f"id{n}", provider="fake", title=f"Film.{n}", name=f"Film {n}", original_title="", year="2024",
                   kind="movie", season="", resolution="1080p", langs=tuple(langs), source=source, hdr=(), codec="",
                   size=int(size_gb * 1e9), seeders=1000 - n, date="2026-11-05T12:00:00Z", url="")


class FakeProvider(Provider):
    """Source triée côté site, qui ne sait filtrer que par type."""
    key = "fake"
    label = "Fake"
    native_filters = frozenset({"kind"})

    def __init__(self, releases, page_size=100, fail_after=None):
        self.releases, self.page_size, self.fail_after, self.calls = releases, page_size, fail_after, 0

    def search(self, query, page):
        self.calls += 1
        if self.fail_after is not None and self.calls > self.fail_after:
            raise RateLimited("trop de requêtes")
        start = (page - 1) * self.page_size
        return ProviderPage(self.releases[start:start + self.page_size],
                            last=start + self.page_size >= len(self.releases), total=len(self.releases))

    def download(self, release_id):
        return b""


class SearchServiceTest(unittest.TestCase):
    def test_batches_follow_each_other_without_gaps(self):
        service = SearchService([FakeProvider([release(n) for n in range(250)])])
        first = service.search("fake", Query())
        second = service.search("fake", Query(), offset=30)
        self.assertEqual([r.id for r in first.releases + second.releases], [f"id{n}" for n in range(60)])
        self.assertTrue(second.more)
        self.assertTrue(first.exact)

    def test_local_filters_fill_the_batch_from_following_pages(self):
        releases = [release(n, size_gb=20 if n % 4 else 2) for n in range(400)]  # 1 sur 4 fait moins de 8 Go
        provider = FakeProvider(releases)
        batch = SearchService([provider]).search("fake", Query(max_gb=8))
        self.assertEqual(len(batch.releases), 30)
        self.assertTrue(all(r.size <= 8e9 for r in batch.releases))
        self.assertEqual(provider.calls, 2)
        self.assertFalse(batch.exact)

    def test_local_filter_change_reuses_cached_pages(self):
        provider = FakeProvider([release(n, source="BluRay" if n % 2 else "WEB-DL") for n in range(80)])
        service = SearchService([provider])
        service.search("fake", Query(sources=("WEB-DL",)))
        service.search("fake", Query(sources=("BluRay",)))
        self.assertEqual(provider.calls, 1)

    def test_duplicates_from_shifting_pages_are_dropped(self):
        releases = [release(n) for n in range(100)]
        provider = FakeProvider(releases + releases[90:], page_size=100)
        batch = SearchService([provider]).search("fake", Query(), offset=90)
        self.assertEqual([r.id for r in batch.releases], [f"id{n}" for n in range(90, 100)])
        self.assertFalse(batch.more)

    def test_rate_limit_after_partial_results_is_reported(self):
        provider = FakeProvider([release(n, size_gb=20 if n else 2) for n in range(500)], fail_after=1)
        batch = SearchService([provider]).search("fake", Query(max_gb=8))
        self.assertEqual(len(batch.releases), 1)
        self.assertTrue(batch.limited)

    def test_rate_limit_without_results_raises(self):
        provider = FakeProvider([release(n) for n in range(10)], fail_after=0)
        with self.assertRaises(RateLimited):
            SearchService([provider]).search("fake", Query())

    def test_vf2_counts_as_vff_and_vfq(self):
        self.assertTrue(release(1, langs=("MULTI", "VF2")).has_lang("VFQ"))
        self.assertFalse(release(1, langs=("VOSTFR",)).has_lang("VFF"))

    def test_versions_keep_same_title_sorted_by_resolution_then_size(self):
        def version(n, name, resolution, size_gb):
            return Release(id=f"v{n}", provider="fake", title=f"{name}.2024.{resolution}", name=name, original_title="",
                           year="2024", kind="movie", season="", resolution=resolution, langs=(), source="WEB-DL",
                           hdr=(), codec="", size=int(size_gb * 1e9), seeders=1, date="", url="")
        provider = FakeProvider([version(1, "Dune", "1080p", 3), version(2, "Dune", "2160p", 8), version(3, "Dune", "1080p", 6),
                                 version(4, "Dune Messiah", "2160p", 9), version(5, "Dune", "2160p", 15)])
        found = SearchService([provider]).versions("fake", "movie", "Dune.2024.1080p", "Dune", "2024")
        self.assertEqual([r.id for r in found], ["v5", "v2", "v3", "v1"])

    def test_account_ratio(self):
        self.assertEqual(Account("u", uploaded=300, downloaded=125).ratio, 2.4)
        self.assertIsNone(Account("u", uploaded=300, downloaded=0).ratio)
        self.assertIsNone(FakeProvider([]).account())

    def test_invalid_query_is_rejected(self):
        with self.assertRaises(ValueError):
            Query(sort="random")


if __name__ == "__main__":
    unittest.main()
