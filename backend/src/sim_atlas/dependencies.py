from sim_atlas.storage_interface import StorageInterface


class _StorageHolder:
    instance: StorageInterface | None = None


def set_storage(storage: StorageInterface | None) -> None:
    _StorageHolder.instance = storage


def get_storage() -> StorageInterface:
    assert _StorageHolder.instance is not None, "Storage has not been initialised"
    return _StorageHolder.instance
