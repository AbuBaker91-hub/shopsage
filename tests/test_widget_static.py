"""The widget is served as JavaScript and reads its endpoint from the
data-endpoint attribute; the demo storefront mounts it with one script tag."""

from fastapi.testclient import TestClient

from app.main import create_shopsage_app


def _client() -> TestClient:
    # static routes touch neither the DB nor the router
    return TestClient(create_shopsage_app(None, None, None))


def test_widget_served_as_javascript():
    res = _client().get("/static/widget.js")
    assert res.status_code == 200
    assert "javascript" in res.headers["content-type"]
    assert "data-endpoint" in res.text
    assert "shopsage-" in res.text  # scoped style classes


def test_demo_page_served_at_root():
    res = _client().get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert '<script src="/static/widget.js" data-endpoint="/chat"></script>' in res.text
