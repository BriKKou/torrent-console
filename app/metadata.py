"""Fiche d'un titre via TMDb (jaquette, note, résumé, genres, durée, IMDb), quelle que soit la source du torrent."""
import threading
import urllib.parse
from dataclasses import asdict, dataclass

from httpclient import get_json


@dataclass(frozen=True)
class Metadata:
    tmdb_id: int = 0
    poster: str = ""
    rating: float | None = None     # note TMDb, si assez de votes
    imdb_id: str = ""
    overview: str = ""              # résumé en français
    genres: tuple[str, ...] = ()
    runtime: int = 0                # minutes (durée d'un épisode pour une série)


class Tmdb:
    API_URL = "https://api.themoviedb.org/3"
    POSTER_URL = "https://image.tmdb.org/t/p/w342"
    LANGUAGE = "fr-FR"              # affiche française si elle existe
    MIN_VOTES = 20                  # en dessous, la note n'est pas fiable
    MAX_CACHE = 5000

    def __init__(self, token: str = ""):
        self._headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._cache: dict[tuple, dict] = {}
        self._lock = threading.Lock()

    def lookup(self, kind: str, title: str, original_title: str = "", year: str = "") -> dict:
        if not self._headers:
            return asdict(Metadata())  # pas de jeton TMDb : pas de fiches
        key = (kind, title, original_title, year)
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        media = "tv" if kind == "tv" else "movie"
        match = self._find(media, title, original_title, year)
        result = asdict(self._details(media, match["id"]) if match else Metadata())
        with self._lock:
            if len(self._cache) >= self.MAX_CACHE:
                self._cache.clear()
            self._cache[key] = result
        return result

    def _find(self, media: str, title: str, original_title: str, year: str) -> dict | None:
        # Titre original d'abord (le plus fiable), puis titre français, puis sans l'année
        attempts = dict.fromkeys([(original_title, year), (title, year), (original_title or title, "")])
        year_param = "first_air_date_year" if media == "tv" else "year"
        for text, with_year in attempts:
            if not text:
                continue
            params = {"query": text, **({year_param: with_year} if with_year else {})}
            results = self._get(f"/search/{media}", params)["results"]
            if results:
                return results[0]
        return None

    def _details(self, media: str, tmdb_id: int) -> Metadata:
        data = self._get(f"/{media}/{tmdb_id}", {"append_to_response": "external_ids"})
        return Metadata(
            tmdb_id=tmdb_id,
            poster=f"{self.POSTER_URL}{data['poster_path']}" if data.get("poster_path") else "",
            rating=round(data["vote_average"], 1) if data.get("vote_count", 0) >= self.MIN_VOTES else None,
            imdb_id=(data.get("external_ids") or {}).get("imdb_id") or "",
            overview=data.get("overview") or "",
            genres=tuple(genre["name"] for genre in data.get("genres") or []),
            runtime=data.get("runtime") or next(iter(data.get("episode_run_time") or []), 0),
        )

    def _get(self, path: str, params: dict) -> dict:
        query = urllib.parse.urlencode({**params, "language": self.LANGUAGE})
        return get_json(f"{self.API_URL}{path}?{query}", self._headers)
