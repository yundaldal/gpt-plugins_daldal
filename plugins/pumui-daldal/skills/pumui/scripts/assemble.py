"""계산 결과를 기안문(draft)에 채우는 조립 보조. 작성기(build_hwpx)는 채운 draft만 받는다.

규칙(기준/case_schema.md): 금액 항목(지급 금액·품의 금액·소요 금액 등)의 value가 비어 있고 subs도 없으면
computed.total_line으로 채우고, subs의 '지급 총액:'처럼 콜론으로 끝나는 줄 뒤에도 금액을 붙인다.
"""
import copy
import re

from readiness import AMOUNT_LABELS


def fill_draft_amounts(case):
    """금액을 채운 case 사본을 돌려준다(원본은 그대로). 이미 채워져 있으면 그대로 두므로 여러 번 불러도 같다."""
    out = copy.deepcopy(case)
    line = (out.get("computed") or {}).get("total_line")
    if not line:
        return out
    for item in out["draft"].get("items") or []:
        label = re.sub(r"\s+", "", item.get("label", ""))
        if label in AMOUNT_LABELS and not item.get("value") and not item.get("subs"):
            item["value"] = line
        if item.get("subs"):
            item["subs"] = [f"{s.rstrip()} {line}" if s.rstrip().endswith(":") else s for s in item["subs"]]
    return out
