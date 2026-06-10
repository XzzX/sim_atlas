"""Contract tests for FileSystemStorage."""

from __future__ import annotations

import pytest

from sim_atlas.file_system_storage import FileSystemStorage

from .test_storage_interface import StorageContractTests


class TestFileSystemStorage(StorageContractTests):
    """Run the full StorageInterface contract against FileSystemStorage."""

    @pytest.fixture
    def storage(self) -> FileSystemStorage:
        s = FileSystemStorage(filename=None)
        return s
