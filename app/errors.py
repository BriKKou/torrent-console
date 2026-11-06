"""Erreurs remontées telles quelles à l'utilisateur (messages en français, sans URL ni clé)."""


class RemoteError(Exception):
    """Un service distant (site de torrents, TMDb, Transmission) a échoué."""


class RateLimited(RemoteError):
    """Le site limite le nombre d'appels : réessayer un peu plus tard."""
