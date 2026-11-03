"""Tests for validate_arch.py. Uses duck-typed fakes, so no framework install."""

from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_arch as va  # noqa: E402


# -- fakes ----------------------------------------------------------------
class FakeFlaskRule:
    def __init__(self, rule: str, endpoint: str, methods: set[str]) -> None:
        self.rule = rule
        self.endpoint = endpoint
        self.methods = methods | {"HEAD", "OPTIONS"}


class FakeUrlMap:
    def __init__(self, rules) -> None:
        self._rules = rules

    def iter_rules(self):
        return iter(self._rules)


class FakeFlaskApp:
    def __init__(self, routes) -> None:
        self.url_map = FakeUrlMap(routes)
        self.view_functions = {r.endpoint: r.handler for r in routes}


class FakeFlaskRoute:
    def __init__(self, rule, endpoint, handler, methods=("GET",)):
        self.rule = rule
        self.endpoint = endpoint
        self.handler = handler
        self.methods = set(methods) | {"HEAD", "OPTIONS"}


class FakeFastAPIRoute:
    def __init__(self, path, endpoint, methods=("GET",), name=""):
        self.path = path
        self.endpoint = endpoint
        self.methods = set(methods)
        self.name = name


class FakeFastAPIApp:
    def __init__(self, routes) -> None:
        self.routes = routes


def arch(endpoints) -> dict:
    return {"api": {"endpoints": endpoints}}


def handler_ok(item_id=None, **kwargs):
    return None


def handler_missing():
    """Accepts no parameters at all — must fail a path-param check."""
    return None


class ValidateArchTest(unittest.TestCase):
    def test_flask_contract_matches(self) -> None:
        app = FakeFlaskApp([FakeFlaskRoute("/api/x/<int:item_id>", "x.get", handler_ok)])
        result = va.validate(
            arch([{"rule": "/api/x/<int:item_id>", "endpoint": "x.get", "methods": ["GET"], "status": "implemented"}]),
            app,
        )
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["framework"], "flask")

    def test_fastapi_contract_matches_and_syntax_is_canonical(self) -> None:
        app = FakeFastAPIApp([FakeFastAPIRoute("/api/x/{item_id}", handler_ok, name="x_get")])
        # JSON written in Flask syntax must still match a FastAPI route.
        result = va.validate(
            arch([{"rule": "/api/x/<int:item_id>", "endpoint": "x.get", "methods": ["GET"], "status": "implemented"}]),
            app,
        )
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["framework"], "fastapi")

    def test_wild_route_is_an_error(self) -> None:
        app = FakeFastAPIApp(
            [
                FakeFastAPIRoute("/api/x", handler_ok, name="x"),
                FakeFastAPIRoute("/secret", handler_ok, name="secret"),
            ]
        )
        result = va.validate(
            arch([{"rule": "/api/x", "endpoint": "x", "methods": ["GET"], "status": "implemented"}]),
            app,
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("wild route" in e for e in result["errors"]))

    def test_missing_route_is_an_error(self) -> None:
        app = FakeFastAPIApp([])
        result = va.validate(
            arch([{"rule": "/api/x", "endpoint": "x", "methods": ["GET"], "status": "implemented"}]),
            app,
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing from app" in e for e in result["errors"]))

    def test_planned_routes_are_skipped(self) -> None:
        app = FakeFastAPIApp([])
        result = va.validate(
            arch([{"rule": "/api/x", "endpoint": "x", "methods": ["GET"], "status": "planned"}]),
            app,
        )
        self.assertTrue(result["ok"], result["errors"])
        self.assertTrue(result["warnings"])

    def test_handler_must_accept_path_param(self) -> None:
        app = FakeFastAPIApp([FakeFastAPIRoute("/api/x/{item_id}", handler_missing, name="x")])
        result = va.validate(
            arch([{"rule": "/api/x/{item_id}", "endpoint": "x", "methods": ["GET"], "status": "implemented"}]),
            app,
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("path param" in e for e in result["errors"]))

    def test_ignore_suppresses_known_extra_routes(self) -> None:
        app = FakeFastAPIApp([FakeFastAPIRoute("/", handler_ok, name="index")])
        result = va.validate(arch([]), app, {"/"})
        self.assertTrue(result["ok"], result["errors"])

    def test_fastapi_path_converter_is_canonicalised(self) -> None:
        """`{path:path}` and `{path}` are the same contract parameter."""
        app = FakeFastAPIApp(
            [FakeFastAPIRoute("/files/{path:path}", handler_ok, name="get_file")]
        )
        result = va.validate(
            arch([{"rule": "/files/{path}", "endpoint": "get_file", "methods": ["GET"], "status": "implemented"}]),
            app,
        )
        self.assertTrue(result["ok"], result["errors"])

    def test_duplicate_json_endpoint_is_reported(self) -> None:
        app = FakeFastAPIApp([FakeFastAPIRoute("/api/x", handler_ok, name="x")])
        duplicate = {"rule": "/api/x", "endpoint": "x", "methods": ["GET"], "status": "implemented"}
        result = va.validate(arch([duplicate, dict(duplicate)]), app)
        self.assertFalse(result["ok"])
        self.assertTrue(any("duplicate" in e for e in result["errors"]))

    def test_framework_docs_routes_are_skipped(self) -> None:
        """FastAPI's own /docs, /redoc and /openapi.json are not contract routes."""
        app = FakeFastAPIApp(
            [
                FakeFastAPIRoute("/api/x", handler_ok, name="x"),
                FakeFastAPIRoute("/openapi.json", handler_ok, name="openapi"),
                FakeFastAPIRoute("/docs", handler_ok, name="swagger_ui_html"),
                FakeFastAPIRoute("/docs/oauth2-redirect", handler_ok, name="swagger_ui_redirect"),
                FakeFastAPIRoute("/redoc", handler_ok, name="redoc_html"),
            ]
        )
        result = va.validate(
            arch([{"rule": "/api/x", "endpoint": "x", "methods": ["GET"], "status": "implemented"}]),
            app,
        )
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["app_routes"], 1)


if __name__ == "__main__":
    unittest.main()
