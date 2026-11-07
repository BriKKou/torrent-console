"""Serveur de la page Recherche torrent : fichiers statiques + API JSON.

    GET  /api/providers         sources configurées et ce qu'elles fournissent en plus (compte, débit vidéo)
    GET  /api/search            lot de résultats (provider, q, type, langs, res, sources, max, sort, after, refresh)
    GET  /api/versions          toutes les versions d'un titre (provider, kind, title = nom de fichier, name, year, season)
    GET  /api/meta              jaquette, note et IMDb d'un titre (kind, title, original, year)
    GET  /api/account           statistiques du compte sur la source, {} si elle ne les fournit pas
    GET  /api/bitrate           débit vidéo d'une release (provider, id), null s'il est inconnu
    GET  /api/torrents          torrents de Transmission
    GET  /api/watches           surveillances de recherches
    POST /api/add               envoie une release à Transmission ({"provider", "id"})
    POST /api/torrents/action   {"action": "start" | "stop" | "remove" | "delete", "ids": [...]}
    POST /api/watches           {"label", "provider", "params": paramètres de /api/search}
    POST /api/watches/remove    {"id"}
"""
import json
import logging
import os
import urllib.parse
from dataclasses import asdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from auth import BasicAuth
from background import DownloadWatcher, run_every
from bitrates import BitrateCache
from errors import RateLimited, RemoteError
from metadata import Tmdb
from models import Query
from notifier import Notifier
from providers import load as load_providers
from search import SearchService
from transmission import Transmission
from watches import WatchService

CONFIG_PATH = os.environ.get("CONFIG_PATH", "/config.json")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PORT = 8282
DOWNLOADS_CHECK_S = 60
WATCHES_CHECK_S = 30 * 60

log = logging.getLogger(__name__)


class App:
    """Les services, assemblés à partir de la configuration."""

    def __init__(self, config: dict):
        page_url = config.get("public_url", "")
        data_dir = config.get("data_dir", "/data")
        self.providers = load_providers(config.get("providers") or {})
        if not self.providers:
            raise ValueError("Aucune source active : voir « providers » dans config.json")
        self.search = SearchService(self.providers)
        self.bitrates = BitrateCache(os.path.join(data_dir, "bitrates.json"))
        self.tmdb = Tmdb((config.get("tmdb") or {}).get("token", ""))
        self.transmission = Transmission(**config["transmission"])
        self.auth = BasicAuth(**config.get("auth", {}))
        notifier = Notifier(config.get("notifications", {}).get("webhook_url", ""))
        self.watches = WatchService(self.search, notifier, os.path.join(data_dir, "watches.json"), page_url)
        self.downloads = DownloadWatcher(self.transmission, notifier, page_url)

    def start_background_tasks(self) -> None:
        run_every(DOWNLOADS_CHECK_S, self.downloads.check, "téléchargements")
        run_every(WATCHES_CHECK_S, self.watches.check_all, "surveillances")

    def provider_key(self, value) -> str:
        """Source demandée, ou la première de la configuration."""
        return str(value or self.providers[0].key)

    # GET

    def list_providers(self, params: dict) -> dict:
        return {"providers": [{"key": p.key, "label": p.label, "features": p.features()} for p in self.providers]}

    def search_releases(self, params: dict) -> dict:
        batch = self.search.search(self.provider_key(params.get("provider")), Query.from_params(params),
                                   offset=int(params.get("after") or 0), refresh=params.get("refresh") == "1")
        return {**asdict(batch), "releases": [asdict(r) for r in batch.releases]}

    def versions(self, params: dict) -> dict:
        releases = self.search.versions(
            self.provider_key(params.get("provider")), params.get("kind") or "all", params.get("title", ""),
            params.get("name", ""), params.get("year", ""), params.get("season", ""))
        return {"releases": [asdict(r) for r in releases]}

    def metadata(self, params: dict) -> dict:
        return self.tmdb.lookup(params.get("kind", ""), params.get("title", ""),
                                params.get("original", ""), params.get("year", ""))

    def account(self, params: dict) -> dict:
        account = self.search.provider(self.provider_key(params.get("provider"))).account()
        return {**asdict(account), "ratio": account.ratio} if account else {}

    def bitrate(self, params: dict) -> dict:
        provider = self.search.provider(self.provider_key(params.get("provider")))
        return {"kbps": self.bitrates.get(provider, params.get("id", ""))}

    def torrents(self, params: dict) -> dict:
        return {"torrents": [asdict(t) for t in self.transmission.torrents()]}

    def list_watches(self, params: dict) -> dict:
        return {"watches": [watch.summary() for watch in self.watches.all()]}

    # POST

    def add(self, body: dict) -> dict:
        torrent = self.search.provider(str(body.get("provider"))).download(str(body.get("id")))
        name, duplicate = self.transmission.add(torrent)
        return {"name": name, "duplicate": duplicate}

    def torrent_action(self, body: dict) -> dict:
        ids = [int(i) for i in body.get("ids", [])]
        actions = {
            "start": lambda: self.transmission.start(ids),
            "stop": lambda: self.transmission.stop(ids),
            "remove": lambda: self.transmission.remove(ids, delete_data=False),
            "delete": lambda: self.transmission.remove(ids, delete_data=True),
        }
        if not ids or body.get("action") not in actions:
            raise ValueError("Action invalide")
        actions[body["action"]]()
        return {}

    def add_watch(self, body: dict) -> dict:
        provider = self.provider_key(body.get("provider"))
        self.search.provider(provider)  # source inconnue : erreur avant tout appel
        params = {name: str(value) for name, value in (body.get("params") or {}).items()}
        watch = self.watches.add(str(body.get("label", "")), provider, Query.from_params(params))
        return watch.summary()

    def remove_watch(self, body: dict) -> dict:
        self.watches.remove(str(body.get("id")))
        return {}


class Handler(SimpleHTTPRequestHandler):
    app: App  # renseigné au démarrage

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        if not self._authorized():
            return
        url = urllib.parse.urlsplit(self.path)
        route = {
            "/api/providers": self.app.list_providers,
            "/api/search": self.app.search_releases,
            "/api/versions": self.app.versions,
            "/api/meta": self.app.metadata,
            "/api/account": self.app.account,
            "/api/bitrate": self.app.bitrate,
            "/api/torrents": self.app.torrents,
            "/api/watches": self.app.list_watches,
        }.get(url.path)
        if route is None:
            return super().do_GET()
        params = {name: values[0].strip() for name, values in urllib.parse.parse_qs(url.query).items()}
        self._answer(route, params)

    def do_POST(self):
        if not self._authorized():
            return
        route = {
            "/api/add": self.app.add,
            "/api/torrents/action": self.app.torrent_action,
            "/api/watches": self.app.add_watch,
            "/api/watches/remove": self.app.remove_watch,
        }.get(self.path)
        # JSON obligatoire : une page d'un autre site ne peut pas l'envoyer sans pré-vérification CORS
        if route is None or not self.headers.get("Content-Type", "").startswith("application/json"):
            return self.send_error(400)
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send_json(400, {"error": "Requête invalide"})
        self._answer(route, body)

    def _authorized(self) -> bool:
        if self.app.auth.allows(self.headers.get("Authorization")):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Recherche torrent", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def _answer(self, route, params) -> None:
        try:
            self._send_json(200, route(params))
        except RateLimited as e:
            self._send_json(429, {"error": str(e)})
        except RemoteError as e:
            self._send_json(502, {"error": str(e)})
        except (ValueError, TypeError) as e:
            self._send_json(400, {"error": str(e) or "Requête invalide"})
        except Exception:
            log.exception("Erreur sur %s", self.path)
            self._send_json(500, {"error": "Erreur interne, voir les journaux du conteneur"})

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        Handler.app = App(json.load(f))
    Handler.app.start_background_tasks()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
