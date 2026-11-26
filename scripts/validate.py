#!/usr/bin/env python3
"""Validate Open Data Catalog YAML sources, privacy hygiene, and live URLs.

Usage:
    python scripts/validate.py                  # Schema + semantic + privacy checks
    python scripts/validate.py --check-urls     # Also probe live HTTP endpoints
    python scripts/validate.py sources/tw-tdx.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from jsonschema import Draft202012Validator

ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT_DIR / "schemas" / "catalog.schema.json"
SOURCES_DIR = ROOT_DIR / "sources"

PATH_PARAM_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")

# Patterns that must never appear in a public repository
PRIVACY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "Local user home directory path",
        re.compile(r"(?<![A-Za-z0-9])/(?:home|Users)/[A-Za-z0-9._-]+/"),
    ),
    (
        "Windows local user directory path",
        re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
    ),
    (
        "Private cryptographic key block",
        re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    ),
    (
        "Hardcoded JWT / Bearer token",
        re.compile(r"Bearer\s+eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    ),
    (
        "Hardcoded GitHub / OpenAI / Google API token",
        re.compile(r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{35})\b"),
    ),
    (
        "Hardcoded secret assignment",
        re.compile(
            r"(?i)\b(?:client_secret|api_secret|access_token|refresh_token)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{16,}['\"]?"
        ),
    ),
    (
        "Taiwan mobile phone number",
        re.compile(r"(?<!\d)09\d{2}-\d{3}-\d{3}(?!\d)"),
    ),
    (
        "Email address in catalog files",
        re.compile(r"\b[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
]


def load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def format_json_path(path_parts: list[Any]) -> str:
    if not path_parts:
        return "<root>"
    out = ""
    for part in path_parts:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def validate_source_file(
    yaml_path: Path,
    validator: Draft202012Validator,
    seen_provider_ids: dict[str, Path],
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    rel = yaml_path.relative_to(ROOT_DIR) if yaml_path.is_relative_to(ROOT_DIR) else yaml_path

    try:
        with yaml_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as exc:
        return None, [f"{rel}: YAML syntax error: {exc}"]

    if not isinstance(data, dict):
        return None, [f"{rel}: Root YAML value must be a mapping/object."]

    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        loc = format_json_path(list(err.absolute_path))
        errors.append(f"{rel} [{loc}]: {err.message}")

    provider = data.get("provider") or {}
    provider_id = provider.get("id")
    if provider_id:
        if yaml_path.stem != provider_id:
            errors.append(
                f"{rel}: Filename stem '{yaml_path.stem}' must match provider.id '{provider_id}'."
            )
        if provider_id in seen_provider_ids:
            errors.append(
                f"{rel}: Duplicate provider.id '{provider_id}' (already defined in {seen_provider_ids[provider_id]})."
            )
        else:
            seen_provider_ids[provider_id] = rel

    catalog_version = data.get("catalog_version")
    changelog = data.get("changelog") or []
    if catalog_version and changelog and isinstance(changelog, list):
        latest_entry = changelog[0]
        if isinstance(latest_entry, dict) and latest_entry.get("version") != catalog_version:
            errors.append(
                f"{rel}: changelog[0].version ('{latest_entry.get('version')}') must match catalog_version ('{catalog_version}')."
            )

    base_url = provider.get("base_url")
    seen_dataset_ids: set[str] = set()
    for idx, ds in enumerate(data.get("datasets") or []):
        if not isinstance(ds, dict):
            continue
        ds_id = ds.get("id", f"index_{idx}")
        if ds_id in seen_dataset_ids:
            errors.append(f"{rel} [datasets[{idx}]]: Duplicate dataset id '{ds_id}'.")
        seen_dataset_ids.add(ds_id)

        endpoint = ds.get("endpoint")
        if endpoint and not base_url:
            errors.append(
                f"{rel} [datasets[{idx}] ({ds_id})]: Uses relative 'endpoint' ('{endpoint}') but provider.base_url is missing."
            )

        if endpoint:
            placeholders = set(PATH_PARAM_RE.findall(endpoint))
            params = ds.get("parameters") or []
            path_params = {
                p.get("name"): p
                for p in params
                if isinstance(p, dict) and p.get("in", "query") == "path"
            }
            missing_params = placeholders - set(path_params.keys())
            if missing_params:
                errors.append(
                    f"{rel} [datasets[{idx}] ({ds_id})]: Endpoint path placeholders {sorted(missing_params)} must be documented in parameters with in='path'."
                )
            if placeholders and not ds.get("sample_url"):
                missing_examples = [
                    name for name in placeholders if name in path_params and "example" not in path_params[name]
                ]
                if missing_examples:
                    errors.append(
                        f"{rel} [datasets[{idx}] ({ds_id})]: Path parameters {sorted(missing_examples)} need an 'example' (or provide dataset.sample_url)."
                    )

    return data, errors


def scan_privacy() -> list[str]:
    """Scan repository text files to ensure no personal data, local paths, or secrets leak."""
    errors: list[str] = []
    scan_targets: list[Path] = []

    for pattern in [
        "README.md",
        "AGENTS.md",
        "llms.txt",
        "requirements.txt",
        "docs/*.md",
        "docs/**/*.md",
        "docs/**/*.yaml",
        "docs/**/*.yml",
        "schemas/*.json",
        "sources/*.yaml",
        "sources/*.yml",
        "tests/*.py",
        "dist/*.json",
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
    ]:
        scan_targets.extend(sorted(ROOT_DIR.glob(pattern)))

    for file_path in scan_targets:
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(ROOT_DIR)
        content = file_path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(content.splitlines(), start=1):
            for label, regex in PRIVACY_PATTERNS:
                match = regex.search(line)
                if match:
                    errors.append(
                        f"{rel}:{line_no}: Privacy/secret check failed ({label}): '{match.group(0)}'"
                    )
    return errors


def resolve_probe_url(provider: dict[str, Any], ds: dict[str, Any]) -> str | None:
    if ds.get("sample_url"):
        return str(ds["sample_url"])
    if ds.get("endpoint") and provider.get("base_url"):
        url = str(provider["base_url"]).rstrip("/") + str(ds["endpoint"])
        for param in ds.get("parameters") or []:
            if param.get("in") == "path" and "example" in param:
                url = url.replace(f"{{{param['name']}}}", str(param["example"]))
        return url
    if ds.get("download_url"):
        return str(ds["download_url"])
    return None


def probe_single_url(
    client: httpx.Client,
    url: str,
    auth_required: bool,
    last_host_hit: dict[str, float] | None = None,
    min_interval: float = 0.35,
) -> tuple[bool, str]:
    status: int
    content_type = ""
    body_sample = ""
    host = urlparse(url).netloc

    if last_host_hit is not None and host:
        elapsed = time.monotonic() - last_host_hit.get(host, 0.0)
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)

    try:
        if auth_required:
            # Auth-gated portals (e.g. MOENV) may return HTTP 200 text/plain error messages;
            # stream GET directly to inspect headers + first bytes in a single round-trip.
            with client.stream("GET", url) as stream_resp:
                status = stream_resp.status_code
                content_type = stream_resp.headers.get("content-type", "")
                for chunk in stream_resp.iter_bytes(chunk_size=512):
                    body_sample = chunk[:512].decode("utf-8", errors="replace")
                    break
        else:
            resp = client.head(url)
            status = resp.status_code
            content_type = resp.headers.get("content-type", "")
            if status in (400, 403, 404, 405, 501):
                with client.stream("GET", url) as stream_resp:
                    status = stream_resp.status_code
                    content_type = stream_resp.headers.get("content-type", "")
                    for chunk in stream_resp.iter_bytes(chunk_size=512):
                        body_sample = chunk[:512].decode("utf-8", errors="replace")
                        break
    except Exception as exc:
        if last_host_hit is not None and host:
            last_host_hit[host] = time.monotonic()
        return False, f"connection error ({exc})"

    if last_host_hit is not None and host:
        last_host_hit[host] = time.monotonic()

    if 200 <= status < 400:
        if auth_required and "text/plain" in content_type.lower() and "api_key" in body_sample.lower():
            return True, f"HTTP {status} (auth-gated: api_key required; payload not verified without key)"
        return True, f"HTTP {status} OK"
    if auth_required and status in (401, 403, 429):
        return True, f"HTTP {status} (auth-gated: endpoint reachable; payload not verified without credentials)"
    if status == 429:
        return True, "HTTP 429 (endpoint reachable; rate-limited)"
    return False, f"HTTP {status}"


def check_urls(parsed_sources: list[tuple[Path, dict[str, Any]]], timeout: float) -> list[str]:
    errors: list[str] = []
    last_host_hit: dict[str, float] = {}
    headers = {
        "User-Agent": "OpenDataCatalogValidator/1.0 (+https://data.gov.tw)"
    }
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        for yaml_path, data in parsed_sources:
            rel = yaml_path.relative_to(ROOT_DIR) if yaml_path.is_relative_to(ROOT_DIR) else yaml_path
            provider = data["provider"]
            auth_required = bool(provider.get("auth", {}).get("required", False))

            for field_name in ("homepage", "docs_url", "license_url"):
                portal_url = provider.get(field_name)
                if portal_url:
                    ok, detail = probe_single_url(
                        client, portal_url, auth_required=False, last_host_hit=last_host_hit
                    )
                    mark = "PASS" if ok else "FAIL"
                    print(f"  [{mark}] {rel} provider.{field_name} -> {detail} ({portal_url})")
                    if not ok:
                        errors.append(f"{rel} [provider.{field_name}]: {detail} ({portal_url})")

            checked_source_pages: set[str] = set()
            for ds in data.get("datasets") or []:
                ds_id = ds["id"]
                probe_url = resolve_probe_url(provider, ds)
                if not probe_url:
                    errors.append(f"{rel} [{ds_id}]: Unable to resolve probe URL.")
                    continue
                ok, detail = probe_single_url(
                    client, probe_url, auth_required=auth_required, last_host_hit=last_host_hit
                )
                mark = "PASS" if ok else "FAIL"
                print(f"  [{mark}] {rel} dataset:{ds_id} -> {detail} ({probe_url})")
                if not ok:
                    errors.append(f"{rel} [dataset:{ds_id}]: {detail} ({probe_url})")

                source_page = ds.get("source_page")
                if source_page and source_page not in checked_source_pages:
                    checked_source_pages.add(source_page)
                    sp_ok, sp_detail = probe_single_url(
                        client, source_page, auth_required=False, last_host_hit=last_host_hit
                    )
                    sp_mark = "PASS" if sp_ok else "FAIL"
                    print(f"  [{sp_mark}] {rel} dataset:{ds_id}.source_page -> {sp_detail} ({source_page})")
                    if not sp_ok:
                        errors.append(f"{rel} [dataset:{ds_id}.source_page]: {sp_detail} ({source_page})")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate sources/*.yaml against schemas/catalog.schema.json, check privacy rules, and optionally test live URLs."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Optional specific YAML files to validate (defaults to all sources/*.yaml).",
    )
    parser.add_argument(
        "--check-urls",
        action="store_true",
        help="Send lightweight HTTP requests to verify provider homepages and dataset endpoints.",
    )
    parser.add_argument(
        "--skip-privacy",
        action="store_true",
        help="Skip repository privacy and secret leak scanning.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout in seconds when --check-urls is enabled (default: 15.0).",
    )
    args = parser.parse_args()

    if not SCHEMA_PATH.is_file():
        print(f"ERROR: Schema file not found at {SCHEMA_PATH}", file=sys.stderr)
        return 1

    schema = load_schema()
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    if args.files:
        yaml_files = [Path(f).resolve() for f in args.files]
    else:
        yaml_files = sorted(SOURCES_DIR.glob("*.yaml")) + sorted(SOURCES_DIR.glob("*.yml"))

    if not yaml_files:
        print("ERROR: No YAML catalog files found in sources/.", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    seen_provider_ids: dict[str, Path] = {}
    parsed_sources: list[tuple[Path, dict[str, Any]]] = []

    print(f"==> Validating {len(yaml_files)} catalog source file(s)...")
    for yaml_path in yaml_files:
        data, errs = validate_source_file(yaml_path, validator, seen_provider_ids)
        rel = yaml_path.relative_to(ROOT_DIR) if yaml_path.is_relative_to(ROOT_DIR) else yaml_path
        if errs:
            all_errors.extend(errs)
            print(f"  [FAIL] {rel} ({len(errs)} error(s))")
        elif data is not None:
            parsed_sources.append((yaml_path, data))
            ds_count = len(data.get("datasets") or [])
            print(
                f"  [PASS] {rel} (provider={data['provider']['id']}, v{data['catalog_version']}, {ds_count} datasets)"
            )

    if not args.skip_privacy:
        print("==> Running privacy & secret leak checks...")
        privacy_errors = scan_privacy()
        if privacy_errors:
            all_errors.extend(privacy_errors)
            print(f"  [FAIL] Found {len(privacy_errors)} privacy/secret violation(s).")
        else:
            print("  [PASS] Zero private paths, emails, phone numbers, or secrets detected.")

    if args.check_urls and parsed_sources:
        print("==> Probing live endpoints...")
        url_errors = check_urls(parsed_sources, timeout=args.timeout)
        all_errors.extend(url_errors)

    if all_errors:
        print("\nValidation FAILED with the following issues:", file=sys.stderr)
        for issue in all_errors:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    print("\nAll checks passed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
