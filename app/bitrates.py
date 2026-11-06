"""Débits vidéo, gardés sur disque : les obtenir coûte un appel à la source par torrent."""
import threading

from providers.base import Provider
from storage import read_json, write_json

MAX_ENTRIES = 5000  # au-delà, les moins récemment consultés sont oubliés


class BitrateCache:
    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()
        # Les dictionnaires gardent l'ordre d'insertion : du moins récemment consulté au plus récent
        self._entries: dict[str, int | None] = read_json(path, {})

    def get(self, provider: Provider, release_id: str) -> int | None:
        """Débit en kb/s, None si la source ne le connaît pas (réponse gardée aussi)."""
        key = f"{provider.key}:{release_id}"
        with self._lock:
            if key in self._entries:
                self._entries[key] = self._entries.pop(key)
                return self._entries[key]
        kbps = provider.video_bitrate(release_id)
        with self._lock:
            self._entries[key] = kbps
            for oldest in list(self._entries)[:max(0, len(self._entries) - MAX_ENTRIES)]:
                del self._entries[oldest]
            write_json(self._path, self._entries)
        return kbps
