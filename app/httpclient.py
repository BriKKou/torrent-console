"""Appels HTTP sortants, avec la bibliothèque standard uniquement."""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from errors import RateLimited, RemoteError

USER_AGENT = "Mozilla/5.0 (torrent-console)"
RETRIES = 2                                 # nouvelles tentatives sur erreur passagère
RETRY_DELAY_S = 1.0
TRANSIENT_CODES = frozenset({500, 502, 503, 504})


def request(url: str, *, data: bytes | None = None, headers: dict | None = None, timeout: int = 30) -> bytes:
    host = urllib.parse.urlsplit(url).hostname
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in range(RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RateLimited(f"{host} limite le nombre de requêtes, réessaie dans une minute") from e
            if e.code not in TRANSIENT_CODES or attempt == RETRIES:
                raise RemoteError(f"{host} : erreur HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == RETRIES:
                raise RemoteError(f"{host} injoignable") from e
        time.sleep(RETRY_DELAY_S * (attempt + 1))
    raise AssertionError("inatteignable")


def get(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
    return request(url, headers=headers, timeout=timeout)


def get_json(url: str, headers: dict | None = None, timeout: int = 30):
    return json.loads(get(url, {"Accept": "application/json", **(headers or {})}, timeout))


def post_json(url: str, payload: dict, timeout: int = 15) -> bytes:
    return request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, timeout=timeout)


class Throttle:
    """Espace les appels vers un même site."""

    def __init__(self, interval_s: float):
        self._interval_s = interval_s
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            time.sleep(max(0.0, self._next - time.monotonic()))
            self._next = time.monotonic() + self._interval_s
