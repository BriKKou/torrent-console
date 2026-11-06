"""Tâches de fond : fin des téléchargements, surveillances de recherches."""
import logging
import threading
import time

from notifier import Notifier
from transmission import Transmission

log = logging.getLogger(__name__)


def run_every(interval_s: float, task, name: str) -> None:
    """Lance `task` toutes les `interval_s` secondes, dans un fil d'exécution à part."""
    def loop():
        while True:
            try:
                task()
            except Exception:
                log.exception("Tâche « %s » en échec", name)
            time.sleep(interval_s)
    threading.Thread(target=loop, name=name, daemon=True).start()


class DownloadWatcher:
    """Prévient quand un torrent de Transmission vient de se terminer."""

    def __init__(self, transmission: Transmission, notifier: Notifier, page_url: str = ""):
        self._transmission = transmission
        self._notifier = notifier
        self._page_url = page_url
        self._complete: set[str] | None = None  # inconnu avant le 1er passage : rien à notifier au démarrage

    def check(self) -> None:
        torrents = self._transmission.torrents()
        if self._complete is not None:
            for torrent in torrents:
                if torrent.complete and torrent.hash not in self._complete:
                    self._notifier.send("Téléchargement terminé", torrent.name, self._page_url)
        self._complete = {torrent.hash for torrent in torrents if torrent.complete}
