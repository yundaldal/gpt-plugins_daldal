"""case.json(computed 포함) -> 수당 지급 내역.xlsx / 물품 구입 목록.xlsx

사용법: python build_xlsx.py case.json 출력폴더
빈 양식(기준/양식/*_빈양식.xlsx)을 복사해 작성하므로 서식·병합·열 너비가 양식 그대로 유지된다.
"""
import copy
import json
import os
import sys

import openpyxl
from openpyxl.styles import Font

FORM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "기준", "양식")
ALLOW_FORM = os.path.join(FORM_DIR, "수당 지급 내역_빈양식.xlsx")
PURCHASE_FORM = os.path.join(FORM_DIR, "물품 구입 목록_빈양식.xlsx")
G4_TITLE = {"instructor": "강사 수당", "consulting": "컨설팅 수당", "committee": "위원회 참석수당"}
# 컨설팅 예시 양식의 열 너비(회차별 일시를 나열하므로 B열이 넓다)
CONSULT_WIDTHS = {"B": 37.1, "G": 34.5, "H": 14.5, "I": 13.4}


def _style_row(ws, src_row, dst_row, ncols):
    for c in range(1, ncols + 1):
        ws.cell(dst_row, c)._style = copy.copy(ws.cell(src_row, c)._style)


def _clear_row(ws, row, ncols):
    blank = ws.cell(60, 1)._style  # 양식 밖의 빈 셀 서식(테두리 없음)
    for c in range(1, ncols + 1):
        ws.cell(row, c).value = None
        ws.cell(row, c)._style = copy.copy(blank)


def _need_complete(case):
    comp = case.get("computed")
    if not comp:
        raise ValueError("computed 가 없습니다. 먼저 amount.py 를 실행하세요.")
    if comp.get("questions"):
        raise ValueError("computed.questions 가 남아 있어 엑셀을 만들 수 없습니다: "
                         + "; ".join(q["message"] for q in comp["questions"]))


def build_allowance(case, out_path):
    _need_complete(case)
    al = case["allowance"]
    people = case["computed"]["people"]
    wb = openpyxl.load_workbook(ALLOW_FORM)
    ws = wb.active
    ws["A1"] = al["sheet_title"]
    ws["A2"] = case.get("department", ws["A2"].value)
    ws["G4"] = G4_TITLE.get(al.get("kind", "instructor"), "강사 수당")
    if al.get("kind") in ("consulting", "committee"):
        for col, w in CONSULT_WIDTHS.items():
            ws.column_dimensions[col].width = w
    first = 5
    for i, p in enumerate(people):
        r = first + i
        if r > 7:
            _style_row(ws, 7, r, 15)
        vals = [i + 1, p["b_text"], p["org"], p["position"], p["name"], p["account"],
                p["g_text"], p["h_text"], p["i_text"], p["j_formula"],
                p["income_tax"], p["local_tax"], p["deduction"], p["net"], p["note"]]
        for c, v in enumerate(vals, 1):
            ws.cell(r, c).value = v
        lines = max(str(v).count("\n") + 1 for v in vals[1:9])
        ws.row_dimensions[r].height = max(90, 21.3 * lines)
    last = first + len(people) - 1
    tot = last + 1
    for r in range(tot, max(tot, 8)):
        _clear_row(ws, r, 15)
    _style_row(ws, 5, tot, 15)
    ws.row_dimensions[tot].height = 30
    ws.cell(tot, 1).value = "합계"
    ws.merge_cells(start_row=tot, start_column=1, end_row=tot, end_column=9)
    for c, col in zip(range(10, 15), "JKLMN"):
        ws.cell(tot, c).value = f"=SUM({col}{first}:{col}{last})"
        ws.cell(tot, c).font = Font(name="맑은 고딕", size=11, bold=True)
    ws.cell(tot, 1).font = Font(name="맑은 고딕", size=11, bold=True)
    wb.save(out_path)
    return out_path


def build_purchase(case, out_path):
    _need_complete(case)
    pu = case["purchase"]
    items = pu["items"]
    wb = openpyxl.load_workbook(PURCHASE_FORM)
    ws = wb.active
    ncols = 8
    data_style = [copy.copy(ws.cell(4, c)._style) for c in range(1, ncols + 1)]
    tot_style = [copy.copy(ws.cell(9, c)._style) for c in range(1, ncols + 1)]
    data_h, tot_h = ws.row_dimensions[4].height, ws.row_dimensions[9].height
    ws.unmerge_cells("A9:B9")
    for r in range(4, max(9, 4 + len(items)) + 1):
        _clear_row(ws, r, ncols)
        ws.row_dimensions[r].height = None
    ws["A1"] = pu["sheet_title"]
    ws["A2"] = pu.get("org", ws["A2"].value)
    for i, it in enumerate(items):
        r = 4 + i
        for c in range(ncols):
            ws.cell(r, c + 1)._style = copy.copy(data_style[c])
        for c, v in enumerate([i + 1, it["name"], it.get("spec", ""), it["qty"], it.get("unit", ""),
                               it["unit_price"], f"=D{r}*F{r}", it.get("note", "")], 1):
            ws.cell(r, c).value = v
        ws.row_dimensions[r].height = data_h
    tot = 4 + len(items)
    for c in range(ncols):
        ws.cell(tot, c + 1)._style = copy.copy(tot_style[c])
    ws.row_dimensions[tot].height = tot_h
    ws.cell(tot, 1).value = "합계"
    ws.merge_cells(start_row=tot, start_column=1, end_row=tot, end_column=2)
    ws.cell(tot, 7).value = f"=SUM(G4:G{tot - 1})"
    wb.save(out_path)
    return out_path


def main(argv):
    if len(argv) != 3:
        print("사용법: python build_xlsx.py case.json 출력폴더")
        return 2
    with open(argv[1], encoding="utf-8") as f:
        case = json.load(f)
    os.makedirs(argv[2], exist_ok=True)
    made = []
    if case.get("allowance"):
        made.append(build_allowance(case, os.path.join(argv[2], "수당 지급 내역.xlsx")))
    if case.get("purchase"):
        made.append(build_purchase(case, os.path.join(argv[2], "물품 구입 목록.xlsx")))
    for m in made:
        print("생성:", m)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
