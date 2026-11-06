"""Sources de torrents.

Une source est un module qui définit une sous-classe de Provider dont `key` est le nom du module.
Les sources livrées sont dans ce dossier ; les autres se déposent dans le dossier `plugins/`
du projet (non versionné), lu comme s'il faisait partie de ce paquet.
config.json choisit les sources actives et leurs paramètres : {"providers": {"<clé>": {...}}}.
"""
import importlib
import inspect
from pathlib import Path

from providers.base import Provider

PLUGINS_DIR = Path(__file__).resolve().parents[2] / "plugins"  # /plugins dans le conteneur
__path__.append(str(PLUGINS_DIR))


def load(config: dict[str, dict]) -> list[Provider]:
    """Les sources de la configuration, dans son ordre : la première est celle proposée par défaut."""
    return [provider_class(key)(**(options or {})) for key, options in config.items()]


def provider_class(key: str) -> type[Provider]:
    module_name = f"{__name__}.{key}"
    if not key.isidentifier():
        raise ValueError(f"Nom de source invalide : « {key} »")
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if e.name != module_name:
            raise  # module trouvé, mais l'une de ses dépendances manque
        raise ValueError(f"Source « {key} » introuvable dans app/providers/ et plugins/") from e
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if issubclass(cls, Provider) and getattr(cls, "key", None) == key:
            return cls
    raise ValueError(f"{key}.py ne définit pas de Provider dont la clé est « {key} »")
