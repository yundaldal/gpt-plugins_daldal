"""File delivery regression: real code execution, including text-only deployment."""
import base64
import copy
import hashlib
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'plugins/approval-excel/skills/instructions'
PACKAGE = runpy.run_path(str(ROOT / 'verification/package_approval.py'))
BUILDER = runpy.run_path(str(SKILL / 'scripts/build_upload.py'))
VALIDATE = runpy.run_path(str(SKILL / 'scripts/validate_upload.py'))['validate']


def recovery_code():
    return (SKILL / 'runtime.md').read_text(encoding='utf-8').split('```python\n', 1)[1].split('```', 1)[0]


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        # Screenshot amounts; missing snack specification is explicitly empty
        # in this test fixture, not inferred for a live user's request.
        self.case = {'region': '경기도 외', 'items': [
            {'내용': '과자', '규격': '', '단위': '개', '수량': 3, '예상단가': 7650},
            {'내용': '바낙스 타코 AR 문어 낚싯대', '규격': 'C 155H', '단위': '개', '수량': 1, '예상단가': 99000}]}

    def test_text_only_both_regions_and_repeated_download(self):
        env = {}
        exec(recovery_code(), env)
        for region, kind, suffix, template in [
            ('경기도 외', 'other', '.xlsx', '엑셀산출파일 경기도외 시도교육청.xlsx'),
            ('경기도', 'gyeonggi', '.xls', '엑셀산출파일 경기도.xls')]:
            self.case['region'] = region
            first = env['generate_upload'](self.case, self.folder)
            path = Path(first['path'])
            self.assertTrue(first['verified'])
            self.assertEqual(first['item_count'], 2)
            self.assertEqual(path.suffix, suffix)
            self.assertTrue(path.is_file())  # still exists after temporary runtime removal
            VALIDATE(self.case, path, SKILL / 'templates' / template, kind)
            second = env['generate_upload'](self.case, self.folder)
            self.assertNotEqual(second['path'], first['path'])
            self.assertEqual(Path(second['path']).read_bytes(), path.read_bytes())

    def test_xlsx_recovery_without_site_packages_or_original_paths(self):
        code = recovery_code() + '\nprint(json.dumps(generate_upload(' + repr(self.case) + ', ' + repr(str(self.folder)) + ')))\n'
        script = self.folder / 'isolated.py'
        script.write_text('import json\n' + code, encoding='utf-8')
        result = subprocess.run([sys.executable, '-I', '-S', str(script)], cwd=self.folder,
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['verified'])

    def test_recovery_bytes_match_release_sources(self):
        self.assertEqual((SKILL / 'runtime.md').read_text(encoding='utf-8'), PACKAGE['runtime_text']())
        env = {}
        exec(recovery_code(), env)
        payload = base64.b64decode(env['PAYLOAD'])
        self.assertEqual(hashlib.sha256(payload).hexdigest(), env['PAYLOAD_SHA256'])
        with ZipFile(io.BytesIO(payload)) as z:
            self.assertEqual(len(z.namelist()), 4)
            for name in z.namelist():
                self.assertEqual(z.read(name), (SKILL / name).read_bytes())

    def test_corrupt_recovery_payload_rejected(self):
        env = {}
        exec(recovery_code(), env)
        env['PAYLOAD_SHA256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, '변경'):
            env['generate_upload'](self.case, self.folder)
        self.assertFalse(list(self.folder.glob('*.xlsx')))

    def test_validator_rejects_wrong_saved_values_both_regions(self):
        for region, kind, suffix, template in [
            ('경기도 외', 'other', '.xlsx', '엑셀산출파일 경기도외 시도교육청.xlsx'),
            ('경기도', 'gyeonggi', '.xls', '엑셀산출파일 경기도.xls')]:
            self.case['region'] = region
            wrong = copy.deepcopy(self.case)
            wrong['items'][0]['수량'] = 2
            out = self.folder / ('bad' + suffix)
            BUILDER['_write'](wrong, out)
            with self.assertRaisesRegex(ValueError, '검증 실패'):
                VALIDATE(self.case, out, SKILL / 'templates' / template, kind)

    def test_failed_validation_does_not_publish_or_replace(self):
        output = self.folder / 'upload.xlsx'
        original_write = BUILDER['_write']
        def wrong_write(case, path):
            wrong = copy.deepcopy(case)
            wrong['items'][0]['수량'] = 2
            return original_write(wrong, path)
        with patch.dict(BUILDER['build'].__globals__, {'_write': wrong_write}):
            with self.assertRaises(ValueError):
                BUILDER['build'](self.case, output)
            self.assertFalse(output.exists())
            output.write_bytes(b'previous download')
            with self.assertRaises(ValueError):
                BUILDER['build'](self.case, output)
            self.assertEqual(output.read_bytes(), b'previous download')
        self.assertFalse(list(self.folder.glob('.upload-*')))

    def test_release_zip_and_version(self):
        files = PACKAGE['package_files']()
        with ZipFile(ROOT / 'downloads/approval-excel.zip') as z:
            self.assertEqual(set(files), set(z.namelist()))
            for name, data in files.items():
                self.assertEqual(z.read(name), data, name)
        for name in ('plugin.json', '.codex-plugin/plugin.json'):
            self.assertEqual(json.loads(files[name])['version'], '0.14.5')

    def test_delivery_instruction_and_unrelated_workflow_preserved(self):
        text = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        for phrase in ('runtime.md', 'M1 입력 확정', 'M2 실행', 'M3 검증', 'M4 전달',
                       'sandbox:/mnt/data/', '사용자에게 원본 양식을 다시 첨부하라고 요구하지',
                       '사용자가 확인한 후에만 4단계', '총합계·소계 행'):
            self.assertIn(phrase, text)
        # All original drafting and confirmation instructions remain byte-for-text identical.
        before = subprocess.check_output(['git', 'show', 'HEAD:plugins/approval-excel/skills/instructions/SKILL.md'], cwd=ROOT).decode('utf-8')
        marker = '## 첫 대화 시 안내 메시지'
        self.assertEqual(before.split(marker, 1)[1].replace('\r\n', '\n'), text.split(marker, 1)[1])


if __name__ == '__main__':
    unittest.main()
