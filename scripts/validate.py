#!/usr/bin/env python3
"""Validate generated StuArchive JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate(data_dir: Path) -> int:
    if not data_dir.exists():
        print(f"[validate] missing data directory: {data_dir}", file=sys.stderr)
        return 1

    json_files = sorted(data_dir.rglob("*.json"))
    if not json_files:
        print(f"[validate] no JSON files found under {data_dir}", file=sys.stderr)
        return 1

    errors: list[str] = []
    for path in json_files:
        try:
            load_json(path)
        except Exception as exc:
            errors.append(f"{path}: {exc}")

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

    if errors:
        for error in errors:
            print(f"[validate] {error}", file=sys.stderr)
        return 1

    print(f"[validate] OK: {len(json_files)} JSON files")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated StuArchive JSON files.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Generated data directory.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return validate(args.data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
