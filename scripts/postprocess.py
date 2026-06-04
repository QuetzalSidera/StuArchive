#!/usr/bin/env python3
"""Post-process generated StuArchive JSON files."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from logging_utils import get_logger, setup_logging


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "sources.json"
DEFAULT_DATA_DIR = ROOT / "data"
SCHEMA_VERSION = "1.0.0"

STATIC_URL_RE = re.compile(r"(?<!:)//static\.kivo\.wiki/")
WHITESPACE_RE = re.compile(r"\s+")

GENERIC_ALIAS_FIELDS = (
    "name",
    "name_cn",
    "name_jp",
    "name_zh_tw",
    "title",
    "title_cn",
    "title_jp",
    "title_zh_tw",
    "label",
    "slug",
    "original_file_name",
)


JsonObject = dict[str, Any]
LOGGER = get_logger("postprocess")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp_path.replace(path)


def safe_relative_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Unsafe output path: {path}")
    return candidate


def raw_url(config: JsonObject, rel_path: Path | str) -> str:
    base = config.get("raw_base_url", "").rstrip("/")
    path = rel_path.as_posix() if isinstance(rel_path, Path) else rel_path
    return f"{base}/{path}" if base else path


def file_stem(value: Any) -> str:
    text = str(value)
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in text)


def absolutize_urls(value: Any) -> Any:
    if isinstance(value, str):
        return STATIC_URL_RE.sub("https://static.kivo.wiki/", value)
    if isinstance(value, list):
        return [absolutize_urls(item) for item in value]
    if isinstance(value, dict):
        return {key: absolutize_urls(item) for key, item in value.items()}
    return value


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = WHITESPACE_RE.sub(" ", text)
    return text or None


def normalized_alias(value: str) -> str:
    text = clean_text(value) or ""
    return WHITESPACE_RE.sub("", text).casefold()


def add_alias(aliases: list[str], seen: set[str], value: Any) -> None:
    text = clean_text(value)
    if not text or text in seen:
        return
    seen.add(text)
    aliases.append(text)


def add_student_name_aliases(aliases: list[str], seen: set[str], family: Any, given: Any, skin: Any) -> None:
    family_text = clean_text(family)
    given_text = clean_text(given)
    skin_text = clean_text(skin)

    bases: list[str] = []
    if family_text and given_text:
        bases.extend([f"{family_text}{given_text}", f"{family_text} {given_text}"])
    elif given_text:
        bases.append(given_text)
    elif family_text:
        bases.append(family_text)

    for base in bases:
        add_alias(aliases, seen, base)
    if given_text:
        add_alias(aliases, seen, given_text)

    if not skin_text:
        return

    for base in bases:
        add_alias(aliases, seen, f"{base}（{skin_text}）")
        add_alias(aliases, seen, f"{base}({skin_text})")
        add_alias(aliases, seen, f"{base} {skin_text}")
        add_alias(aliases, seen, f"{base}-{skin_text}")
    if given_text:
        add_alias(aliases, seen, f"{given_text}（{skin_text}）")
        add_alias(aliases, seen, f"{given_text}({skin_text})")
        add_alias(aliases, seen, f"{given_text} {skin_text}")
        add_alias(aliases, seen, f"{given_text}-{skin_text}")


def student_aliases(item: JsonObject) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()

    add_student_name_aliases(aliases, seen, item.get("family_name"), item.get("given_name"), item.get("skin"))
    add_student_name_aliases(aliases, seen, item.get("family_name_cn"), item.get("given_name_cn"), item.get("skin_cn"))
    add_student_name_aliases(aliases, seen, item.get("family_name_jp"), item.get("given_name_jp"), item.get("skin_jp"))
    add_student_name_aliases(aliases, seen, item.get("family_name"), item.get("given_name"), item.get("skin_zh_tw"))
    add_student_name_aliases(aliases, seen, item.get("family_name_cn"), item.get("given_name_cn"), item.get("skin_zh_tw"))
    return aliases


def generic_aliases(item: JsonObject) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for field in GENERIC_ALIAS_FIELDS:
        add_alias(aliases, seen, item.get(field))
    return aliases


def collect_aliases(resource: JsonObject, item: JsonObject) -> list[str]:
    if resource.get("name") == "students":
        return student_aliases(item)
    return generic_aliases(item)


def append_unique_id(mapping: dict[str, list[str]], key: str, item_id: str) -> None:
    values = mapping.setdefault(key, [])
    if item_id not in values:
        values.append(item_id)


def detail_rel_path(resource: JsonObject, item_id: Any) -> str | None:
    if not resource.get("detail_path"):
        return None
    output_dir = safe_relative_path(resource.get("output_dir", resource["name"]))
    return (output_dir / f"{file_stem(item_id)}.json").as_posix()


def build_lookup(
    config: JsonObject,
    resource: JsonObject,
    collection_index: JsonObject,
    index_rel_path: Path,
) -> JsonObject:
    items = collection_index.get("items", [])
    id_key = collection_index.get("id_key") or resource.get("id_key", "id")

    by_id: dict[str, JsonObject] = {}
    by_alias: dict[str, list[str]] = {}
    by_normalized_alias: dict[str, list[str]] = {}

    for item in items:
        if not isinstance(item, dict) or id_key not in item:
            continue

        item_id = item[id_key]
        item_id_key = str(item_id)
        entry: JsonObject = {
            "id": item_id,
            "source_path": index_rel_path.as_posix(),
            "source_raw_url": raw_url(config, index_rel_path),
            "item": item,
        }

        detail_path = detail_rel_path(resource, item_id)
        if detail_path:
            entry["detail_path"] = detail_path
            entry["detail_raw_url"] = raw_url(config, detail_path)

        by_id[item_id_key] = entry

        for alias in collect_aliases(resource, item):
            append_unique_id(by_alias, alias, item_id_key)
            normalized = normalized_alias(alias)
            if normalized:
                append_unique_id(by_normalized_alias, normalized, item_id_key)

    return {
        "schema_version": SCHEMA_VERSION,
        "name": resource["name"],
        "description": resource.get("description", ""),
        "generated_at": collection_index.get("generated_at"),
        "id_key": id_key,
        "source_index": {
            "path": index_rel_path.as_posix(),
            "raw_url": raw_url(config, index_rel_path),
        },
        "normalization": "NFKC, trim, collapse whitespace, casefold, then remove whitespace.",
        "total_items": len(by_id),
        "alias_count": len(by_alias),
        "normalized_alias_count": len(by_normalized_alias),
        "by_id": by_id,
        "by_alias": by_alias,
        "by_normalized_alias": by_normalized_alias,
    }


def lookup_summary(config: JsonObject, lookup_rel_path: Path, lookup: JsonObject) -> JsonObject:
    return {
        "path": lookup_rel_path.as_posix(),
        "raw_url": raw_url(config, lookup_rel_path),
        "alias_count": lookup.get("alias_count", 0),
        "normalized_alias_count": lookup.get("normalized_alias_count", 0),
        "total_items": lookup.get("total_items", 0),
    }


def update_manifest_lookup(manifest: JsonObject, resource_name: str, summary: JsonObject) -> bool:
    updated = False
    for resource in manifest.get("resources", []):
        if resource.get("name") != resource_name or resource.get("type") != "collection":
            continue
        resource["lookup_path"] = summary["path"]
        resource["lookup_raw_url"] = summary["raw_url"]
        resource["lookup_alias_count"] = summary["alias_count"]
        resource["lookup_normalized_alias_count"] = summary["normalized_alias_count"]
        updated = True
    return updated


def postprocess_data(config: JsonObject, data_dir: Path) -> JsonObject:
    normalized_files = 0
    for path in sorted(data_dir.rglob("*.json")):
        payload = load_json(path)
        normalized = absolutize_urls(payload)
        if normalized != payload:
            write_json(path, normalized)
            normalized_files += 1

    manifest_path = data_dir / "index.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else None

    lookup_count = 0
    for resource in config.get("resources", []):
        if resource.get("mode") != "paginated":
            continue

        output_dir = safe_relative_path(resource.get("output_dir", resource["name"]))
        index_rel_path = output_dir / "index.json"
        index_path = data_dir / index_rel_path
        if not index_path.exists():
            continue

        collection_index = load_json(index_path)
        lookup = build_lookup(config, resource, collection_index, index_rel_path)
        lookup_rel_path = output_dir / "lookup.json"
        summary = lookup_summary(config, lookup_rel_path, lookup)
        collection_index["lookup"] = summary

        write_json(data_dir / lookup_rel_path, lookup)
        write_json(index_path, collection_index)
        lookup_count += 1

        if manifest is not None:
            update_manifest_lookup(manifest, resource["name"], summary)

    if manifest is not None:
        write_json(manifest_path, manifest)

    return {
        "normalized_files": normalized_files,
        "lookup_count": lookup_count,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize generated data and rebuild lookup indexes.")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="Path to sources.json.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Generated data directory.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    config = load_json(args.sources)
    result = postprocess_data(config, args.data_dir)
    LOGGER.info(
        "normalized %s file(s), wrote %s lookup index(es)",
        result["normalized_files"],
        result["lookup_count"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
