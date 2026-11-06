"""Surveillances de recherches : une notification quand une nouvelle release correspond, sans rien télécharger."""
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field, replace

from models import Query
from notifier import Notifier
from search import SearchService
from storage import read_json, write_json

MAX_SEEN = 1000         # releases déjà vues, gardées par surveillance
MAX_LISTED = 3          # titres cités dans une notification groupée


@dataclass
class Watch:
    id: str
    label: str
    provider: str
    query: Query
    created: float
    checked: float = 0.0
    seen: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {**asdict(self), "query": asdict(self.query)}

    @classmethod
    def from_json(cls, data: dict) -> "Watch":
        query = {name: tuple(value) if isinstance(value, list) else value for name, value in data["query"].items()}
        return cls(**{**data, "query": Query(**query)})

    def summary(self) -> dict:
        """Ce que la page affiche (sans la liste des releases déjà vues)."""
        return {"id": self.id, "label": self.label, "provider": self.provider, "query": asdict(self.query),
                "created": self.created, "checked": self.checked}


class WatchService:
    def __init__(self, search: SearchService, notifier: Notifier, path: str, page_url: str = ""):
        self._search = search
        self._notifier = notifier
        self._path = path
        self._page_url = page_url
        self._lock = threading.Lock()
        self._watches = self._load()

    def all(self) -> list[Watch]:
        with self._lock:
            return list(self._watches)

    def add(self, label: str, provider: str, query: Query) -> Watch:
        query = replace(query, sort="date")
        # Ce qui existe déjà au moment de l'ajout ne déclenche pas de notification
        seen = [release.id for release in self._latest(provider, query)]
        now = time.time()
        watch = Watch(id=uuid.uuid4().hex[:12], label=label.strip() or "Surveillance", provider=provider,
                      query=query, created=now, checked=now, seen=seen)
        with self._lock:
            self._watches.append(watch)
            self._save()
        return watch

    def remove(self, watch_id: str) -> None:
        with self._lock:
            self._watches = [w for w in self._watches if w.id != watch_id]
            self._save()

    def check_all(self) -> None:
        for watch in self.all():
            new = [r for r in self._latest(watch.provider, watch.query) if r.id not in watch.seen]
            if new:
                self._notify(watch, new)
            with self._lock:
                watch.seen = ([r.id for r in new] + watch.seen)[:MAX_SEEN]
                watch.checked = time.time()
                self._save()

    def _latest(self, provider: str, query: Query):
        return self._search.search(provider, query, refresh=True).releases

    def _notify(self, watch: Watch, releases) -> None:
        if len(releases) == 1:
            title = f"Nouvelle release : {watch.label}"
        else:
            title = f"{len(releases)} nouvelles releases : {watch.label}"
        lines = [r.title for r in releases[:MAX_LISTED]]
        if len(releases) > MAX_LISTED:
            lines.append(f"… et {len(releases) - MAX_LISTED} autres")
        self._notifier.send(title, "\n".join(lines), self._page_url)

    def _load(self) -> list[Watch]:
        return [Watch.from_json(item) for item in read_json(self._path, [])]

    def _save(self) -> None:
        write_json(self._path, [watch.to_json() for watch in self._watches])
