"""case.json(B 물품·C 일반 지출) -> 예산연결 업로드양식 결과.xlsx (에듀파인 예산연결 업로드용)

사용법: python build_budget_upload.py case.json out.xlsx
기준/양식/예산연결 업로드양식.xlsx 를 복사해 A 순번·B 품명·C 수량·E 단가·F 금액(=C*E)·L 학교급('본청')만 채운다.
붙임이 아니라 사용자가 에듀파인에 따로 올리는 파일이다. A(수당) 유형은 만들지 않는다.
"""
import copy
import json
import os
import sys

import openpyxl

FORM = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", "기준", "양식", "예산연결 업로드양식.xlsx")


def budget_rows(case):
    """(품명, 수량, 단가) 목록. B는 purchase.items, C는 expense.lines. 해당 없으면(A 유형) None."""
    if case.get("purchase"):
        return [(it["name"], int(it["qty"]), int(it["unit_price"])) for it in case["purchase"]["items"]]
    if case.get("expense"):
        rows = []
        for ln in case["expense"]["lines"]:
            qty = 1
            for f in ln.get("factors") or []:
                qty *= int(f)
            price = int(ln["unit_price"])
            if ln.get("amount") not in (None, "") and int(ln["amount"]) != qty * price:
                raise ValueError(f"{ln['label']}: 수량×단가 {qty * price} 가 금액 {ln['amount']} 와 다릅니다.")
            rows.append((ln["label"], qty, price))
        return rows
    return None


def build(case, out_path):
    rows = budget_rows(case)
    if rows is None:
        raise ValueError("예산연결 업로드양식은 물품(B)·일반 지출(C) 유형에만 만듭니다.")
    wb = openpyxl.load_workbook(FORM)
    ws = wb.active
    school_level = case.get("school_level")
    if not isinstance(school_level, str) or not school_level.strip():
        raise ValueError("예산연결 파일을 만들려면 school_level을 명시해야 합니다.")
    for i, (name, qty, price) in enumerate(rows):
        r = 2 + i
        if r > 4:  # 양식은 2~4행만 서식이 있어 2행 서식을 이어 쓴다
            for c in range(1, 19):
                ws.cell(r, c)._style = copy.copy(ws.cell(2, c)._style)
        for col, v in (("A", i + 1), ("B", name), ("C", qty), ("E", price), ("F", f"=C{r}*E{r}"), ("L", school_level)):
            ws[f"{col}{r}"].value = v
    wb.save(out_path)
    return out_path


def main(argv):
    if len(argv) != 3:
        print("사용법: python build_budget_upload.py case.json out.xlsx")
        return 2
    with open(argv[1], encoding="utf-8") as f:
        case = json.load(f)
    print(build(case, argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
