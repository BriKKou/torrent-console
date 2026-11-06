"""Client minimal de l'API RPC de Transmission."""
import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from errors import RemoteError

# Codes d'état de Transmission ramenés à quelques états lisibles
STATES = {0: "paused", 1: "queued", 2: "checking", 3: "queued", 4: "downloading", 5: "queued", 6: "seeding"}
FIELDS = ["id", "hashString", "name", "status", "percentDone", "rateDownload", "rateUpload", "eta",
          "uploadRatio", "sizeWhenDone", "error", "errorString", "addedDate", "doneDate"]


@dataclass(frozen=True)
class Torrent:
    id: int
    hash: str
    name: str
    state: str          # downloading | seeding | paused | queued | checking
    progress: float     # de 0 à 1
    size: int           # octets
    down_rate: int      # octets/s
    up_rate: int
    eta: int            # secondes, négatif si inconnu
    ratio: float
    error: str
    added: int          # horodatage Unix
    done: int           # horodatage Unix, 0 tant que ce n'est pas fini

    @property
    def complete(self) -> bool:
        return self.progress >= 1


class Transmission:
    def __init__(self, url: str, user: str, password: str):
        self._url = url
        self._auth = "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()
        self._session = ""

    def add(self, torrent: bytes) -> tuple[str, bool]:
        """Ajoute un .torrent (ou un lien magnet). Renvoie son nom et s'il était déjà présent."""
        if torrent.startswith(b"magnet:"):
            arguments = {"filename": torrent.decode()}
        else:
            arguments = {"metainfo": base64.b64encode(torrent).decode()}
        result = self._call("torrent-add", arguments)
        duplicate = "torrent-duplicate" in result
        return result["torrent-duplicate" if duplicate else "torrent-added"]["name"], duplicate

    def torrents(self) -> list[Torrent]:
        return [
            Torrent(
                id=t["id"], hash=t["hashString"], name=t["name"], state=STATES.get(t["status"], "paused"),
                progress=t["percentDone"], size=t["sizeWhenDone"], down_rate=t["rateDownload"],
                up_rate=t["rateUpload"], eta=t["eta"], ratio=max(t["uploadRatio"], 0.0),
                error=t["errorString"] if t["error"] else "", added=t["addedDate"], done=t["doneDate"],
            )
            for t in self._call("torrent-get", {"fields": FIELDS})["torrents"]
        ]

    def start(self, ids: list[int]) -> None:
        self._call("torrent-start", {"ids": ids})

    def stop(self, ids: list[int]) -> None:
        self._call("torrent-stop", {"ids": ids})

    def remove(self, ids: list[int], delete_data: bool = False) -> None:
        self._call("torrent-remove", {"ids": ids, "delete-local-data": delete_data})

    def _call(self, method: str, arguments: dict) -> dict:
        body = json.dumps({"method": method, "arguments": arguments}).encode()
        for _ in range(2):  # le 1er appel peut servir à obtenir l'identifiant de session (409)
            request = urllib.request.Request(self._url, data=body, headers={
                "Authorization": self._auth, "X-Transmission-Session-Id": self._session})
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    reply = json.load(response)
            except urllib.error.HTTPError as e:
                if e.code == 409:
                    self._session = e.headers["X-Transmission-Session-Id"]
                    continue
                raise RemoteError(f"Transmission : erreur HTTP {e.code}") from e
            except urllib.error.URLError as e:
                raise RemoteError("Transmission injoignable") from e
            if reply.get("result") != "success":
                raise RemoteError(f"Transmission : {reply.get('result')}")
            return reply["arguments"]
        raise RemoteError("Transmission refuse la session")
