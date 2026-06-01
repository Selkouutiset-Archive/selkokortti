from pathlib import Path

import pytest

FIXTURE_DATA = Path(__file__).parent / "fixtures" / "data"


@pytest.fixture
def data_dir() -> Path:
    return FIXTURE_DATA
