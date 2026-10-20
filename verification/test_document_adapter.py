import sys
import tempfile
import unittest
import zipfile
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "pumui-daldal" / "skills" / "pumui" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import document_adapter


class DocumentAdapterTests(unittest.TestCase):
    def test_hwpx_extracts_text_blocks_without_private_values_in_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic.hwpx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("mimetype", "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
                archive.writestr("Contents/content.hpf", "<hpf/>")
                archive.writestr("Contents/section0.xml", '<hs:sec xmlns:hs="x" xmlns:hp="y"><hp:p><hp:run><hp:t>SYNTHETIC_TEXT</hp:t></hp:run></hp:p><hp:tbl><hp:tr><hp:tc><hp:subList><hp:p><hp:run><hp:t>SYNTHETIC_TABLE_CELL</hp:t></hp:run></hp:p></hp:subList></hp:tc></hp:tr></hp:tbl></hs:sec>')
            result = document_adapter.inspect(path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["blocks"][0]["text"], "SYNTHETIC_TEXT")
        self.assertIn("paragraph:0", result["blocks"][0]["source"])
        self.assertIn("table:0/row:0/cell:0", result["blocks"][1]["source"])
        self.assertEqual(result["warnings"], [])

    def test_invalid_or_empty_hwpx_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            invalid = root / "invalid.hwpx"
            invalid.write_bytes(b"SYNTHETIC_NOT_A_ZIP")
            missing_section = root / "missing-section.hwpx"
            with zipfile.ZipFile(missing_section, "w") as archive:
                archive.writestr("mimetype", "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
                archive.writestr("Contents/content.hpf", "<hpf/>")
            empty = root / "empty.hwpx"
            with zipfile.ZipFile(empty, "w") as archive:
                archive.writestr("mimetype", "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
                archive.writestr("Contents/content.hpf", "<hpf/>")
                archive.writestr("Contents/section0.xml", "<sec/>")
            self.assertEqual(document_adapter.inspect(invalid)["status"], "unreadable")
            self.assertEqual(document_adapter.inspect(missing_section)["status"], "unreadable")
            self.assertEqual(document_adapter.inspect(empty)["status"], "unreadable")

    def test_hwp_and_pdf_report_engine_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hwp = root / "synthetic.hwp"; hwp.write_bytes(b"synthetic")
            pdf = root / "synthetic.pdf"; pdf.write_bytes(b"synthetic")
            self.assertEqual(document_adapter.inspect(hwp)["status"], "needs_engine")
            self.assertEqual(document_adapter.inspect(pdf)["status"], "needs_engine")

    def test_preinstalled_kordoc_json_is_normalized_for_hwp(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hwp = root / "synthetic.hwp"; hwp.write_bytes(b"synthetic")
            fake = root / "fake-kordoc.cmd"
            fake.write_text('@if "%2"=="--format" if "%3"=="json" echo {"success":true,"markdown":"# synthetic","format":"hwp","metadata":{"engine":"kordoc","engine_version":"synthetic","source_revision":"r1"},"blocks":[{"text":"SYNTHETIC_BLOCK"}],"warnings":[]}', encoding="utf-8")
            old = os.environ.get("PUMUI_KORDOC")
            os.environ["PUMUI_KORDOC"] = str(fake)
            try:
                result = document_adapter.inspect(hwp)
            finally:
                if old is None:
                    os.environ.pop("PUMUI_KORDOC", None)
                else:
                    os.environ["PUMUI_KORDOC"] = old
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["engine"], "kordoc")
        self.assertEqual(result["blocks"][0]["text"], "SYNTHETIC_BLOCK")

    def test_kordoc_contract_rejects_failure_and_partial_or_empty_responses(self):
        valid = {
            "success": True,
            "markdown": "# synthetic",
            "metadata": {"engine": "kordoc", "engine_version": "synthetic", "source_revision": "r1"},
            "blocks": [{"text": "SYNTHETIC_BLOCK"}],
        }
        invalid_responses = [
            {**valid, "success": False},
            {**valid, "markdown": "  ", "blocks": []},
            {**valid, "markdown": "", "blocks": []},
            {**valid, "blocks": [{"type": "text", "text": "  "}]},
            {**valid, "metadata": None},
            {**valid, "blocks": ["SYNTHETIC_NOT_A_BLOCK"]},
        ]
        for response in invalid_responses:
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    document_adapter._normalize_engine_result(response, Path("synthetic.hwp"))

    def test_kordoc_preserves_structured_table_and_image_blocks(self):
        response = {
            "success": True,
            "markdown": "",
            "metadata": {},
            "blocks": [{"type": "table", "rows": [["SYNTHETIC"]]}, {"type": "image", "src": "synthetic.png"}],
        }
        result = document_adapter._normalize_engine_result(response, Path("synthetic.hwp"))
        self.assertEqual(result["engine"], "kordoc")
        self.assertEqual(result["engine_version"], "unknown")
        self.assertEqual(result["blocks"], response["blocks"])


if __name__ == "__main__":
    unittest.main()
