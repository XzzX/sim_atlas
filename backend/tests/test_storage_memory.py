"""Contract tests for InMemoryStorage."""

from __future__ import annotations

import pytest

from app.storage_memory import InMemoryStorage

from .test_storage_interface import StorageContractTests


class TestInMemoryStorage(StorageContractTests):
    """Run the full StorageInterface contract against InMemoryStorage."""

    @pytest.fixture
    def storage(self) -> InMemoryStorage:
        s = InMemoryStorage(start_clean=True)
        return s
