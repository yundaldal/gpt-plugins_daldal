#!/usr/bin/env python3
"""기안문 JSON(case.json의 draft 섹션) -> HWPX 기안문 본문 생성.

사용: python build_hwpx.py case.json out.hwpx
바탕 양식(기준/양식/기안문_바탕.hwpx)이 없으면 hwpx 스킬의 공문 템플릿으로 자동 생성한다.
"""
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
BASE_HWPX = ROOT / "resources" / "기준" / "양식" / "기안문_바탕.hwpx"

MARKS = "가나다라마바사아자차카타파하"
CHAR_BODY = 11   # 바탕 header에 추가한 본문 굴림체 12pt
CHAR_ORG = 7     # 기관명 22pt 굵게
PARA_BODY = 0    # 양쪽 정렬, 줄간격 160%
PARA_CENTER = 20
FONT_FACE = "굴림체"

# 에듀파인(웹기안기)에 붙여넣으면 탭 위치·문단 여백이 버려지므로, 첫 줄 들여쓰기와 기호 뒤 간격은
# 모두 일반 공백으로 낸다(줄 앞 공백 INDENT칸 + "가. " 식 1칸). 문단 모양의 내어쓰기는 한글에서
# 둘째 줄을 맞추는 용도로만 남긴다(에듀파인에서는 무시됨).
# 단계별 문단 모양: 이름 -> (paraPr id, 왼쪽 여백, 내어쓰기(음수)), 단위 HWPUNIT.
# 한글 규칙: 첫 줄 시작 = 왼쪽 여백, 둘째 줄부터 = 왼쪽 여백 - 내어쓰기.
# 굴림체 12pt 고정폭: 한글 1자 = 1200, 반각(숫자·마침표·공백) = 600.
LEVELS = {
    "L0": (23, 0, -1800),         # "1. "            둘째 줄 1800
    "L1": (24, 0, -3600),         # "  가. "         둘째 줄 3600
    "L2": (25, 0, -4200),         # "    1) "       둘째 줄 4200
    "L3": (26, 0, -3600),         # "    - "        둘째 줄 3600
    "ATT1": (27, 0, -3600),       # "붙임  "         둘째 줄 3600
    "ATT_FIRST": (28, 0, -5400),  # "붙임  1. "      둘째 줄 5400
    "ATT_NEXT": (29, 0, -6600),   # "        2. "   둘째 줄 6600(텍스트 시작)
}
# 줄 앞 공백 칸 수(반각 600). ATT_NEXT는 에듀파인(비고정폭 글꼴)에서 "붙임  "이 공백 약 8칸 폭이라
# 8칸이어야 "2."가 첫 건의 "1." 아래에 온다(사용자 확인, 한글 굴림체에서는 한 글자 오른쪽).
INDENT = {"L1": 2, "L2": 4, "L3": 4, "ATT_NEXT": 8}
BLANK = "BLANK"  # 0단계 항목 묶음 사이·붙임 앞의 빈 문단(기본 문단 모양)

NS_DECL = (
    'xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
    'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
)


# ---------- 줄 생성 (순수 함수, hwpx_check.py가 재사용) ----------

def normalized_title(title):
    """Return the official approval title with exactly one [품의] prefix."""
    title = re.sub(r"^\s*(?:\[품의\]\s*)+", "", str(title or "")).strip()
    return f"[품의] {title}".rstrip()


def render_header(draft):
    """본문 위쪽 머리 줄(기관명·수신·경유·제목)."""
    return [draft["organization"], "수신  내부결재", "(경유)",
            f"제목  {normalized_title(draft['title'])}"]


def render_lines(draft):
    """기안문 본문 (단계, 텍스트) 목록(1. 관련 ~ 붙임 끝.). 단계는 LEVELS의 키 또는 BLANK(빈 줄).

    텍스트에는 줄 앞 들여쓰기 공백이 없다. 실제 문단 텍스트는 line_text()로 만든다.
    """
    lines = []
    n = 1
    related = draft.get("related") or []
    if len(related) == 1:
        r = related[0]
        lines.append(("L0", f"{n}. 관련: {r['doc_no']}({r['date']}) {r['title']}"))
        n += 1
    elif len(related) >= 2:
        lines.append(("L0", f"{n}. 관련"))
        for i, r in enumerate(related):
            lines.append(("L1", f"{MARKS[i]}. {r['doc_no']}({r['date']}) {r['title']}"))
        n += 1

    if lines:
        lines.append((BLANK, ""))
    lines.append(("L0", f"{n}. {draft['purpose']}"))
    for i, item in enumerate(draft.get("items") or []):
        mark = f"{MARKS[i]}. {item['label']}"
        lines.append(("L1", f"{mark}: {item['value']}" if item.get("value") else mark))
        for sub in item.get("subs") or []:
            lines.append(("L3", f"- {sub}"))

    atts = draft.get("attachments") or []
    if atts:
        lines.append((BLANK, ""))
    if len(atts) == 1:
        a = atts[0]
        lines.append(("ATT1", f"붙임  {a['name']} {a['count']}.  끝."))
    elif atts:
        for i, a in enumerate(atts):
            head = "붙임  " if i == 0 else ""
            lines.append(("ATT_FIRST" if i == 0 else "ATT_NEXT",
                          f"{head}{i + 1}. {a['name']} {a['count']}."))
        lines[-1] = (lines[-1][0], lines[-1][1] + "  끝.")
    else:
        lines[-1] = (lines[-1][0], lines[-1][1] + "  끝.")
    return lines


def line_text(level, text):
    """문단에 실제로 들어가는 텍스트(단계별 줄 앞 공백 포함)."""
    return " " * INDENT.get(level, 0) + text


# ---------- 바탕 양식의 문단 스타일 ----------

def _para_pr(pid, left, intent, tab_id=0):
    """양쪽 정렬, 줄간격 160%, 왼쪽 여백·내어쓰기를 가진 paraPr."""
    def margin(k):
        return (f'<hh:margin><hc:intent value="{intent * k}" unit="HWPUNIT"/>'
                f'<hc:left value="{left * k}" unit="HWPUNIT"/>'
                '<hc:right value="0" unit="HWPUNIT"/><hc:prev value="0" unit="HWPUNIT"/>'
                '<hc:next value="0" unit="HWPUNIT"/></hh:margin>'
                '<hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>')
    return (f'<hh:paraPr id="{pid}" tabPrIDRef="{tab_id}" condense="0" fontLineHeight="0" snapToGrid="1" '
            'suppressLineNumbers="0" checked="0" textDir="LTR">'
            '<hh:align horizontal="JUSTIFY" vertical="BASELINE"/>'
            '<hh:heading type="NONE" idRef="0" level="0"/>'
            '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="BREAK_WORD" widowOrphan="0" '
            'keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>'
            '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
            '<hp:switch><hp:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">'
            f'{margin(1)}</hp:case><hp:default>{margin(2)}</hp:default></hp:switch>'
            '<hh:border borderFillIDRef="2" offsetLeft="0" offsetRight="0" offsetTop="0" '
            'offsetBottom="0" connect="0" ignoreMargin="0"/></hh:paraPr>')


# ---------- section0.xml 조립 ----------

def _para(pid, text, char=CHAR_BODY, para=PARA_BODY):
    return (f'<hp:p id="{pid}" paraPrIDRef="{para}" styleIDRef="0" pageBreak="0" '
            f'columnBreak="0" merged="0"><hp:run charPrIDRef="{char}">'
            f'<hp:t>{escape(text)}</hp:t></hp:run></hp:p>')


def build_section(base_section, draft):
    """바탕의 첫 문단(secPr)을 기관명 문단으로 재사용하고 나머지 문단을 붙인다."""
    first_end = base_section.index("</hp:p>") + len("</hp:p>")
    first = base_section[:first_end]
    first = first[first.index("<hp:p "):]
    first = first.replace('paraPrIDRef="0"', f'paraPrIDRef="{PARA_CENTER}"', 1)
    # secPr/colPr run은 그대로 두고, 빈 텍스트 run을 기관명 run으로 교체
    organization = escape(draft["organization"])
    first = re.sub(r'<hp:run charPrIDRef="0">\s*<hp:t/>\s*</hp:run>',
                   f'<hp:run charPrIDRef="{CHAR_ORG}"><hp:t>{organization}</hp:t></hp:run>',
                   first, count=1)
    first = re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", first, flags=re.S)

    header = render_header(draft)
    paras = [first, _para(1000000002, "")]
    pid = 1000000003
    for text in header[1:]:
        paras.append(_para(pid, text))
        pid += 1
    paras.append(_para(pid, ""))
    pid += 1
    for level, text in render_lines(draft):
        paras.append(_para(pid, line_text(level, text),
                           para=LEVELS[level][0] if level in LEVELS else PARA_BODY))
        pid += 1
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
            f'<hs:sec {NS_DECL}>\n' + "\n".join(paras) + "\n</hs:sec>\n")


def apply_levels(header):
    """Update only the known paragraph style definitions in the bundled base template."""
    for pid, left, intent in LEVELS.values():
        header, count = re.subn(
            rf'<hh:paraPr id="{pid}" .*?</hh:paraPr>',
            lambda _: _para_pr(pid, left, intent), header, count=1, flags=re.S,
        )
        if count != 1:
            raise ValueError(f"Bundled base template is missing paragraph style {pid}")
    return header


def build(draft, out_path):
    if not BASE_HWPX.exists():
        raise FileNotFoundError("Bundled HWPX base template is missing")
    with zipfile.ZipFile(BASE_HWPX) as zin:
        section = build_section(zin.read("Contents/section0.xml").decode("utf-8"), draft)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "Contents/section0.xml":
                    data = section.encode("utf-8")
                if info.filename == "Contents/header.xml":
                    data = apply_levels(data.decode("utf-8")).encode("utf-8")
                if info.filename == "mimetype":
                    zout.writestr(info, data, compress_type=zipfile.ZIP_STORED)
                else:
                    zout.writestr(info, data)


def main():
    args = sys.argv[1:]
    if len(args) != 2:
        sys.exit("사용: python build_hwpx.py case.json out.hwpx")
    case = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    build(case["draft"], Path(args[1]))
    print(f"생성: {args[1]}")


if __name__ == "__main__":
    main()
