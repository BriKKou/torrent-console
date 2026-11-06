"""Modèles partagés par les sources de torrents, la recherche et l'API HTTP."""
from dataclasses import dataclass, field, fields, replace

KINDS = ("all", "movie", "tv")
SORTS = ("seeders", "size_desc", "size_asc", "date")
# Filtres de Query. Une source applique elle-même ceux qu'elle sait faire (Provider.native_filters),
# la recherche applique les autres.
FILTERS = frozenset({"text", "kind", "langs", "resolutions", "sources", "max_gb"})


@dataclass(frozen=True)
class Release:
    id: str                 # identifiant chez la source (infohash, identifiant d'élément…)
    provider: str           # Provider.key
    title: str              # nom brut de la release
    name: str               # titre lisible
    original_title: str
    year: str
    kind: str               # "movie" | "tv"
    season: str             # « S03 », « S03E05 » ou vide
    resolution: str         # « 2160p », « 1080p », « 720p » ou « SD »
    langs: tuple[str, ...]
    source: str             # « WEB-DL », « BluRay »… ou « Autre »
    hdr: tuple[str, ...]
    codec: str
    size: int               # octets
    seeders: int | None     # None si la source ne le donne pas
    date: str               # ISO 8601
    url: str                # fiche sur le site
    freeleech: bool = False # téléchargement non décompté du ratio

    def has_lang(self, lang: str) -> bool:
        # VF2 = VFF + VFQ
        return lang in self.langs or (lang in ("VFF", "VFQ") and "VF2" in self.langs)


@dataclass(frozen=True)
class Query:
    text: str = ""
    kind: str = "all"
    langs: tuple[str, ...] = ()
    resolutions: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    max_gb: int = 0
    sort: str = "seeders"

    def __post_init__(self):
        if self.kind not in KINDS or self.sort not in SORTS or self.max_gb < 0:
            raise ValueError("Paramètre de recherche invalide")

    def without(self, filters: frozenset[str]) -> "Query":
        """Copie sans les filtres donnés (remis à leur valeur par défaut)."""
        defaults = {f.name: f.default for f in fields(self)}
        return replace(self, **{name: defaults[name] for name in filters})

    def accepts(self, release: Release, filters: frozenset[str]) -> bool:
        """La release passe-t-elle les filtres donnés ?"""
        checks = {
            "text": lambda: all(word in release.title.lower() for word in self.text.lower().split()),
            "kind": lambda: self.kind in ("all", release.kind),
            "langs": lambda: not self.langs or any(release.has_lang(lang) for lang in self.langs),
            "resolutions": lambda: not self.resolutions or release.resolution in self.resolutions,
            "sources": lambda: not self.sources or release.source in self.sources,
            "max_gb": lambda: not self.max_gb or release.size <= self.max_gb * 1e9,
        }
        return all(checks[name]() for name in filters)


@dataclass(frozen=True)
class Account:
    """Statistiques du compte sur le site."""
    username: str
    uploaded: int       # octets envoyés, bonus compris
    downloaded: int     # octets reçus
    bonus: int = 0      # part de `uploaded` offerte par le site

    @property
    def ratio(self) -> float | None:
        return round(self.uploaded / self.downloaded, 2) if self.downloaded else None


@dataclass
class ProviderPage:
    releases: list[Release]
    last: bool                  # plus aucune page après celle-ci
    total: int | None = None    # nombre de résultats annoncé par la source, si elle le donne


@dataclass
class Batch:
    """Lot de résultats renvoyé à la page."""
    releases: list[Release] = field(default_factory=list)
    more: bool = False          # d'autres résultats peuvent suivre
    total: int | None = None    # total annoncé par la source
    exact: bool = True          # False si des filtres appliqués ici réduisent ce total
    limited: bool = False       # la source a freiné avant que le lot soit complet
