#!/usr/bin/env python
"""Validate implemented routes and handler signatures against ARCHITECTURE.json.

The guardrail behind "architecture as code":

1. every implemented route must exist in the JSON;
2. every JSON route must exist in the app unless it is marked ``planned``;
3. route methods must match;
4. path variables and declared parameters must be accepted by the handler.

Supports both Flask (``url_map``) and FastAPI / Starlette (``routes``), because
the architecture skeleton is shared by projects on either stack.

Usage::

    # Flask project (default: import api_server, use api_server.app)
    python scripts/validate_arch.py

    # FastAPI project living in another directory
    python scripts/validate_arch.py \
        --arch ../contract/ARCHITECTURE.json \
        --app api:app --root ../app --ignore /
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IGNORED_METHODS = {"HEAD", "OPTIONS"}
# Framework-managed routes that are not part of the application contract.
IGNORED_ROUTE_NAMES = {
    "openapi",
    "swagger_ui_html",
    "swagger_ui_oauth2_redirect",
    "swagger_ui_oauth2_redirect_html",
    "swagger_ui_redirect",
    "redoc",
    "redoc_html",
}
# Belt and braces: names vary across FastAPI versions, paths do not.
DOCS_PATHS = {
    "/openapi.json",
    "/openapi.yaml",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}

# Matches both Flask "<int:item_id>" / "<item_id>" and FastAPI "{item_id}".
_PARAM = re.compile(r"<(?:(?P<conv>[^:<>]+):)?(?P<name>[^<>]+)>|\{(?P<fname>[^{}]+)\}")


def canonical_rule(rule: str) -> str:
    """Normalise a route rule so Flask and FastAPI syntax compare equal."""
    return _PARAM.sub(lambda m: "{" + (m.group("name") or m.group("fname")) + "}", rule)


def route_key(rule: str, method: str) -> tuple[str, str]:
    return canonical_rule(rule), method.upper()


def methods_of(endpoint: dict[str, Any]) -> set[str]:
    return {m.upper() for m in endpoint.get("methods") or ["GET"]} - IGNORED_METHODS


def path_params(rule: str) -> set[str]:
    return {
        m.group("name") or m.group("fname") for m in _PARAM.finditer(rule)
    }


def _accepts(func: Any, name: str) -> bool:
    if func is None:
        return True
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return True
    if name in signature.parameters:
        return True
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())


def detect_framework(app: Any) -> str:
    if hasattr(app, "url_map"):
        return "flask"
    if hasattr(app, "routes"):
        return "fastapi"
    raise TypeError(
        "unrecognised application object: expected a Flask app (url_map) "
        "or a FastAPI/Starlette app (routes)"
    )


def collect_routes(app: Any) -> dict[tuple[str, str], Any]:
    """Map (canonical_rule, METHOD) -> handler for every implemented route."""
    routes: dict[tuple[str, str], Any] = {}
    framework = detect_framework(app)

    if framework == "flask":
        view_functions = getattr(app, "view_functions", {})
        for rule in app.url_map.iter_rules():
            if rule.endpoint == "static":
                continue
            handler = view_functions.get(rule.endpoint)
            for method in rule.methods - IGNORED_METHODS:
                routes[route_key(rule.rule, method)] = handler
        return routes

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue  # Mount / WebSocket / docs helpers
        if path in DOCS_PATHS:
            continue
        if getattr(route, "name", "") in IGNORED_ROUTE_NAMES:
            continue
        handler = getattr(route, "endpoint", None)
        for method in set(methods) - IGNORED_METHODS:
            routes[route_key(path, method)] = handler
    return routes


def load_architecture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    endpoints = data.get("api", {}).get("endpoints")
    if not isinstance(endpoints, list):
        raise ValueError("ARCHITECTURE.json: api.endpoints must be a list")
    return data


def load_app(spec: str, root: str | None = None) -> Any:
    if root:
        sys.path.insert(0, str(Path(root).resolve()))
    module_name, _, attribute = spec.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, attribute or "app")


def validate(
    arch: dict[str, Any], app: Any, ignore: set[str] | None = None
) -> dict[str, Any]:
    ignore = {canonical_rule(p) for p in (ignore or set())}
    errors: list[str] = []
    warnings: list[str] = []

    documented: dict[tuple[str, str], dict[str, Any]] = {}
    for endpoint in arch.get("api", {}).get("endpoints", []):
        rule = endpoint.get("rule")
        if not rule:
            errors.append("endpoint without rule")
            continue
        if endpoint.get("status") == "planned":
            continue
        for method in methods_of(endpoint):
            key = route_key(rule, method)
            if key in documented:
                errors.append(f"duplicate endpoint in JSON: {method} {rule}")
            documented[key] = endpoint

    implemented = collect_routes(app)

    for key in sorted(implemented.keys() - documented.keys()):
        if key[0] in ignore:
            continue
        errors.append(f"wild route not in ARCHITECTURE.json: {key[1]} {key[0]}")
    for key in sorted(documented.keys() - implemented.keys()):
        errors.append(f"documented route missing from app: {key[1]} {key[0]}")

    for key, endpoint in documented.items():
        handler = implemented.get(key)
        rule = endpoint.get("rule", "")
        for param in path_params(rule):
            if not _accepts(handler, param):
                errors.append(
                    f"handler {endpoint.get('endpoint')} does not accept path param '{param}'"
                )
        for param in endpoint.get("parameters") or []:
            name = param if isinstance(param, str) else param.get("name")
            if name and not _accepts(handler, name):
                errors.append(
                    f"handler {endpoint.get('endpoint')} does not accept parameter '{name}'"
                )

    if not errors:
        for endpoint in arch.get("api", {}).get("endpoints", []):
            if endpoint.get("status") == "planned":
                warnings.append(f"planned endpoint not implemented: {endpoint.get('rule')}")

    return {
        "ok": not errors,
        "framework": detect_framework(app),
        "json_routes": len(documented),
        "app_routes": len(implemented),
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="validate ARCHITECTURE.json against an app")
    parser.add_argument("--arch", default=str(ROOT / "ARCHITECTURE.json"))
    parser.add_argument("--app", default="api_server:app", help="module:attribute")
    parser.add_argument("--root", default=None, help="extra sys.path entry for --app")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="route path that is intentionally outside the contract (repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="print machine-readable result")
    args = parser.parse_args(argv)

    arch = load_architecture(Path(args.arch))
    app = load_app(args.app, args.root)
    result = validate(arch, app, set(args.ignore))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"framework={result['framework']} "
            f"json_routes={result['json_routes']} app_routes={result['app_routes']}"
        )
        for item in result["errors"]:
            print(f"ERROR {item}")
        for item in result["warnings"]:
            print(f"WARN  {item}")
        print("OK" if result["ok"] else "FAILED")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
