import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import yaml

from scripts import build_index, validate


class CatalogValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = validate.load_schema()
        self.validator = validate.Draft202012Validator(self.schema)

    def test_all_sources_pass_schema_and_semantics(self) -> None:
        source_files = sorted((validate.ROOT_DIR / "sources").glob("*.yaml"))
        self.assertGreaterEqual(len(source_files), 3)
        seen_ids: dict[str, Path] = {}
        for path in source_files:
            data, errors = validate.validate_source_file(path, self.validator, seen_ids)
            self.assertIsNotNone(data)
            self.assertEqual(errors, [], f"Unexpected errors in {path}: {errors}")

    def test_privacy_scan_clean(self) -> None:
        self.assertEqual(validate.scan_privacy(), [])

    def test_detects_changelog_version_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sample = Path(tmpdir) / "demo-source.yaml"
            doc = yaml.safe_load((validate.ROOT_DIR / "docs/templates/source-template.yaml").read_text(encoding="utf-8"))
            doc["provider"]["id"] = "demo-source"
            doc["catalog_version"] = "1.1.0"
            sample.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
            _, errors = validate.validate_source_file(sample, self.validator, {})
            self.assertTrue(any("changelog[0].version" in err for err in errors))

    def test_detects_missing_path_parameter(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            sample = Path(tmpdir) / "demo-source.yaml"
            doc = yaml.safe_load((validate.ROOT_DIR / "docs/templates/source-template.yaml").read_text(encoding="utf-8"))
            doc["provider"]["id"] = "demo-source"
            doc["datasets"][0]["endpoint"] = "/items/{ItemId}"
            sample.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
            _, errors = validate.validate_source_file(sample, self.validator, {})
            self.assertTrue(any("ItemId" in err for err in errors))

    def test_probe_reports_moenv_plaintext_auth_gate_honestly(self) -> None:
        stream_resp = MagicMock(status_code=200, headers={"content-type": "text/plain; charset=utf-8"})
        stream_resp.iter_bytes.return_value = iter(["api_key 不存在。".encode("utf-8")])
        stream_ctx = MagicMock()
        stream_ctx.__enter__.return_value = stream_resp
        stream_ctx.__exit__.return_value = False

        client = MagicMock()
        client.stream.return_value = stream_ctx

        ok, detail = validate.probe_single_url(
            client, "https://data.moenv.gov.tw/api/v2/aqx_p_432", auth_required=True
        )
        self.assertTrue(ok)
        self.assertIn("auth-gated: api_key required", detail)
        client.head.assert_not_called()


class CatalogBuildIndexTests(unittest.TestCase):
    def test_compiled_outputs_match_sources(self) -> None:
        sources = build_index.load_sources()
        compiled = build_index.build_full_catalog(sources)
        self.assertEqual(compiled["total_providers"], len(sources))
        self.assertEqual(
            compiled["total_datasets"],
            sum(len(doc["datasets"]) for _, doc in sources),
        )
        llms_text = build_index.render_llms_txt(sources)
        self.assertIn("tw-data-gov", llms_text)
        self.assertIn("tw-moenv", llms_text)
        self.assertIn("tw-tdx", llms_text)


if __name__ == "__main__":
    unittest.main()
