#!/usr/bin/env python3
"""Compile sources/*.yaml into root llms.txt and dist/full-catalog.json.

Usage:
    python scripts/build_index.py          # Generate llms.txt and dist/full-catalog.json
    python scripts/build_index.py --check  # Verify generated files are up to date (for CI)
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT_DIR / "sources"
LLMS_TXT_PATH = ROOT_DIR / "llms.txt"
FULL_CATALOG_PATH = ROOT_DIR / "dist" / "full-catalog.json"


def load_sources() -> list[tuple[str, dict[str, Any]]]:
    yaml_files = sorted(SOURCES_DIR.glob("*.yaml")) + sorted(SOURCES_DIR.glob("*.yml"))
    sources: list[tuple[str, dict[str, Any]]] = []
    for path in yaml_files:
        rel_posix = path.relative_to(ROOT_DIR).as_posix()
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        sources.append((rel_posix, data))
    sources.sort(key=lambda item: item[1]["provider"]["id"])
    return sources


def render_llms_txt(sources: list[tuple[str, dict[str, Any]]]) -> str:
    total_providers = len(sources)
    total_datasets = sum(len(data.get("datasets") or []) for _, data in sources)

    lines: list[str] = [
        "# Open Data Catalog Index",
        "",
        "> 本倉庫採用「Data Catalog as Code」架構，收錄各政府與公開資料平臺之標準化 API 與下載規格。",
        "> AI Agent 請遵循兩階段檢索：先由本索引鎖定目標來源，再讀取對應的 `sources/<id>.yaml` 取得完整端點、認證方式與欄位定義。詳細規範請參閱 [AGENTS.md](AGENTS.md)。",
        "",
        f"- 收錄平臺數：{total_providers}",
        f"- 收錄資料集總數：{total_datasets}",
        "- 單一合併索引（供程式批次讀取）：[dist/full-catalog.json](dist/full-catalog.json)",
        "",
        "## 可用資料來源清單 (Sources)",
        "",
    ]

    for rel_posix, data in sources:
        provider = data["provider"]
        datasets = data.get("datasets") or []
        version = data["catalog_version"]
        updated_date = str(data["last_updated"])[:10]
        auth_info = provider.get("auth") or {}
        auth_label = auth_info.get("type", "None") if auth_info.get("required") else "免認證公開存取"
        dataset_names = "、".join(ds["name"] for ds in datasets[:6])
        if len(datasets) > 6:
            dataset_names += f" 等 {len(datasets)} 項"

        lines.append(
            f"- [{provider['name']}]({rel_posix}): {provider['summary']} "
            f"（共 {len(datasets)} 項資料集｜認證：{auth_label}｜v{version}，更新於 {updated_date}）"
        )
        lines.append(f"  - 代表資料集：{dataset_names}")

    lines.append("")
    return "\n".join(lines)


def build_full_catalog(sources: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    compiled_sources: list[dict[str, Any]] = []
    total_datasets = 0
    latest_updated = ""

    for rel_posix, raw_data in sources:
        entry = copy.deepcopy(raw_data)
        provider = entry["provider"]
        base_url = str(provider.get("base_url") or "").rstrip("/")

        if str(entry.get("last_updated", "")) > latest_updated:
            latest_updated = str(entry["last_updated"])

        for ds in entry.get("datasets") or []:
            total_datasets += 1
            if "ai_usage_guide" in ds and isinstance(ds["ai_usage_guide"], str):
                ds["ai_usage_guide"] = ds["ai_usage_guide"].strip()
            if ds.get("endpoint") and base_url:
                ds["resolved_endpoint"] = f"{base_url}{ds['endpoint']}"
            elif ds.get("download_url"):
                ds["resolved_endpoint"] = ds["download_url"]

        if isinstance(provider.get("auth", {}).get("notes"), str):
            provider["auth"]["notes"] = provider["auth"]["notes"].strip()

        compiled_sources.append(
            {
                "source_file": rel_posix,
                **entry,
            }
        )

    return {
        "schema_version": "1.0",
        "last_updated": latest_updated,
        "total_providers": len(compiled_sources),
        "total_datasets": total_datasets,
        "sources": compiled_sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate llms.txt and dist/full-catalog.json from sources/*.yaml."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check whether llms.txt and dist/full-catalog.json match current sources without writing.",
    )
    args = parser.parse_args()

    sources = load_sources()
    if not sources:
        print("ERROR: No YAML files found in sources/.", file=sys.stderr)
        return 1

    expected_llms = render_llms_txt(sources)
    expected_json = (
        json.dumps(build_full_catalog(sources), ensure_ascii=False, indent=2) + "\n"
    )

    if args.check:
        stale: list[str] = []
        if not LLMS_TXT_PATH.is_file() or LLMS_TXT_PATH.read_text(encoding="utf-8") != expected_llms:
            stale.append("llms.txt")
        if (
            not FULL_CATALOG_PATH.is_file()
            or FULL_CATALOG_PATH.read_text(encoding="utf-8") != expected_json
        ):
            stale.append("dist/full-catalog.json")

        if stale:
            print(
                f"ERROR: Generated index files are out of date: {', '.join(stale)}. "
                "Run 'python scripts/build_index.py' to update them.",
                file=sys.stderr,
            )
            return 1

        print("Index files (llms.txt, dist/full-catalog.json) are up to date.")
        return 0

    LLMS_TXT_PATH.write_text(expected_llms, encoding="utf-8")
    FULL_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    FULL_CATALOG_PATH.write_text(expected_json, encoding="utf-8")

    print(
        f"Built {LLMS_TXT_PATH.relative_to(ROOT_DIR)} and {FULL_CATALOG_PATH.relative_to(ROOT_DIR)} "
        f"({len(sources)} providers, {sum(len(s.get('datasets') or []) for _, s in sources)} datasets)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
