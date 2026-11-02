"""Independently reopen an upload workbook and compare it to case and template."""
from decimal import Decimal
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def require(condition, message):
    if not condition:
        raise ValueError('엑셀 검증 실패: ' + message)


def expected_rows(case, kind):
    rows = []
    for i, item in enumerate(case['items'], 1):
        q, p = Decimal(str(item['수량'])), Decimal(str(item['예상단가']))
        if kind == 'gyeonggi':
            rows.append([item['내용'], item['규격'], item['단위'], q, p])
        else:
            fee = Decimal(str(item['수수료'])) if '수수료' in item else None
            rows.append([Decimal(i), item['내용'], item.get('S2B물품번호', ''),
                         item['규격'], q, item['단위'], p, q * p, fee])
    return rows


def validate(case, output, template, kind):
    output, template = Path(output), Path(template)
    require(output.is_file() and output.stat().st_size > 0, '파일 없음')
    expected = expected_rows(case, kind)
    if kind == 'gyeonggi':
        import xlrd
        original = xlrd.open_workbook(str(template), formatting_info=True)
        result = xlrd.open_workbook(str(output), formatting_info=True)
        require(original.sheet_names() == result.sheet_names() == ['품목내역'], '시트')
        a, b = original.sheet_by_index(0), result.sheet_by_index(0)
        require(b.nrows == len(expected) + 1 and b.ncols == 5, '행/열 수')
        require(a.row_values(0) == b.row_values(0), '헤더')
        require(a.merged_cells == b.merged_cells, '병합')
        require({c: x.width for c, x in a.colinfo_map.items()} ==
                {c: x.width for c, x in b.colinfo_map.items()}, '열 너비')
        for col in range(5):
            old = original.xf_list[a.cell_xf_index(0, col)]
            new = result.xf_list[b.cell_xf_index(0, col)]
            require(vars(old.alignment) == vars(new.alignment), '헤더 정렬')
            # xlutils renumbers the FONT table; compare every font property,
            # excluding only its table position (observed 5 -> 7).
            font_a = vars(original.font_list[old.font_index])
            font_b = vars(result.font_list[new.font_index])
            require({k: v for k, v in font_a.items() if k != 'font_index'} ==
                    {k: v for k, v in font_b.items() if k != 'font_index'}, '헤더 글꼴')
            for edge in ('left', 'right', 'top', 'bottom', 'diag'):
                style = edge + '_line_style'
                require(getattr(old.border, style) == getattr(new.border, style), '테두리')
                if getattr(old.border, style):
                    color = edge + '_colour_index'
                    require(getattr(old.border, color) == getattr(new.border, color), '테두리 색')
        for r, values in enumerate(expected, 1):
            for c, value in enumerate(values):
                cell = b.cell(r, c)
                if isinstance(value, Decimal):
                    require(cell.ctype == xlrd.XL_CELL_NUMBER and cell.value == float(value), '숫자 값')
                else:
                    require(cell.value == value, '문자 값')
        original.release_resources()
        result.release_resources()
    else:
        member = 'xl/worksheets/sheet1.xml'
        with ZipFile(template) as a, ZipFile(output) as b:
            require(a.namelist() == b.namelist(), '통합문서 구성')
            require(b.testzip() is None, 'ZIP CRC')
            for name in a.namelist():
                if name != member:
                    require(a.read(name) == b.read(name), '원본 구성 변경: ' + name)
            old, new = ET.fromstring(a.read(member)), ET.fromstring(b.read(member))
            sheet = new.find('s:sheetData', NS)
            rows = list(sheet)
            require(len(rows) == len(expected) + 3, '품목 행 수')
            require(not new.findall('.//s:f', NS), '수식')
            require(new.find('s:dimension', NS).get('ref') == f'A1:I{len(expected)+3}', '입력 범위')
            for r, values in enumerate(expected, 4):
                row = rows[r-1]
                require(row.get('r') == str(r), '행 순서')
                cells = {cell.get('r'): cell for cell in row}
                wanted = {f'{chr(65+c)}{r}': v for c, v in enumerate(values) if v is not None and v != ''}
                require(len(cells) == len(row) and set(cells) == set(wanted), '입력 열/빈칸')
                for address, value in wanted.items():
                    cell = cells[address]
                    if isinstance(value, Decimal):
                        require(cell.get('t') in (None, 'n') and
                                Decimal(cell.findtext('s:v', namespaces=NS)) == value, '숫자 값: ' + address)
                    else:
                        require(cell.get('t') == 'inlineStr' and
                                ''.join(cell.find('s:is', NS).itertext()) == value, '문자 값: ' + address)
            for row in rows[3:]:
                sheet.remove(row)
            new.find('s:dimension', NS).set('ref', old.find('s:dimension', NS).get('ref'))
            require(ET.tostring(old) == ET.tostring(new), '제목/헤더/병합/기존 서식')
    return {'verified': True, 'item_count': len(expected), 'path': str(output.resolve())}
