"""Recherche par lots de 30 au-dessus des sources.

Les filtres que la source ne sait pas appliquer sont faits ici : on lit alors des pages
supplémentaires de la source (mises en cache) jusqu'à remplir le lot.
"""
import threading
import time
from dataclasses import dataclass, field

from errors import RateLimited
from models import FILTERS, Batch, Query, Release
from providers.base import Provider
from releases import describe

RESOLUTION_ORDER = ("2160p", "1080p", "720p", "SD")


@dataclass
class _Cursor:
    """Ce qui a déjà été lu chez une source pour une requête."""
    releases: list[Release] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)
    next_page: int = 1
    last: bool = False
    total: int | None = None
    created: float = field(default_factory=time.monotonic)


class SearchService:
    BATCH_SIZE = 30
    MAX_CALLS = 5       # pages lues au plus par lot, quand les filtres locaux écartent beaucoup
    CACHE_TTL_S = 600
    MAX_CURSORS = 50
    MAX_VERSION_PAGES = 3   # versions d'un même titre lues au plus (300 torrents)

    def __init__(self, providers: list[Provider]):
        self._providers = {provider.key: provider for provider in providers}
        self._cursors: dict[tuple, _Cursor] = {}
        self._lock = threading.Lock()

    def provider(self, key: str) -> Provider:
        if key not in self._providers:
            raise ValueError("Source inconnue")
        return self._providers[key]

    def versions(self, provider_key: str, kind: str, title: str, name: str, year: str, season: str = "") -> list[Release]:
        """Toutes les versions d'un titre chez la source (pas seulement celles de la recherche affichée),
        de la meilleure résolution à la moins bonne, puis de la plus grosse à la plus petite."""
        provider = self.provider(provider_key)
        # Le site cherche dans les noms de fichiers : « Dune Deuxieme Partie », pas « Dune : Deuxième partie »
        query = Query(text=describe(title).name, kind=kind)
        found: dict[str, Release] = {}
        for page in range(1, self.MAX_VERSION_PAGES + 1):
            result = provider.search(query, page)
            found.update((r.id, r) for r in result.releases)
            if result.last:
                break
        same_title = lambda r: (r.name.lower(), r.year, r.season.split("E")[0]) == (name.lower(), year, season.split("E")[0])
        rank = lambda r: RESOLUTION_ORDER.index(r.resolution) if r.resolution in RESOLUTION_ORDER else len(RESOLUTION_ORDER)
        return sorted((r for r in found.values() if same_title(r)), key=lambda r: (rank(r), -r.size))

    def search(self, provider_key: str, query: Query, offset: int = 0, refresh: bool = False) -> Batch:
        """Les résultats qui suivent les `offset` déjà affichés."""
        provider = self.provider(provider_key)
        local = FILTERS - provider.native_filters
        remote_query = query.without(local)
        with self._lock:
            cursor = self._cursor(provider, remote_query, refresh)
            found = [r for r in cursor.releases if query.accepts(r, local)]
            end = offset + self.BATCH_SIZE
            calls, limited = 0, False
            # un résultat de plus que le lot, pour savoir s'il y a une suite
            while len(found) <= end and not cursor.last and calls < self.MAX_CALLS:
                try:
                    page = provider.search(remote_query, cursor.next_page)
                except RateLimited:
                    if not found[offset:]:
                        raise
                    limited = True
                    break
                calls += 1
                cursor.next_page += 1
                cursor.last = page.last
                cursor.total = page.total
                fresh = [r for r in page.releases if r.id not in cursor.seen]
                cursor.seen.update(r.id for r in fresh)
                cursor.releases += fresh
                found += [r for r in fresh if query.accepts(r, local)]
            return Batch(
                releases=found[offset:end],
                more=len(found) > end or not cursor.last,
                total=cursor.total,
                exact=remote_query == query,
                limited=limited,
            )

    def _cursor(self, provider: Provider, query: Query, refresh: bool) -> _Cursor:
        key = (provider.key, query)
        cursor = self._cursors.get(key)
        if refresh or not cursor or time.monotonic() - cursor.created > self.CACHE_TTL_S:
            if len(self._cursors) >= self.MAX_CURSORS:
                self._cursors.clear()
            cursor = self._cursors[key] = _Cursor()
        return cursor
