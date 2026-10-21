import io
import tempfile
import unittest
import zipfile
from pathlib import Path

import package_release


class PackageReleaseTests(unittest.TestCase):
    def test_archive_is_deterministic_and_matches_exact_plugin_files(self):
        files = package_release.collect_plugin_files()
        first = package_release.build_archive_bytes(files)
        second = package_release.build_archive_bytes(files)

        self.assertEqual(first, second)
        package_release.verify_archive_bytes(first, files)
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            names = archive.namelist()
        self.assertEqual(len(names), len(files))
        self.assertTrue(all(name.startswith("pumui-daldal/") for name in names))
        self.assertTrue(all("\\" not in name for name in names))
        self.assertTrue(all("__pycache__" not in name and not name.endswith(".pyc") for name in names))

    def test_archive_verifier_rejects_source_mismatch(self):
        files = package_release.collect_plugin_files()
        payload = package_release.build_archive_bytes(files)
        _, archive_name = files[0]
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "synthetic-source.bin"
            path.write_bytes(b"synthetic-mismatch")
            modified_files = list(files)
            modified_files[0] = (path, archive_name)
            with self.assertRaisesRegex(ValueError, "content differs from source"):
                package_release.verify_archive_bytes(payload, modified_files)


if __name__ == "__main__":
    unittest.main()
