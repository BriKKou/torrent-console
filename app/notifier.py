"""Notifications sur le téléphone, via un webhook Home Assistant."""
import logging

from errors import RemoteError
from httpclient import post_json

log = logging.getLogger(__name__)


class Notifier:
    def __init__(self, webhook_url: str = ""):
        self._webhook_url = webhook_url

    def send(self, title: str, message: str, url: str = "") -> None:
        """Une notification perdue ne doit rien bloquer : l'échec est seulement journalisé."""
        if not self._webhook_url:
            return
        try:
            post_json(self._webhook_url, {"title": title, "message": message, "url": url})
        except RemoteError as e:
            log.warning("Notification non envoyée : %s", e)
