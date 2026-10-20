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
                archive.writestr("Contents/section0.xml", '<hs:sec xmlns:hs="x"><hp:t xmlns:hp="x">SYNTHETIC_TEXT</hp:t></hs:sec>')
            result = document_adapter.inspect(path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["blocks"][0]["text"], "SYNTHETIC_TEXT")
        self.assertEqual(result["warnings"], [])

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
            fake.write_text('@echo {"status":"ok","format":"hwp","engine":"kordoc","engine_version":"synthetic","blocks":[{"text":"SYNTHETIC_BLOCK"}],"warnings":[]}', encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
