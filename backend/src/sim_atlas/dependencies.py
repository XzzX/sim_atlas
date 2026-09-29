from sim_atlas.catalog import Catalog
from sim_atlas.storage.storage_interface import StorageInterface


class _StorageHolder:
    instance: StorageInterface | None = None
    catalog: Catalog | None = None


def set_storage(storage: StorageInterface | None) -> None:
    _StorageHolder.instance = storage
    _StorageHolder.catalog = Catalog(storage) if storage is not None else None


def get_storage() -> StorageInterface:
    assert _StorageHolder.instance is not None, "Storage has not been initialised"
    return _StorageHolder.instance


def get_catalog() -> Catalog:
    assert _StorageHolder.catalog is not None, "Storage has not been initialised"
    return _StorageHolder.catalog
