"""Fill the supplied Ed fine templates; never create summary rows or sheets."""
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
REGIONS = {"서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
           "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주", "경기도 외"}
FIELDS = {"내용", "규격", "단위", "수량", "예상단가", "S2B물품번호", "예상금액", "수수료"}
GUIDANCE = "에듀파인에서 [파일]업로드를 통해 타이핑 없이 바로 행에 넣으세요."


def region_kind(region):
    if region in {"경기", "경기도", "경기도교육청"}:
        return "gyeonggi"
    if region in REGIONS:
        return "other"
    raise ValueError("지역을 경기도 또는 경기도 외(시도명 약칭)로 먼저 확인하세요.")


def number(value, field, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{field}: 숫자가 필요합니다.")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{field}: 숫자가 필요합니다.") from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError(f"{field}: 유효한 양의 수량/음수가 아닌 금액이 필요합니다.")
    if len(result.as_tuple().digits) > 15 or abs(result.adjusted()) > 14:
        raise ValueError(f"{field}: Excel 정밀도 범위를 벗어납니다.")
    return result


def prepare(case):
    if set(case) != {"region", "items"}:
        raise ValueError("입력은 region과 items만 허용합니다. 합계·설명은 파일 밖에 두세요.")
    kind = region_kind(case["region"])
    items = case["items"]
    if not isinstance(items, list) or not items or len(items) > 65535:
        raise ValueError("확인된 품목 행이 필요합니다(1~65535행).")
    rows = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict) or set(item) - FIELDS:
            raise ValueError("양식에 없는 열은 허용하지 않습니다.")
        for field in ("내용", "규격", "단위"):
            value = item.get(field)
            if not isinstance(value, str) or (field != "규격" and not value.strip()):
                raise ValueError(f"{field}을 확인하세요. 규격 없음은 빈 문자열로 명시하세요.")
        for field in ("내용", "규격", "단위", "S2B물품번호"):
            value = item.get(field, "")
            if not isinstance(value, str) or len(value) > 32767 or any(ord(c) < 32 and c not in "\t\n\r" for c in value):
                raise ValueError(f"{field}: 유효한 문자열이 필요합니다.")
        quantity = number(item.get("수량"), "수량", positive=True)
        price = number(item.get("예상단가"), "예상단가")
        amount = number(str(quantity * price), "예상금액")
        if "예상금액" in item and number(item["예상금액"], "예상금액") != amount:
            raise ValueError("예상금액과 수량×예상단가가 다릅니다. 원자료를 다시 확인하세요.")
        fee = number(item["수수료"], "수수료") if "수수료" in item else None
        if kind == "gyeonggi":
            if item.get("S2B물품번호") or fee is not None:
                raise ValueError("경기도 양식에 없는 S2B물품번호·수수료는 별도 확인이 필요합니다.")
            rows.append([item["내용"], item["규격"], item["단위"], quantity, price])
        else:
            rows.append([index, item["내용"], item.get("S2B물품번호", ""),
                         item["규격"], quantity, item["단위"], price, amount, fee])
    return kind, rows


def build(case, output):
    kind, rows = prepare(case)
    output = Path(output)
    suffix = ".xls" if kind == "gyeonggi" else ".xlsx"
    if output.suffix.lower() != suffix:
        raise ValueError(f"선택한 원본 양식의 {suffix} 확장자를 유지하세요.")
    template = ROOT / "templates" / ("엑셀산출파일 경기도.xls" if kind == "gyeonggi"
                                      else "엑셀산출파일 경기도외 시도교육청.xlsx")
    if output.resolve() == template.resolve():
        raise ValueError("원본 양식을 덮어쓸 수 없습니다.")
    if kind == "gyeonggi":
        import xlrd
        from xlutils.copy import copy
        source = xlrd.open_workbook(str(template), formatting_info=True)
        book = copy(source)
        sheet = book.get_sheet(0)
        for r, values in enumerate(rows, 1):
            for c, value in enumerate(values):
                sheet.write(r, c, float(value) if isinstance(value, Decimal) else value)
        book.save(str(output))
    else:
        # Preserve every archive member and all original worksheet XML except
        # its used range and appended data rows, including drawings and styles.
        xml_rows = []
        for r, values in enumerate(rows, 4):
            cells = []
            for c, value in enumerate(values):
                if value is None or value == "":
                    continue
                address = f"{chr(65 + c)}{r}"
                if isinstance(value, (int, Decimal)):
                    cells.append(f'<c r="{address}"><v>{value}</v></c>')
                else:
                    cells.append(f'<c r="{address}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>')
            xml_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
        with ZipFile(template) as source, ZipFile(output, "w") as target:
            for member in source.infolist():
                data = source.read(member.filename)
                if member.filename == "xl/worksheets/sheet1.xml":
                    xml = data.decode("utf-8")
                    if xml.count('</sheetData>') != 1 or 'ref="A1:I3"' not in xml:
                        raise ValueError("원본 양식 구조가 변경되었습니다.")
                    data = xml.replace('ref="A1:I3"', f'ref="A1:I{len(rows)+3}"', 1).replace(
                        '</sheetData>', ''.join(xml_rows) + '</sheetData>').encode("utf-8")
                target.writestr(member, data)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        result = build(json.loads(args.case.read_text(encoding="utf-8-sig")), args.output)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"생성 중단: {exc}\n")
    print(result)
    print(GUIDANCE)
