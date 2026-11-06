"""Internet Archive (archive.org) : films et séries du domaine public, en torrent.

Source livrée en exemple, légale : seuls les éléments marqués « domaine public » sont listés,
hors dépôts non triés. archive.org sert lui-même les fichiers (webseed) : il n'y a pas de
nombre de seeders, et le tri « seeders » se fait sur la popularité (nombre de téléchargements).
"""
import re
import urllib.parse
from contextlib import contextmanager

from errors import RemoteError
from httpclient import Throttle, get, get_json
from models import ProviderPage, Query, Release
from providers.base import Provider
from releases import describe

IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
QUERY_SYNTAX = re.compile(r'[+\-&|!(){}\[\]^"~*?:\\/]')  # caractères spéciaux de la syntaxe de recherche
TITLE_YEAR = re.compile(r"\s*\((?:19|20)\d{2}\).*$")  # « Titre (1968) - restored » -> « Titre »
YEAR = re.compile(r"(?:19|20)\d{2}")


class InternetArchive(Provider):
    key = "internet_archive"
    label = "Internet Archive"
    native_filters = frozenset({"text", "kind"})

    BASE_URL = "https://archive.org"
    PAGE_SIZE = 100
    COLLECTIONS = {"movie": "feature_films", "tv": "classic_tv"}
    FILTERS = ("mediatype:(movies)", "licenseurl:(*publicdomain*)", "-collection:(feature_films_unsorted)")
    SORTS = {
        "seeders": "downloads desc",
        "size_desc": "item_size desc",
        "size_asc": "item_size asc",
        "date": "publicdate desc",
    }
    FIELDS = ("identifier", "title", "year", "item_size", "publicdate", "collection")
    MIN_INTERVAL_S = 1.0

    def __init__(self):
        self._throttle = Throttle(self.MIN_INTERVAL_S)

    def search(self, query: Query, page: int) -> ProviderPage:
        kinds = ("movie", "tv") if query.kind == "all" else (query.kind,)
        terms = [*self.FILTERS, f"collection:({' OR '.join(self.COLLECTIONS[kind] for kind in kinds)})"]
        # En minuscules, AND, OR et NOT ne sont plus des opérateurs
        words = QUERY_SYNTAX.sub(" ", query.text).lower().split()
        if words:
            terms.append(f"title:({' AND '.join(words)})")
        params = [
            ("q", " AND ".join(terms)),
            *(("fl[]", name) for name in self.FIELDS),
            ("sort[]", self.SORTS[query.sort]),
            ("rows", self.PAGE_SIZE),
            ("page", page),
            ("output", "json"),
        ]
        self._throttle.wait()
        data = get_json(f"{self.BASE_URL}/advancedsearch.php?{urllib.parse.urlencode(params)}")
        with _expected_format():
            total = data["response"]["numFound"]
            return ProviderPage(
                releases=[self._release(doc) for doc in data["response"]["docs"]],
                last=page * self.PAGE_SIZE >= total,
                total=total,
            )

    def download(self, release_id: str) -> bytes:
        if not IDENTIFIER.fullmatch(release_id):
            raise RemoteError("Identifiant Internet Archive invalide")
        self._throttle.wait()
        return get(f"{self.BASE_URL}/download/{release_id}/{release_id}_archive.torrent")

    def _release(self, doc: dict) -> Release:
        identifier = doc["identifier"]
        title = str(_first(doc.get("title")) or identifier)
        # La résolution ou la source figurent parfois dans l'identifiant (« …_1080p », « …_dvd »)
        info = describe(f"{title} {identifier}")
        year = YEAR.search(str(_first(doc.get("year")) or ""))
        return Release(
            id=identifier,
            provider=self.key,
            title=title,
            name=TITLE_YEAR.sub("", title) or title,
            original_title="",
            year=year.group() if year else info.year,
            kind="tv" if self.COLLECTIONS["tv"] in _values(doc.get("collection")) else "movie",
            season=info.season,
            resolution=info.resolution,
            langs=info.langs,
            source=info.source,
            hdr=info.hdr,
            codec=info.codec,
            size=int(doc.get("item_size") or 0),
            seeders=None,
            date=doc.get("publicdate") or "",
            url=f"{self.BASE_URL}/details/{identifier}",
        )


def _values(value) -> list:
    """Certains champs sont tantôt une valeur, tantôt une liste de valeurs."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _first(value):
    values = _values(value)
    return values[0] if values else None


@contextmanager
def _expected_format():
    try:
        yield
    except (KeyError, TypeError, ValueError) as e:
        raise RemoteError("Réponse inattendue d'Internet Archive : son API a peut-être changé") from e
