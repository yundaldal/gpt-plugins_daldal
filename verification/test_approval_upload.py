"""Workbook regression harness, not an Ed fine host integration test."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import xlrd

SKILL = Path(__file__).resolve().parents[1] / 'plugins/approval-excel/skills/instructions'
spec = importlib.util.spec_from_file_location('build_upload', SKILL / 'scripts/build_upload.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case = {'region': '경기도', 'items': [
            {'내용': '색연필', '규격': '12색', '단위': '세트', '수량': 3, '예상단가': 2000},
            {'내용': '종이 & 클립', '규격': '', '단위': '개', '수량': 2, '예상단가': 1500}]}

    def output(self, suffix):
        return Path(self.temp.name) / ('output' + suffix)

    def test_gyeonggi_values_and_structure(self):
        out = builder.build(self.case, self.output('.xls'))
        original = xlrd.open_workbook(str(SKILL / 'templates/엑셀산출파일 경기도.xls'), formatting_info=True)
        result = xlrd.open_workbook(str(out), formatting_info=True)
        self.assertEqual(result.sheet_names(), original.sheet_names())
        a, b = original.sheet_by_index(0), result.sheet_by_index(0)
        self.assertEqual(b.row_values(0), a.row_values(0))
        self.assertEqual((b.nrows, b.ncols), (3, 5))
        self.assertEqual(b.row_values(1), ['색연필', '12색', '세트', 3, 2000])
        self.assertEqual(b.row_values(2), ['종이 & 클립', '', '개', 2, 1500])
        self.assertEqual(a.merged_cells, b.merged_cells)
        self.assertEqual({c: i.width for c, i in a.colinfo_map.items()},
                         {c: i.width for c, i in b.colinfo_map.items()})
        for col in range(5):
            old = original.xf_list[a.cell_xf_index(0, col)]
            new = result.xf_list[b.cell_xf_index(0, col)]
            self.assertEqual(vars(old.alignment), vars(new.alignment))
            for edge in ('left', 'right', 'top', 'bottom', 'diag'):
                style = edge + '_line_style'
                self.assertEqual(getattr(old.border, style), getattr(new.border, style))
                if getattr(old.border, style):
                    color = edge + '_colour_index'
                    self.assertEqual(getattr(old.border, color), getattr(new.border, color))

    def test_other_values_and_template_preservation(self):
        self.case['region'] = '서울'
        self.case['items'][0]['S2B물품번호'] = '00123'
        self.case['items'][0]['수수료'] = 100
        self.case['items'][1]['내용'] = '=SUM(A1:A2) & <문자>'
        out = builder.build(self.case, self.output('.xlsx'))
        with ZipFile(SKILL / 'templates/엑셀산출파일 경기도외 시도교육청.xlsx') as a, ZipFile(out) as b:
            self.assertEqual(a.namelist(), b.namelist())
            for name in a.namelist():
                if name != 'xl/worksheets/sheet1.xml':
                    self.assertEqual(a.read(name), b.read(name), name)
            old = ET.fromstring(a.read('xl/worksheets/sheet1.xml'))
            new = ET.fromstring(b.read('xl/worksheets/sheet1.xml'))
            old_rows = old.findall('s:sheetData/s:row', NS)
            rows = new.findall('s:sheetData/s:row', NS)
            self.assertEqual(len(rows), 5)
            for i in range(3):
                self.assertEqual(ET.tostring(old_rows[i]), ET.tostring(rows[i]))
            self.assertEqual(ET.tostring(old.find('s:mergeCells', NS)), ET.tostring(new.find('s:mergeCells', NS)))
            self.assertEqual(len(new.findall('.//s:f', NS)), 0)
            cells = {c.attrib['r']: ''.join(c.itertext()) for r in rows[3:] for c in r}
            self.assertEqual(cells, {'A4': '1', 'B4': '색연필', 'C4': '00123', 'D4': '12색',
                                    'E4': '3', 'F4': '세트', 'G4': '2000', 'H4': '6000', 'I4': '100',
                                    'A5': '2', 'B5': '=SUM(A1:A2) & <문자>', 'E5': '2',
                                    'F5': '개', 'G5': '1500', 'H5': '3000'})

    def test_all_regions(self):
        for region in builder.REGIONS:
            self.assertEqual(builder.region_kind(region), 'other')
        for region in ['경기', '경기도', '경기도교육청']:
            self.assertEqual(builder.region_kind(region), 'gyeonggi')
        for region in ['', '미확인', '수도권']:
            with self.assertRaises(ValueError):
                builder.region_kind(region)

    def test_reject_invalid_or_extra_values(self):
        variants = []
        for key, value in [('합계', 9000), ('예상금액', 1), ('수량', 0), ('수량', True),
                           ('예상단가', 'NaN'), ('수수료', 0), ('S2B물품번호', '123'),
                           ('내용', ''), ('단위', ''), ('규격', None)]:
            case = copy.deepcopy(self.case)
            case['items'][0][key] = value
            variants.append(case)
        variants += [dict(self.case, region=''), dict(self.case, items=[]), dict(self.case, total=9000)]
        for case in variants:
            with self.subTest(case=case), self.assertRaises(ValueError):
                builder.build(case, self.output('.xls'))
            self.assertFalse(self.output('.xls').exists())

    def test_extension_and_region_change(self):
        with self.assertRaises(ValueError):
            builder.build(self.case, self.output('.xlsx'))
        builder.build(self.case, self.output('.xls'))
        self.case['region'] = '경기도 외'
        builder.build(self.case, self.output('.xlsx'))
        with self.assertRaises(ValueError):
            builder.build(self.case, self.output('.xls'))

    def test_instruction_contract(self):
        text = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        for phrase in ['지역을 추측하거나 기본값으로 지정하지', '총합계·소계 행',
                       '사용자가 확인한 후에만 4단계', '지역 변경 시', builder.GUIDANCE]:
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
