"""세부유형 구성 + input 폴더 파일 목록 + case.json -> 준비점검표.md

사용법: python readiness.py case.json input_dir out.md
붙임 4가지 상태: 🛠 생성 예정 / ✅ 사용자 준비 완료 / ⏳ 추후 첨부 / ➖ 해당 없음
(사용자가 정해야 하는데 파일도 상태 지정도 없는 필수 서류는 ❓ 확인 필요로 표시)
"""
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "resources", "기준", "유형별_구성.json")
AMOUNT_LABELS = {"지급금액", "품의금액", "소요금액", "지출금액", "지급총액"}
SKIP_FILES = ("입력양식",)


def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _norm(s):
    return re.sub(r"\s+", "", s or "")


def detect_type(title, config=None):
    """제목 키워드로 세부유형 코드를 추정한다(추정일 뿐, 사용자 확인 필요). 못 정하면 None."""
    config = config or load_config()
    t = _norm(title)
    major = None
    for rule in config["판별"]["대분류"]:
        if any(_norm(k) in t for k in rule["any"]):
            major = rule["대분류"]
            break
    if not major:
        return None
    for rule in config["판별"]["세부"]:
        if rule["type"].startswith(major) and any(_norm(k) in t for k in rule["any"]):
            return rule["type"]
    return None


def project_name(case):
    """붙임 이름의 {사업명}·{연수명} 자리에 넣을 사업명. 엑셀 제목에서 끝말('강사 수당 지급 내역' 등)을 떼어 낸다. 못 정하면 None."""
    title = (case.get("allowance") or {}).get("sheet_title") or (case.get("purchase") or {}).get("sheet_title")
    if not title:
        return None
    title = re.sub(r"\s*\([^()]*\)\s*$", "", title)  # 끝의 '(2 추가)' 같은 꼬리표
    name = re.sub(r"\s*(운영\s*)?(강사\s*|컨설팅\s*위원\s*)?(수당|물품)\s*(지급|구입)\s*(내역|목록)\s*$", "", title).strip()
    return name or None


def attachment_name(att, case):
    name = att["name"]
    pn = project_name(case)
    if pn:
        name = name.replace("{사업명}", pn).replace("{연수명}", pn)
    return name


def list_input_files(input_dir):
    files = []
    if input_dir and os.path.isdir(input_dir):
        for root, _, names in os.walk(input_dir):
            for n in sorted(names):
                if not n.startswith(SKIP_FILES):
                    files.append(os.path.relpath(os.path.join(root, n), input_dir))
    return files


def _match_file(keywords, files):
    for f in files:
        name = _norm(os.path.basename(f))
        if any(_norm(k) in name for k in keywords):
            return f
    return None


def attachment_status(att, case, files, status):
    """붙임 1건 -> (상태 문구, 비고)."""
    key = att["key"]
    user_status = (case.get("user_status") or {}).get(key)
    if att["source"] == "generated":
        has = bool(case.get(att.get("when")))
        if has or att.get("required"):
            return status["generated"], "파이프라인이 생성"
        return status["na"], att.get("condition", "해당 자료 없음")
    if user_status in ("ready", "later", "na"):
        return status[user_status], "사용자 지정"
    hit = _match_file(att.get("keywords", []), files)
    if hit:
        return status["ready"], "사용자 자료 확인"
    if att.get("default_status") == "later":
        return status["later"], "기본값(추후 첨부)"
    if att["required"]:
        return status["unresolved"], "input에 파일 없음 - 준비 또는 '추후 첨부' 지정 필요"
    names = [_norm(a.get("name")) for a in (case.get("draft") or {}).get("attachments") or []]
    if any(_norm(k) in n for k in att.get("keywords", []) for n in names):
        return status["unresolved"], "기안문 붙임에 기재됨 - 준비 또는 '추후 첨부' 지정 필요"
    return status["na"], att.get("condition", "해당 시 첨부")


def _find_item(items, spec_item):
    names = {_norm(spec_item["label"])} | {_norm(a) for a in spec_item.get("aliases", [])}
    for it in items:
        if _norm(it.get("label")) in names:
            return it
    return None


def body_status(spec_item, items, computed_total):
    """본문 항목 1건 -> (채움 여부, 비고)."""
    it = _find_item(items, spec_item)
    if it is None:
        return False, "case.json에 항목 없음"
    if _norm(spec_item["label"]) in AMOUNT_LABELS or _norm(it.get("label")) in AMOUNT_LABELS:
        if computed_total is not None:
            return True, "금액 자동 입력(계산 완료)"
        if it.get("value") or it.get("subs"):
            return True, ""
        return False, "금액 계산 전"
    if it.get("value") or any(it.get("subs") or []):
        return True, ""
    return False, "내용 비어 있음"


def build_report(case, files, config=None):
    """(markdown 문자열, 요약 dict)."""
    config = config or load_config()
    status = config["상태값"]
    spec = config["유형"][case["type"]]
    draft = case.get("draft") or {}
    total = (case.get("computed") or {}).get("total")
    rows, counts = [], {k: 0 for k in status}
    inv = {v: k for k, v in status.items()}
    for i, att in enumerate(spec["붙임"], 1):
        st, note = attachment_status(att, case, files, status)
        counts[inv[st]] += 1
        tag = "필수" if att["required"] else "선택"
        rows.append(f"| {i} | {attachment_name(att, case)} | {tag} | {st} | {note} |")

    body_rows, missing = [], 0
    for sp in spec["본문_항목"]:
        ok, note = body_status(sp, draft.get("items") or [], total)
        if not ok and sp["required"]:
            missing += 1
        mark = "✅ 채움" if ok else ("⬜ 비어 있음" if sp["required"] else "➖ 선택(비어 있음)")
        body_rows.append(f"| {sp['label']} | {'필수' if sp['required'] else '선택'} | {mark} | {note} |")
    rel = [r for r in draft.get("related") or [] if r.get("doc_no") and r.get("date")]
    if not rel:
        missing += 1
    body_rows.append(f"| 관련 문서 | 필수 | {'✅ ' + str(len(rel)) + '건' if rel else '⬜ 비어 있음'} | 번호·날짜는 사용자 입력 |")
    purpose_ok = bool(draft.get("purpose"))
    if not purpose_ok:
        missing += 1
    body_rows.append(f"| 목적 문장 | 필수 | {'✅ 채움' if purpose_ok else '⬜ 비어 있음'} | |")
    title_ok = str(draft.get("title", "")).startswith("[품의]")
    if not title_ok:
        missing += 1
    body_rows.append(f"| 제목([품의]로 시작) | 필수 | {'✅ 확인' if title_ok else '⬜ 확인 필요'} | |")

    waiting = counts["later"] + counts["unresolved"]
    lines = [
        f"# 준비점검표 - {draft.get('title', case.get('case_id', ''))}",
        "",
        f"- 세부유형: {case['type']} {spec['이름']}",
        f"- input 파일 {len(files)}건: " + (", ".join(files) if files else "(없음)"),
        "",
        "## 붙임 서류",
        "",
        "| 번호 | 서류 | 구분 | 상태 | 비고 |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "## 기안문 본문 항목",
        "",
        "| 항목 | 구분 | 상태 | 비고 |",
        "|---|---|---|---|",
        *body_rows,
        "",
        "## 요약",
        "",
        " / ".join(f"{status[k]} {counts[k]}건" for k in ("generated", "ready", "later", "na", "unresolved") if counts[k] or k != "unresolved"),
        "",
        f"- 본문 필수 항목 누락: {missing}건",
        f"- 제출 준비: {'완료' if not waiting and not missing else '미완료'}"
        + (f" (추후 첨부·확인 필요 {waiting}건, 본문 누락 {missing}건)" if waiting or missing else ""),
        "",
    ]
    return "\n".join(lines), {"counts": counts, "missing_body": missing, "waiting": waiting}


def main(argv):
    if len(argv) != 4:
        print("사용법: python readiness.py case.json input_dir out.md")
        return 2
    with open(argv[1], encoding="utf-8") as f:
        case = json.load(f)
    md, summary = build_report(case, list_input_files(argv[2]))
    with open(argv[3], "w", encoding="utf-8") as f:
        f.write(md)
    print("생성:", argv[3], summary["counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
