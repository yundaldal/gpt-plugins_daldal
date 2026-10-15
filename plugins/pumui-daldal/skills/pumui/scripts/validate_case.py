"""Front-door validation for the case JSON. Messages never echo entered values."""
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR.parent / "resources" / "기준"
TYPE_CODES = {"A1", "A2", "A3", "A4", "B1", "B2", "C1", "C2", "C3"}


def _norm(value):
    return re.sub(r"\s+", "", value or "")


def _is_text(value):
    return isinstance(value, str) and bool(value.strip()) and not any(ord(ch) < 32 for ch in value)


def _positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _money(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return False
    try:
        number = float(value)
    except (ValueError, TypeError):
        return False
    return math.isfinite(number)


def _valid_date(value):
    if not isinstance(value, str):
        return False
    for fmt in ("%Y-%m-%d", "%Y. %m. %d.", "%Y. %m. %d.(%a)"):
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    # Accept the Korean weekday spelling used in public documents, but verify its date.
    match = re.fullmatch(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.(?:\(([월화수목금토일])\))?", value)
    if not match:
        return False
    try:
        day = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return False
    weekday = match.group(4)
    return weekday is None or weekday == "월화수목금토일"[day.weekday()]


def _valid_time(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        return False
    return True


def _load_config():
    path = CONFIG_DIR / "유형별_구성.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_rates():
    path = CONFIG_DIR / "수당단가.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate(case):
    issues = []

    def add(field, message):
        issues.append({"field": field, "message": message})

    if not isinstance(case, dict):
        return [{"field": "case", "message": "최상위 값은 JSON 객체여야 합니다."}]
    code = case.get("type")
    if code not in TYPE_CODES:
        add("type", "A1~A4, B1~B2, C1~C3 중 유형을 확인해 주세요.")
        return issues
    draft = case.get("draft")
    if not isinstance(draft, dict):
        add("draft", "기안문 초안이 필요합니다.")
        return issues
    for field, label in (("organization", "기관명"), ("title", "제목"), ("purpose", "목적 문장")):
        if not _is_text(draft.get(field)):
            add(f"draft.{field}", f"{label}을 입력해 주세요.")
    if not _is_text(case.get("department")):
        add("department", "부서명을 입력해 주세요.")

    related = draft.get("related")
    if not isinstance(related, list):
        add("draft.related", "관련 문서 목록을 입력해 주세요. 해당 문서가 없으면 빈 목록 []으로 표시해 주세요.")
    else:
        for i, item in enumerate(related):
            prefix = f"draft.related[{i}]"
            if not isinstance(item, dict):
                add(prefix, "관련 문서 항목은 객체여야 합니다.")
                continue
            for key, label in (("doc_no", "문서번호"), ("date", "날짜"), ("title", "문서 제목")):
                if not _is_text(item.get(key)):
                    add(f"{prefix}.{key}", f"{label}을 입력해 주세요.")
            if item.get("date") and not _valid_date(item["date"]):
                add(f"{prefix}.date", "유효한 날짜와 요일을 입력해 주세요.")

    items = draft.get("items")
    if not isinstance(items, list):
        add("draft.items", "기안문 본문 항목 목록이 필요합니다.")
        items = []
    attachments = draft.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        add("draft.attachments", "기안문에 적을 붙임 목록을 입력해 주세요.")
    else:
        for i, att in enumerate(attachments):
            if not isinstance(att, dict) or not _is_text(att.get("name")) or not _is_text(att.get("count")):
                add(f"draft.attachments[{i}]", "붙임 이름과 부수를 입력해 주세요.")

    sections = [key for key in ("allowance", "purchase", "expense") if case.get(key) is not None]
    expected = "allowance" if code.startswith("A") else "purchase" if code.startswith("B") else "expense"
    if code == "C3":
        if sections not in (["expense"], ["purchase", "expense"]):
            add("allowance/purchase/expense", "C3 유형은 경비 자료가 필요하며 물품 목록은 선택 항목입니다.")
    elif sections != [expected]:
        add("allowance/purchase/expense", f"{code} 유형은 {expected} 자료만 허용합니다. 여러 종류를 합산하지 마세요.")

    if expected in ("purchase", "expense") and not _is_text(case.get("school_level")):
        add("school_level", "예산연결 업로드 파일에 넣을 학교급을 직접 지정해 주세요.")

    if expected == "allowance":
        allowance = case.get("allowance")
        if not isinstance(allowance, dict):
            allowance = {}
        configured_kind = allowance.get("kind")
        allowed_kinds = ("consulting", "committee") if code == "A4" else ("instructor",)
        if configured_kind not in allowed_kinds:
            expected_kinds = "컨설팅 또는 위원회" if code == "A4" else "강사"
            add("allowance.kind", f"{code} 유형은 {expected_kinds} 수당 종류를 선택해 주세요.")
        want_kind = configured_kind if configured_kind in allowed_kinds else allowed_kinds[0]
        people = allowance.get("people")
        if not isinstance(people, list) or not people:
            add("allowance.people", "지급 대상자 한 명 이상을 입력해 주세요.")
            people = []
        for i, person in enumerate(people):
            prefix = f"allowance.people[{i}]"
            if not isinstance(person, dict):
                add(prefix, "지급 대상자 항목은 객체여야 합니다.")
                continue
            for key, label in (("name", "성명"), ("org", "소속"), ("position", "직위"), ("income_type", "소득 구분"), ("category", "수당 구분")):
                if not _is_text(person.get(key)):
                    add(f"{prefix}.{key}", f"{label}을 입력해 주세요.")
            if person.get("income_type") not in ("기타", "사업"):
                add(f"{prefix}.income_type", "기타 또는 사업 중 실제 소득 구분을 확인해 주세요.")
            sessions = person.get("sessions")
            if not isinstance(sessions, list) or not sessions:
                add(f"{prefix}.sessions", "날짜와 인정시간 또는 시작·종료 시각을 입력해 주세요.")
                sessions = []
            for j, session in enumerate(sessions):
                sp = f"{prefix}.sessions[{j}]"
                if not isinstance(session, dict):
                    add(sp, "회기 항목은 객체여야 합니다.")
                    continue
                if not _valid_date(session.get("date")):
                    add(f"{sp}.date", "유효한 날짜(YYYY-MM-DD)를 입력해 주세요.")
                start, end = session.get("start"), session.get("end")
                if start not in (None, "") and not _valid_time(start):
                    add(f"{sp}.start", "시각은 24시간 HH:MM 형식이어야 합니다.")
                if end not in (None, "") and not _valid_time(end):
                    add(f"{sp}.end", "시각은 24시간 HH:MM 형식이어야 합니다.")
                if start and end and _valid_time(start) and _valid_time(end) and end <= start:
                    add(sp, "종료 시각은 시작 시각보다 뒤여야 합니다.")
                if want_kind == "instructor":
                    h = session.get("recognized_hours")
                    if not _finite_number(h) or float(h) <= 0:
                        add(f"{sp}.recognized_hours", "강의 인정시간을 양수로 입력해 주세요.")
                elif not (start and end):
                    add(sp, "회기 날짜와 시작·종료 시각을 입력해 주세요.")
            travel = person.get("travel")
            if not isinstance(travel, dict) or not _money(travel.get("amount")):
                add(f"{prefix}.travel.amount", "교통비 금액을 명시해 주세요. 지급하지 않으면 0을 입력합니다.")
            if want_kind == "instructor":
                manuscript = person.get("manuscript")
                if not isinstance(manuscript, dict) or manuscript.get("kind") not in ("국문", "PPT", "도서", "none"):
                    add(f"{prefix}.manuscript.kind", "원고 종류를 입력해 주세요. 원고료가 없으면 none을 선택합니다.")
                elif manuscript["kind"] != "none":
                    if not _finite_number(manuscript.get("pages")) or float(manuscript["pages"]) <= 0:
                        add(f"{prefix}.manuscript.pages", "인정 매수 또는 면수를 양수로 입력해 주세요.")
                    if not isinstance(manuscript.get("meets_spec"), bool):
                        add(f"{prefix}.manuscript.meets_spec", "원고 규격 충족 여부를 확인해 주세요.")
                if isinstance(manuscript, dict) and "revision_ratio" in manuscript and manuscript["revision_ratio"] is not None:
                    if not _finite_number(manuscript["revision_ratio"]) or not 0 <= float(manuscript["revision_ratio"]) <= 100:
                        add(f"{prefix}.manuscript.revision_ratio", "수정률은 0~100 사이여야 합니다.")
                elif isinstance(manuscript, dict) and manuscript.get("kind") not in (None, "none"):
                    add(f"{prefix}.manuscript.revision_ratio", "기존 원고 재활용 수정률을 입력하거나 null로 확인해 주세요.")
            if person.get("category") == "그룹":
                if not _positive_int(person.get("group_size")):
                    add(f"{prefix}.group_size", "그룹 강사 참여 인원은 양의 정수여야 합니다.")
            if person.get("category") not in (None, "") and want_kind != "committee":
                rates = _load_rates()
                valid_categories = set(rates["강사수당"]) | {"그룹"} if want_kind == "instructor" else {
                    key for key, value in rates["컨설팅"].items() if isinstance(value, dict)
                }
                if person.get("category") not in valid_categories:
                    add(f"{prefix}.category", "분류는 제공된 기준 단가 묶음 목록에서 선택해 주세요.")

        draft_org = draft.get("organization")
        confirmation = case.get("rate_confirmation")
        if not isinstance(confirmation, dict) or confirmation.get("confirmed") is not True:
            add("rate_confirmation.confirmed", "기준 단가가 해당 기관·회계연도에 적용되는지 확인하고 true로 표시해 주세요.")
        else:
            rates = _load_rates()
            year = rates.get("프로필", {}).get("연도")
            if confirmation.get("year") != year:
                add("rate_confirmation.year", "확인 연도가 제공된 기준 단가 묶음의 연도와 다릅니다. 기준 파일을 검토해 주세요.")
            if not _is_text(draft_org) or confirmation.get("organization") != draft_org:
                add("rate_confirmation.organization", "단가 적용 기관이 기안문 기관명과 같은지 확인해 주세요.")

    if expected == "purchase" or (code == "C3" and case.get("purchase") is not None):
        purchase = case.get("purchase")
        if not isinstance(purchase, dict):
            add("purchase", "물품 자료는 객체여야 합니다.")
            purchase = {}
        if not _is_text(purchase.get("sheet_title")):
            add("purchase.sheet_title", "물품 목록 제목을 입력해 주세요.")
        purchase_items = purchase.get("items", [])
        if not isinstance(purchase_items, list) or not purchase_items:
            add("purchase.items", "구입 품목을 한 개 이상 입력해 주세요.")
        else:
            for i, item in enumerate(purchase_items):
                prefix = f"purchase.items[{i}]"
                if not isinstance(item, dict):
                    add(prefix, "품목 항목은 객체여야 합니다.")
                    continue
                if not _is_text(item.get("name")):
                    add(f"{prefix}.name", "품명을 입력해 주세요.")
                if not _positive_int(item.get("qty")):
                    add(f"{prefix}.qty", "수량은 양의 정수여야 합니다.")
                if not _money(item.get("unit_price")):
                    add(f"{prefix}.unit_price", "단가는 0 이상의 정수 원이어야 합니다.")
        if not _is_text(purchase.get("org")):
            add("purchase.org", "물품 목록에 표시할 부서명을 입력해 주세요.")

    if expected == "expense":
        expense = case.get("expense")
        if not isinstance(expense, dict):
            add("expense", "경비 자료는 객체여야 합니다.")
            expense = {}
        lines = expense.get("lines", [])
        if not isinstance(lines, list) or not lines:
            add("expense.lines", "경비 항목을 한 개 이상 입력해 주세요.")
        else:
            for i, line in enumerate(lines):
                prefix = f"expense.lines[{i}]"
                if not isinstance(line, dict):
                    add(prefix, "경비 항목은 객체여야 합니다.")
                    continue
                if not _is_text(line.get("label")):
                    add(f"{prefix}.label", "경비 항목명을 입력해 주세요.")
                if not _money(line.get("unit_price")):
                    add(f"{prefix}.unit_price", "단가는 0 이상의 정수 원이어야 합니다.")
                factors = line.get("factors") or []
                if not isinstance(factors, list) or any(not _positive_int(f) for f in factors):
                    add(f"{prefix}.factors", "수량 인자는 양의 정수 목록이어야 합니다.")
                elif line.get("amount") not in (None, ""):
                    if not _money(line["amount"]):
                        add(f"{prefix}.amount", "금액은 0 이상의 정수 원이어야 합니다.")
                    else:
                        quantity = math.prod(factors) if factors else 1
                        if int(line["amount"]) != quantity * int(line["unit_price"]):
                            add(f"{prefix}.amount", "입력 금액과 단가×수량 계산값이 다릅니다.")

    if code == "C3" and isinstance(case.get("purchase"), dict) and isinstance(case.get("expense"), dict):
        purchase_items = case["purchase"].get("items")
        expense_lines = case["expense"].get("lines")
        if isinstance(purchase_items, list) and purchase_items and isinstance(expense_lines, list) and expense_lines:
            purchase_values = [
                item for item in purchase_items
                if isinstance(item, dict) and _positive_int(item.get("qty")) and _money(item.get("unit_price"))
            ]
            expense_values = [
                line for line in expense_lines
                if isinstance(line, dict)
                and _money(line.get("unit_price"))
                and isinstance(line.get("factors") or [], list)
                and all(_positive_int(factor) for factor in (line.get("factors") or []))
            ]
            if len(purchase_values) == len(purchase_items) and len(expense_values) == len(expense_lines):
                purchase_total = sum(int(item["qty"]) * int(item["unit_price"]) for item in purchase_values)
                expense_total = sum(
                    int(line["unit_price"]) * math.prod(line.get("factors") or [1])
                    for line in expense_values
                )
                if purchase_total != expense_total:
                    add(
                        "purchase.total",
                        "C3의 예산연결 행은 물품 목록을 사용하므로 물품 목록 합계와 경비 총액이 다릅니다. 예산연결에 반영할 범위와 두 합계를 확인해 주세요.",
                    )

    try:
        spec = _load_config()["유형"][code]
        has_computable_amount = bool(sections)
        normalized_items = {_norm(item.get("label")): item for item in items if isinstance(item, dict)}
        for body_spec in spec["본문_항목"]:
            keys = {_norm(body_spec["label"])} | {_norm(alias) for alias in body_spec.get("aliases", [])}
            found = next((normalized_items[k] for k in keys if k in normalized_items), None)
            if found is None and body_spec.get("required"):
                add(f"draft.items.{body_spec['label']}", "필수 본문 항목이 없습니다.")
                continue
            if found is None:
                continue
            amount_label = _norm(body_spec["label"]) in {"지급금액", "품의금액", "소요금액", "지출금액", "지급총액"}
            if not _is_text(found.get("value")) and not found.get("subs"):
                if not (amount_label and has_computable_amount):
                    add(f"draft.items.{body_spec['label']}", "필수 본문 내용을 입력해 주세요.")
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        add("configuration", "포함된 유형 설정을 읽을 수 없습니다.")

    return issues


def main(argv):
    if len(argv) != 2:
        print("사용법: python validate_case.py case.json")
        return 2
    try:
        case = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("[오류] case.json을 읽을 수 없거나 JSON 형식이 아닙니다.")
        return 2
    issues = validate(case)
    if not issues:
        print("[통과] 필수 입력과 수치 형식이 확인되었습니다.")
        return 0
    for issue in issues:
        print(f"[확인 필요] {issue['field']}: {issue['message']}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
