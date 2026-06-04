#!/usr/bin/env python3
"""Probe Kivo API endpoints before adding them to sources.json."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from logging_utils import get_logger, setup_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "sources.json"
LOGGER = get_logger("probe")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_url(base_url: str, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    if path == "/":
        return base_url.rstrip("/") + "/"
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def candidate_paths(config: dict[str, Any], extra_paths: list[str]) -> list[str]:
    if extra_paths:
        return extra_paths
    paths = []
    for resource in config.get("resources", []):
        paths.append(resource["path"])
        if resource.get("mode") == "paginated":
            paths.append(resource["path"] + ("&page=2" if "?" in resource["path"] else "?page=2"))
        if resource.get("detail_path"):
            paths.append(resource["detail_path"].format(id=1))
    return paths


def probe(url: str, user_agent: str, timeout: float) -> tuple[int, str, str]:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(300)
            return response.status, response.headers.get("Content-Type", ""), body.decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read(300)
        return exc.code, exc.headers.get("Content-Type", ""), body.decode("utf-8", "replace")


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="Probe Kivo API endpoints.")
    parser.add_argument("paths", nargs="*", help="Endpoint paths or full URLs to probe.")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="Path to sources.json.")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    config = load_json(args.sources)
    for path in candidate_paths(config, args.paths):
        url = build_url(config["base_url"], path)
        try:
            status, content_type, snippet = probe(url, config.get("user_agent", "StuArchiveProbe/0.1"), config.get("timeout_seconds", 15))
        except Exception as exc:
            LOGGER.error("%s\tERR\t%s: %s", path, type(exc).__name__, exc)
            continue
        snippet = snippet.replace("\n", " ")[:160]
        LOGGER.info("%s\t%s\t%s\t%s", path, status, content_type, snippet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
