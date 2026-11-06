"""Contrat commun aux sources de torrents."""
from abc import ABC, abstractmethod

from models import Account, ProviderPage, Query

OPTIONAL_FEATURES = ("account", "video_bitrate")


class Provider(ABC):
    key: str                        # identifiant court, nom du module (« internet_archive »)
    label: str                      # nom affiché
    native_filters: frozenset[str]  # filtres de Query que le site applique lui-même (voir models.FILTERS)

    @abstractmethod
    def search(self, query: Query, page: int) -> ProviderPage:
        """Page `page` (à partir de 1), déjà triée selon `query.sort` et filtrée selon `native_filters`."""

    @abstractmethod
    def download(self, release_id: str) -> bytes:
        """Contenu du .torrent de la release, ou son lien magnet (b"magnet:?…")."""

    # Facultatif : la page n'affiche ces informations que pour les sources qui les fournissent

    def account(self) -> Account | None:
        """Statistiques du compte (envoyé, reçu), si le site les fournit."""
        return None

    def video_bitrate(self, release_id: str) -> int | None:
        """Débit vidéo en kb/s, s'il est connu."""
        return None

    def features(self) -> list[str]:
        """Méthodes facultatives que la source fournit vraiment."""
        return [name for name in OPTIONAL_FEATURES if getattr(type(self), name) is not getattr(Provider, name)]
