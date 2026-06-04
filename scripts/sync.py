#!/usr/bin/env python3
"""Sync Kivo public JSON endpoints into static files under data/."""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from logging_utils import get_logger, setup_logging
from postprocess import absolutize_urls, build_lookup, lookup_summary, postprocess_data


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "sources.json"
DEFAULT_DATA_DIR = ROOT / "data"
SCHEMA_VERSION = "1.0.0"


JsonObject = dict[str, Any]
LOGGER = get_logger("sync")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> JsonObject:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    payload = absolutize_urls(payload)
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


def build_url(base_url: str, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    base = base_url.rstrip("/")
    if path == "/":
        return base + "/"
    return base + "/" + path.lstrip("/")


def add_query_param(path: str, key: str, value: str | int) -> str:
    split = urllib.parse.urlsplit(path)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(split.query, keep_blank_values=True) if k != key]
    query.append((key, str(value)))
    return urllib.parse.urlunsplit((split.scheme, split.netloc, split.path, urllib.parse.urlencode(query), split.fragment))


def file_stem(value: Any) -> str:
    text = str(value)
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in text)


def raw_url(config: JsonObject, rel_path: Path) -> str:
    base = config.get("raw_base_url", "").rstrip("/")
    return f"{base}/{rel_path.as_posix()}" if base else rel_path.as_posix()


def load_previous_resources(data_dir: Path) -> dict[str, JsonObject]:
    manifest_path = data_dir / "index.json"
    if not manifest_path.exists():
        return {}

    try:
        manifest = load_json(manifest_path)
    except Exception as exc:
        LOGGER.warning("cannot load previous manifest for stale fallback: %s", exc)
        return {}

    resources = manifest.get("resources", [])
    if not isinstance(resources, list):
        return {}
    return {resource["name"]: resource for resource in resources if isinstance(resource, dict) and "name" in resource}


def mark_stale(entry: JsonObject, error: str, attempted_at: str) -> JsonObject:
    stale_entry = dict(entry)
    stale_entry["stale"] = True
    stale_entry["sync_error"] = error
    stale_entry["sync_attempted_at"] = attempted_at
    return stale_entry


def fallback_single_entry(resource: JsonObject, config: JsonObject, data_dir: Path, error: str, attempted_at: str) -> JsonObject | None:
    rel_path = safe_relative_path(resource["output"])
    if not (data_dir / rel_path).exists():
        return None
    return mark_stale(
        {
            "name": resource["name"],
            "type": "single",
            "description": resource.get("description", ""),
            "upstream_url": build_url(config["base_url"], resource["path"]),
            "path": rel_path.as_posix(),
            "raw_url": raw_url(config, rel_path),
        },
        error,
        attempted_at,
    )


def fallback_collection_entry(
    resource: JsonObject,
    config: JsonObject,
    data_dir: Path,
    error: str,
    attempted_at: str,
) -> JsonObject | None:
    output_dir = safe_relative_path(resource.get("output_dir", resource["name"]))
    index_rel_path = output_dir / "index.json"
    index_path = data_dir / index_rel_path
    if not index_path.exists():
        return None

    try:
        collection = load_json(index_path)
    except Exception as exc:
        LOGGER.warning("cannot load stale collection index %s: %s", index_rel_path, exc)
        return None

    entry: JsonObject = {
        "name": resource["name"],
        "type": "collection",
        "description": resource.get("description", ""),
        "upstream_url": build_url(config["base_url"], resource["path"]),
        "path": index_rel_path.as_posix(),
        "raw_url": raw_url(config, index_rel_path),
        "list_key": resource["list_key"],
        "max_page": collection.get("max_page", 0),
        "synced_pages": collection.get("synced_pages", 0),
        "total_items": collection.get("total_items", 0),
        "details_synced": collection.get("details_synced", 0),
        "details_available": bool(resource.get("detail_path")),
    }

    lookup = collection.get("lookup", {})
    if isinstance(lookup, dict) and lookup.get("path"):
        entry["lookup_path"] = lookup.get("path")
        entry["lookup_raw_url"] = lookup.get("raw_url")
        entry["lookup_alias_count"] = lookup.get("alias_count", 0)
        entry["lookup_normalized_alias_count"] = lookup.get("normalized_alias_count", 0)

    return mark_stale(entry, error, attempted_at)


def fallback_resource_entry(
    resource: JsonObject,
    previous_resources: dict[str, JsonObject],
    config: JsonObject,
    data_dir: Path,
    error: str,
    attempted_at: str,
) -> JsonObject | None:
    previous_entry = previous_resources.get(resource["name"])
    if previous_entry:
        return mark_stale(previous_entry, error, attempted_at)

    if resource.get("mode", "single") == "paginated":
        return fallback_collection_entry(resource, config, data_dir, error, attempted_at)
    return fallback_single_entry(resource, config, data_dir, error, attempted_at)


class KivoClient:
    def __init__(self, config: JsonObject, delay: float | None = None) -> None:
        self.base_url = config["base_url"]
        self.user_agent = config.get("user_agent", "StuArchive/0.1")
        self.timeout = float(config.get("timeout_seconds", 30))
        self.retries = int(config.get("request_retries", 3))
        self.retry_delay = float(config.get("request_retry_delay_seconds", 2))
        self.delay = float(config.get("request_delay_seconds", 0.1) if delay is None else delay)
        self.request_count = 0

    def get(self, path: str, resource: JsonObject | None = None) -> tuple[JsonObject, str]:
        url = build_url(self.base_url, path)
        timeout = float(resource.get("timeout_seconds", self.timeout)) if resource else self.timeout
        retries = int(resource.get("request_retries", self.retries)) if resource else self.retries
        retry_delay = float(resource.get("request_retry_delay_seconds", self.retry_delay)) if resource else self.retry_delay
        attempts = max(1, retries + 1)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": self.user_agent,
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    body = response.read()
                break
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", "replace")
                if exc.code < 500 or attempt == attempts:
                    raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:200]}") from exc
                last_error = exc
            except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
                if attempt == attempts:
                    raise RuntimeError(f"Network error for {url}: {exc}") from exc
                last_error = exc

            wait_seconds = retry_delay * attempt
            LOGGER.warning("retry %s/%s for %s: %s; waiting %.1fs", attempt, attempts - 1, url, last_error, wait_seconds)
            time.sleep(wait_seconds)
        else:
            raise RuntimeError(f"Network error for {url}: {last_error}")

        self.request_count += 1
        if self.delay > 0:
            time.sleep(self.delay)

        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            snippet = body[:200].decode("utf-8", "replace")
            raise RuntimeError(f"Non-JSON response for {url}: {snippet}") from exc
        return payload, url


def ensure_success(payload: JsonObject, url: str) -> None:
    if payload.get("success") is False:
        raise RuntimeError(f"Kivo API returned success=false for {url}: {payload.get('message')}")


def get_data(payload: JsonObject, url: str) -> JsonObject:
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"Expected object payload.data for {url}")
    return data


def sync_single(
    resource: JsonObject,
    client: KivoClient,
    config: JsonObject,
    data_dir: Path,
    fetched_at: str,
) -> JsonObject:
    payload, url = client.get(resource["path"], resource)
    ensure_success(payload, url)
    rel_path = safe_relative_path(resource["output"])
    write_json(data_dir / rel_path, payload)
    return {
        "name": resource["name"],
        "type": "single",
        "description": resource.get("description", ""),
        "upstream_url": url,
        "path": rel_path.as_posix(),
        "raw_url": raw_url(config, rel_path),
        "fetched_at": fetched_at,
    }


def list_items(payload: JsonObject, key: str, url: str) -> list[JsonObject]:
    data = get_data(payload, url)
    items = data.get(key)
    if not isinstance(items, list):
        raise RuntimeError(f"Expected payload.data.{key} list for {url}")
    return items


def unique_ids(items: list[JsonObject], id_key: str) -> list[Any]:
    seen: set[str] = set()
    ids: list[Any] = []
    for item in items:
        if not isinstance(item, dict) or id_key not in item:
            continue
        value = item[id_key]
        marker = str(value)
        if marker in seen:
            continue
        seen.add(marker)
        ids.append(value)
    return ids


def sync_details(
    resource: JsonObject,
    ids: list[Any],
    client: KivoClient,
    config: JsonObject,
    data_dir: Path,
    output_dir: Path,
    details_limit: int | None,
) -> list[JsonObject]:
    detail_path_template = resource.get("detail_path")
    if not detail_path_template:
        return []

    detail_entries: list[JsonObject] = []
    ids_to_fetch = ids[:details_limit] if details_limit else ids
    total = len(ids_to_fetch)
    for index, value in enumerate(ids_to_fetch, start=1):
        quoted_id = urllib.parse.quote(str(value), safe="")
        detail_path = detail_path_template.format(id=quoted_id)
        payload, url = client.get(detail_path, resource)
        ensure_success(payload, url)
        rel_path = output_dir / f"{file_stem(value)}.json"
        write_json(data_dir / rel_path, payload)
        detail_entries.append(
            {
                "id": value,
                "upstream_url": url,
                "path": rel_path.as_posix(),
                "raw_url": raw_url(config, rel_path),
            }
        )
        if index % 50 == 0 or index == total:
            LOGGER.info("%s: details %s/%s", resource["name"], index, total)
    return detail_entries


def sync_collection(
    resource: JsonObject,
    client: KivoClient,
    config: JsonObject,
    data_dir: Path,
    fetched_at: str,
    include_details: bool,
    include_disabled_details: bool,
    max_pages: int | None,
    details_limit: int | None,
) -> JsonObject:
    name = resource["name"]
    output_dir = safe_relative_path(resource.get("output_dir", name))
    list_key = resource["list_key"]
    page_param = resource.get("page_param", "page")
    first_path = add_query_param(resource["path"], page_param, 1)
    first_payload, first_url = client.get(first_path, resource)
    ensure_success(first_payload, first_url)
    first_data = get_data(first_payload, first_url)
    max_page = int(first_data.get("max_page", 1))
    page_count = min(max_page, max_pages) if max_pages else max_page

    pages: list[JsonObject] = []
    items: list[JsonObject] = []

    for page in range(1, page_count + 1):
        if page == 1:
            payload = first_payload
            url = first_url
        else:
            payload, url = client.get(add_query_param(resource["path"], page_param, page), resource)
            ensure_success(payload, url)

        page_items = list_items(payload, list_key, url)
        items.extend(page_items)
        rel_path = output_dir / "pages" / f"{page}.json"
        write_json(data_dir / rel_path, payload)
        pages.append(
            {
                "page": page,
                "upstream_url": url,
                "path": rel_path.as_posix(),
                "raw_url": raw_url(config, rel_path),
                "item_count": len(page_items),
            }
        )

    id_key = resource.get("id_key", "id")
    ids = unique_ids(items, id_key)
    details_enabled = bool(resource.get("details_enabled", False))
    should_sync_details = include_details and (details_enabled or include_disabled_details)
    details = sync_details(resource, ids, client, config, data_dir, output_dir, details_limit) if should_sync_details else []

    index_rel_path = output_dir / "index.json"
    collection_index = {
        "schema_version": SCHEMA_VERSION,
        "name": name,
        "description": resource.get("description", ""),
        "source": {
            "site": config.get("source_site_url", "https://kivo.wiki/"),
            "api_path": resource["path"],
            "upstream_url": build_url(config["base_url"], resource["path"]),
        },
        "generated_at": fetched_at,
        "list_key": list_key,
        "id_key": id_key,
        "max_page": max_page,
        "synced_pages": page_count,
        "total_items": len(items),
        "details_synced": len(details),
        "details_enabled": details_enabled,
        "items": items,
        "pages": pages,
        "details": details,
    }

    lookup_rel_path = output_dir / "lookup.json"
    lookup = build_lookup(config, resource, collection_index, index_rel_path)
    lookup_info = lookup_summary(config, lookup_rel_path, lookup)
    collection_index["lookup"] = lookup_info
    write_json(data_dir / lookup_rel_path, lookup)
    write_json(data_dir / index_rel_path, collection_index)

    LOGGER.info(
        "%s: pages %s/%s, items %s, details %s, aliases %s",
        name,
        page_count,
        max_page,
        len(items),
        len(details),
        lookup_info["alias_count"],
    )
    return {
        "name": name,
        "type": "collection",
        "description": resource.get("description", ""),
        "upstream_url": build_url(config["base_url"], resource["path"]),
        "path": index_rel_path.as_posix(),
        "raw_url": raw_url(config, index_rel_path),
        "list_key": list_key,
        "max_page": max_page,
        "synced_pages": page_count,
        "total_items": len(items),
        "details_synced": len(details),
        "details_available": bool(resource.get("detail_path")),
        "lookup_path": lookup_info["path"],
        "lookup_raw_url": lookup_info["raw_url"],
        "lookup_alias_count": lookup_info["alias_count"],
        "lookup_normalized_alias_count": lookup_info["normalized_alias_count"],
    }


def selected_resources(config: JsonObject, selected: set[str] | None) -> list[JsonObject]:
    resources = config.get("resources", [])
    if selected is None:
        return resources
    matched = [resource for resource in resources if resource["name"] in selected]
    missing = selected - {resource["name"] for resource in matched}
    if missing:
        raise RuntimeError(f"Unknown resource name(s): {', '.join(sorted(missing))}")
    return matched


def sync(args: argparse.Namespace) -> int:
    config = load_json(args.sources)
    data_dir = args.data_dir
    fetched_at = utc_now()
    client = KivoClient(config, delay=args.delay)
    names = set(args.resource) if args.resource else None
    previous_resources = load_previous_resources(data_dir)
    manifest_resources: list[JsonObject] = []
    sync_errors: list[JsonObject] = []

    for resource in selected_resources(config, names):
        mode = resource.get("mode", "single")
        try:
            if mode == "single":
                manifest_resources.append(sync_single(resource, client, config, data_dir, fetched_at))
            elif mode == "paginated":
                manifest_resources.append(
                    sync_collection(
                        resource,
                        client,
                        config,
                        data_dir,
                        fetched_at,
                        include_details=args.include_details,
                        include_disabled_details=args.include_disabled_details,
                        max_pages=args.max_pages,
                        details_limit=args.details_limit,
                    )
                )
            else:
                raise RuntimeError(f"Unsupported resource mode for {resource['name']}: {mode}")
        except Exception as exc:
            error = str(exc)
            fallback = fallback_resource_entry(resource, previous_resources, config, data_dir, error, fetched_at)
            if not fallback:
                raise
            LOGGER.warning("%s failed, keeping stale data: %s", resource["name"], error)
            manifest_resources.append(fallback)
            sync_errors.append(
                {
                    "name": resource["name"],
                    "path": resource.get("path"),
                    "error": error,
                    "kept_stale": True,
                }
            )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "name": config.get("name", "StuArchive"),
        "description": config.get("description", ""),
        "generated_at": fetched_at,
        "generator": "scripts/sync.py",
        "source": {
            "site": config.get("source_site_url", "https://kivo.wiki/"),
            "api_base_url": config["base_url"],
        },
        "license": config.get("license", {}),
        "raw": {
            "base_url": config.get("raw_base_url", ""),
            "entrypoint": raw_url(config, Path("index.json")),
            "template": f"{config.get('raw_base_url', '').rstrip('/')}" + "/{path}",
        },
        "resources": manifest_resources,
        "request_count": client.request_count,
        "sync_errors": sync_errors,
    }
    write_json(data_dir / "index.json", manifest)
    postprocess_result = postprocess_data(config, data_dir)
    LOGGER.info("wrote %s", data_dir / "index.json")
    LOGGER.info(
        "postprocess: normalized %s file(s), wrote %s lookup index(es), wrote %s student profile(s)",
        postprocess_result["normalized_files"],
        postprocess_result["lookup_count"],
        postprocess_result["student_profile_count"],
    )
    LOGGER.info("requests: %s", client.request_count)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Kivo public JSON data into data/ for GitHub Raw access.")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="Path to sources.json.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR, help="Output data directory.")
    parser.add_argument("--resource", action="append", help="Resource name to sync. Repeat to sync multiple resources.")
    parser.add_argument("--include-details", action="store_true", help="Also fetch per-id detail files for configured resources.")
    parser.add_argument(
        "--include-disabled-details",
        action="store_true",
        help="Fetch detail files even for resources marked details_enabled=false.",
    )
    parser.add_argument("--max-pages", type=int, help="Limit pages per paginated resource, useful for smoke tests.")
    parser.add_argument("--details-limit", type=int, help="Limit details per resource, useful for smoke tests.")
    parser.add_argument("--delay", type=float, help="Override request delay seconds from sources.json.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return sync(args)
    except Exception as exc:
        LOGGER.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
