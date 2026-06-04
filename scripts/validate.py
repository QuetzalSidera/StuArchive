#!/usr/bin/env python3
"""Validate generated StuArchive JSON files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from logging_utils import get_logger, setup_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"
STATIC_PROTOCOL_RELATIVE_RE = re.compile(r"(?<!:)//static\.kivo\.wiki/")
LOGGER = get_logger("validate")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_protocol_relative_static_urls(value: Any, path: str = "$") -> list[str]:
    if isinstance(value, str):
        if STATIC_PROTOCOL_RELATIVE_RE.search(value):
            return [path]
        return []
    if isinstance(value, list):
        found: list[str] = []
        for index, item in enumerate(value):
            found.extend(find_protocol_relative_static_urls(item, f"{path}[{index}]"))
        return found
    if isinstance(value, dict):
        found = []
        for key, item in value.items():
            found.extend(find_protocol_relative_static_urls(item, f"{path}.{key}"))
        return found
    return []


def validate(data_dir: Path) -> int:
    if not data_dir.exists():
        LOGGER.error("missing data directory: %s", data_dir)
        return 1

    json_files = sorted(data_dir.rglob("*.json"))
    if not json_files:
        LOGGER.error("no JSON files found under %s", data_dir)
        return 1

    errors: list[str] = []
    for path in json_files:
        try:
            payload = load_json(path)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
            continue

        protocol_relative_urls = find_protocol_relative_static_urls(payload)
        if protocol_relative_urls:
            first = protocol_relative_urls[0]
            errors.append(f"{path}: contains protocol-relative static URL at {first}")

    manifest_path = data_dir / "index.json"
    if not manifest_path.exists():
        errors.append("data/index.json is missing")
    else:
        manifest = load_json(manifest_path)
        for resource in manifest.get("resources", []):
            rel_path = resource.get("path")
            if rel_path and not (data_dir / rel_path).exists():
                errors.append(f"manifest resource missing file: {rel_path}")

            if resource.get("type") == "collection" and rel_path:
                index_path = data_dir / rel_path
                if index_path.exists():
                    collection = load_json(index_path)
                    items = collection.get("items", [])
                    if collection.get("total_items") != len(items):
                        errors.append(f"{rel_path}: total_items does not match items length")
                    for page in collection.get("pages", []):
                        page_path = page.get("path")
                        if page_path and not (data_dir / page_path).exists():
                            errors.append(f"{rel_path}: missing page file {page_path}")
                    for detail in collection.get("details", []):
                        detail_path = detail.get("path")
                        if detail_path and not (data_dir / detail_path).exists():
                            errors.append(f"{rel_path}: missing detail file {detail_path}")
                    lookup = collection.get("lookup", {})
                    lookup_path = lookup.get("path")
                    if lookup_path and not (data_dir / lookup_path).exists():
                        errors.append(f"{rel_path}: missing lookup file {lookup_path}")
                    profile_index = collection.get("profile_index", {})
                    profile_index_path = profile_index.get("path")
                    if profile_index_path and not (data_dir / profile_index_path).exists():
                        errors.append(f"{rel_path}: missing profile index file {profile_index_path}")
                    for profile in collection.get("profiles", []):
                        profile_path = profile.get("path")
                        if profile_path and not (data_dir / profile_path).exists():
                            errors.append(f"{rel_path}: missing profile file {profile_path}")

            lookup_path = resource.get("lookup_path")
            if lookup_path and not (data_dir / lookup_path).exists():
                errors.append(f"manifest resource missing lookup file: {lookup_path}")
            profile_index_path = resource.get("profile_index_path")
            if profile_index_path and not (data_dir / profile_index_path).exists():
                errors.append(f"manifest resource missing profile index file: {profile_index_path}")

    if errors:
        for error in errors:
            LOGGER.error("%s", error)
        return 1

    LOGGER.info("OK: %s JSON files", len(json_files))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated StuArchive JSON files.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Generated data directory.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return validate(args.data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
