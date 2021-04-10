import shutil
from pathlib import Path

import pytest


@pytest.fixture()
def test_data_dir():
    return Path(__file__).parent / "test-export"


@pytest.fixture(autouse=True)
def cleanup_test_data(test_data_dir):
    yield
    shutil.rmtree(test_data_dir, ignore_errors=True)
