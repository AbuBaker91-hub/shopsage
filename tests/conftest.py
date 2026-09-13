from pathlib import Path

import pytest
from aiforge_core import testing
from aiforge_core.testing import *  # noqa: F401,F403
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "samples" / "catalog.json"


@pytest.fixture
def prompts_dir():
    return str(ROOT / "prompts")


@pytest.fixture
def project_migrations_dir():
    return str(ROOT / "migrations")


@pytest.fixture
def app_client(test_db, mock_provider, prompts_dir, stub_embedder):  # noqa: F811
    """TestClient wired to a fresh test DB (catalog loaded), MockProvider router
    and StubEmbedder. No network anywhere."""
    from app.catalog import load_catalog
    from app.main import create_shopsage_app

    load_catalog(test_db, CATALOG, stub_embedder)
    app = create_shopsage_app(
        test_db, testing.make_router(mock_provider, prompts_dir), stub_embedder
    )
    return TestClient(app)
