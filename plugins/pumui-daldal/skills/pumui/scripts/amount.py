"""품의봇 금액 계산: 수당·원고료·세금·한글 금액·산출기초 문구.

사용법: python amount.py case.json   (computed 필드를 채워 같은 파일에 저장)
모호하거나 빠진 입력은 예외를 내지 않고 computed.questions 에 담아 돌려준다(역질문용).
"""
import json
import os
import sys
from datetime import date
from fractions import Fraction

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RATES_PATH = os.path.join(BASE_DIR, "..", "resources", "기준", "수당단가.json")
WEEK = "월화수목금토일"

CAT_LABEL = {
    "특별1": "특별강사 1",
    "특별2": "특별강사 2",
    "일반1종": "일반강사 1종",
    "일반2종": "일반강사 2종",
    "일반3종_평생": "일반강사 3종(평생교육)",
    "일반3종_외국어체육전산": "일반강사 3종(외국어·체육·전산)",
    "보조_실기": "보조강사(실기실습)",
    "보조_전산": "보조강사(전산 실기실습)",
}
CAT_CONSULT = ("컨설팅_교수전문가", "컨설팅_일반인", "컨설팅_공무원")


def load_rates(path=RATES_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------- 한글 금액 ----------
_DIGIT = "영일이삼사오육칠팔구"
_SMALL = ["", "십", "백", "천"]
_BIG = ["", "만", "억", "조"]


def to_korean_amount(n):
    """2403000 -> '이백사십만삼천'. 공문 관례대로 십·백·천 앞의 '일'도 적는다(10만 -> 일십만)."""
    n = int(n)
    if n < 0:
        raise ValueError("음수 금액")
    if n == 0:
        return "영"
    parts, g = [], 0
    while n:
        chunk = n % 10000
        n //= 10000
        if chunk:
            s = ""
            for i in range(4):
                d = (chunk // 10 ** i) % 10
                if d:
                    s = _DIGIT[d] + _SMALL[i] + s
            parts.append(s + _BIG[g])
        g += 1
    return "".join(reversed(parts))


def format_amount_line(n):
    """2403000 -> '금2,403,000원(금이백사십만삼천원)'"""
    n = int(n)
    return f"금{n:,}원(금{to_korean_amount(n)}원)"


# ---------- 공통 보조 ----------
def _fr(x):
    return Fraction(str(x))


def _round(fr):
    return int(fr + Fraction(1, 2)) if fr >= 0 else -int(-fr + Fraction(1, 2))


def _fmt_h(fr):
    fr = Fraction(fr)
    return str(int(fr)) if fr.denominator == 1 else str(float(fr))


def _fmt_date(iso):
    d = date.fromisoformat(iso)
    return f"{d.year}. {d.month}. {d.day}.({WEEK[d.weekday()]})"


def _minutes(hm):
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def _q(person, field, message, options=None):
    q = {"person": person.get("name", ""), "field": field, "message": message}
    if options:
        q["options"] = options
    return q


def _rate_options(rates):
    opts = [f"{k}: 기본 {v['기본']:,}원 / 초과 {v['초과']:,}원"
            for k, v in rates["강사수당"].items() if not k.startswith("_")]
    g = rates["그룹강사"]
    opts.append(f"그룹: 기본 {g['기본료']:,}원({g['기본인원']}인·{g['기본시간']}시간) / 초과 1인당 {g['초과_1인당']:,}원")
    return opts


def _by_date(sessions):
    """날짜별로 묶어 [(date, [session, ...]), ...] (입력 순서 유지)."""
    out = {}
    for s in sessions:
        out.setdefault(s["date"], []).append(s)
    return list(out.items())


def _duration_h(s):
    """인정시간이 있으면 그 값, 없으면 시작~종료 실제 시간, 둘 다 없으면 None."""
    if s.get("recognized_hours") not in (None, ""):
        return _fr(s["recognized_hours"])
    if s.get("start") and s.get("end"):
        return Fraction(_minutes(s["end"]) - _minutes(s["start"]), 60)
    return None


def _sessions_text(sessions, title, closing):
    """B열 '강의 일시' 문구. 1회면 '날짜\\n시간(N시간)', 여러 회면 '*제목\\n날짜 시간...\\n마무리'."""
    def span(s):
        return f"{s['start']}~{s['end']}" if s.get("start") and s.get("end") else ""
    if len(sessions) == 1 and closing == "hours":
        s = sessions[0]
        h = _duration_h(s)
        tail = f"({_fmt_h(h)}시간)" if h is not None else ""
        return f"{_fmt_date(s['date'])}\n{span(s)}{tail}".rstrip()
    lines = [f"{_fmt_date(s['date'])} {span(s)}".rstrip() for s in sessions]
    if closing == "hours":
        tot = sum((_duration_h(s) or 0 for s in sessions), Fraction(0))
        tail = f"【{len(_by_date(sessions))}일/총 {_fmt_h(tot)}시간】"
    else:
        tail = f"총 {len(sessions)}회"
    return "\n".join([f"*{title}"] + lines + [tail])


# ---------- 세금 ----------
def calc_tax(total, taxable_business, income_type, rates=None):
    """Bundled profile arithmetic only; the user must verify applicable policy."""
    rates = rates or load_rates()
    tax = rates["세금"]
    unit = int(rates.get("세금", {}).get("절사단위", 10))

    def floor_unit(value):
        return int(value) // unit * unit

    if income_type == "기타":
        rule = tax["기타소득"]
        inc = floor_unit(Fraction(total) * int(rule["세율_퍼센트"]) / 100) if total > int(rule["면제_이하"]) else 0
    elif income_type == "사업":
        rule = tax["사업소득"]
        inc = floor_unit(Fraction(taxable_business) * int(rule["세율_퍼센트"]) / 100)
    else:
        raise ValueError(f"소득구분 오류: {income_type!r}")
    return inc, floor_unit(Fraction(inc) * int(tax["지방소득세"]["세율_퍼센트"]) / 100)


# ---------- 강사수당 ----------
def calc_instructor(person, rates):
    """강의일별 (기본 + 초과×(인정시간-1)) 합산. 30분 미만은 기본의 반액. 그룹 강사는 별도.
    반환: {"pay", "text", "questions", "hours"} (pay=None이면 계산 불가)."""
    qs = []
    cat = person.get("category")
    table = {k: v for k, v in rates["강사수당"].items() if not k.startswith("_")}
    if cat not in table and cat != "그룹":
        qs.append(_q(person, "category", "강사 유형이 없거나 기준표에 없습니다. 어느 항목에 해당하는지 알려주세요.", _rate_options(rates)))
        return {"pay": None, "text": "", "questions": qs, "hours": None}
    sessions = person.get("sessions") or []
    if not sessions:
        qs.append(_q(person, "sessions", "강의 일자·시간 정보가 없습니다."))
        return {"pay": None, "text": "", "questions": qs, "hours": None}
    per_day = []
    for d, ss in _by_date(sessions):
        hs = [s.get("recognized_hours") for s in ss]
        if any(h in (None, "") for h in hs):
            guess = [_duration_h(s) for s in ss]
            hint = f" (실제 시간 기준 약 {_fmt_h(sum(guess, Fraction(0)))}시간)" if all(g is not None for g in guess) else ""
            qs.append(_q(person, "recognized_hours", f"{_fmt_date(d)} 인정시간이 없습니다{hint}. 인정시간을 알려주세요."))
            continue
        per_day.append((d, sum((_fr(h) for h in hs), Fraction(0))))
    if qs:
        return {"pay": None, "text": "", "questions": qs, "hours": None}
    total_h = sum((h for _, h in per_day), Fraction(0))

    if cat == "그룹":
        g = rates["그룹강사"]
        size = person.get("group_size")
        if not size:
            qs.append(_q(person, "group_size", "그룹 강사의 참여 인원 수가 없습니다."))
        if any(h > g["기본시간"] for _, h in per_day):
            qs.append(_q(person, "recognized_hours",
                         f"그룹 강사는 기본 {g['기본인원']}인·{g['기본시간']}시간 기준입니다. 시간 초과분의 산정 기준을 확인해 주세요."))
        if qs:
            return {"pay": None, "text": "", "questions": qs, "hours": total_h}
        extra_n = max(0, int(size) - g["기본인원"])
        days = len(per_day)
        pay = (g["기본료"] + g["초과_1인당"] * extra_n) * days
        lines = [f"{pay:,}원", f"다수인(그룹)강사: 기본 {g['기본료']:,}원×{days}회({g['기본인원']}인·{g['기본시간']}시간)"]
        if extra_n:
            lines.append(f"+ 인원 초과 {g['초과_1인당']:,}원×{extra_n}명×{days}회")
        return {"pay": pay, "text": "\n".join(lines), "questions": [], "hours": total_h}

    base, extra = table[cat]["기본"], table[cat]["초과"]
    half = rates["반액규칙"]
    pay = Fraction(0)
    full_days = half_days = 0
    extra_h = Fraction(0)
    for _, h in per_day:
        if h < _fr(half["기준_시간"]):
            pay += base * _fr(half["비율"])
            half_days += 1
        else:
            pay += base + extra * max(Fraction(0), h - 1)
            extra_h += max(Fraction(0), h - 1)
            full_days += 1
    pay = _round(pay)
    unit = "시간" if len(per_day) == 1 and not half_days else "회"
    lines = [f"{pay:,}원"]
    if full_days:
        n = 1 if unit == "시간" else full_days
        lines.append(f"{CAT_LABEL[cat]}: 기본 {base:,}원×{n}{unit}")
    if half_days:
        hb = _round(base * _fr(half["비율"]))
        lines.append(("+ " if full_days else f"{CAT_LABEL[cat]}: ") + f"30분 미만 반액 {hb:,}원×{half_days}회")
    if extra_h:
        lines.append(f"+ 초과 {extra:,}원×{_fmt_h(extra_h)}시간")
    return {"pay": pay, "text": "\n".join(lines), "questions": [], "hours": total_h}


# ---------- 원고료 ----------
def calc_manuscript(person, rates, hours):
    """min(매수, 시간×한도)×단가, 재활용 수정률 규칙 적용. hours=강의 인정시간 합계."""
    m = person.get("manuscript") or {}
    kind = m.get("kind") or "none"
    if kind == "none":
        return {"pay": 0, "text": "0원\n", "questions": [], "warnings": []}
    qs, warns = [], []
    if kind not in ("국문", "PPT", "도서"):
        qs.append(_q(person, "manuscript.kind", f"원고 종류({kind!r})를 알 수 없습니다. 국문/PPT/도서/none 중에서 알려주세요."))
        return {"pay": None, "text": "", "questions": qs, "warnings": warns}
    if m.get("pages") in (None, ""):
        qs.append(_q(person, "manuscript.pages", f"{kind} 원고의 인정 매수(면수)를 알려주세요."))
    if m.get("meets_spec") is None:
        qs.append(_q(person, "manuscript.meets_spec", "원고가 기준표 규격(A4·12pt·행간 160·여백)을 충족하는지 알려주세요."))
    if qs:
        return {"pay": None, "text": "", "questions": qs, "warnings": warns}
    if m["meets_spec"] is False:
        warns.append("원고 규격 미충족: 원고료 0원 처리")
        return {"pay": 0, "text": "0원\n규격 미충족", "questions": [], "warnings": warns}
    r = rates["원고료"][kind]
    pages = _fr(m["pages"])
    if kind == "도서":
        pay = min(r["단가"] * pages, r["지급한도액"])
        calc = f"도서 {r['단가']:,}원×{_fmt_h(pages)}{r['단위']}"
    else:
        cap = hours * r["시간당한도"]
        if pages >= cap:
            calc = f"{kind} {r['단가']:,}원×{r['시간당한도']}매×{_fmt_h(hours)}시간"
        else:
            calc = f"{kind} {r['단가']:,}원×{_fmt_h(pages)}매"
        pay = r["단가"] * min(pages, cap)
    note = ""
    ratio = m.get("revision_ratio")
    if ratio is not None:
        pct = _fr(ratio)
        for z in rates["재활용규칙"]["구간"]:
            if ("미만" in z and pct < z["미만"]) or ("이하" in z and pct <= z["이하"]) or ("초과" in z and pct > z["초과"]):
                pay = pay * _fr(z["비율"])
                note = f"\n※ 기존 원고 재활용(수정 {_fmt_h(pct)}%) {z['문구']}"
                break
    pay = _round(pay)
    return {"pay": pay, "text": f"{pay:,}원\n{calc}{note}", "questions": [], "warnings": warns}


# ---------- 컨설팅·위원회 ----------
def _day_hours(person, qs):
    out = []
    for d, ss in _by_date(person.get("sessions") or []):
        hs = [_duration_h(s) for s in ss]
        if any(h is None for h in hs):
            qs.append(_q(person, "sessions", f"{_fmt_date(d)} 시작·종료 시각 또는 인정시간이 없습니다."))
            continue
        out.append((d, hs))
    return out


def calc_consulting(person, rates):
    """회차마다 기본, 회차가 3시간을 넘으면 초과 1회(1일 1회 한정)."""
    qs = []
    cat = person.get("category")
    if cat not in CAT_CONSULT:
        qs.append(_q(person, "category", "컨설팅 대상 구분(교수·전문가 / 일반인 / 공무원)을 알려주세요.",
                     [f"{k}: 기본 {rates['컨설팅'][k]['기본']:,}원 / 초과 {rates['컨설팅'][k]['초과']:,}원" for k in CAT_CONSULT]))
        return {"pay": None, "text": "", "questions": qs, "count": 0}
    if not person.get("sessions"):
        qs.append(_q(person, "sessions", "컨설팅 일시 정보가 없습니다."))
        return {"pay": None, "text": "", "questions": qs, "count": 0}
    base, extra = rates["컨설팅"][cat]["기본"], rates["컨설팅"][cat]["초과"]
    limit = rates["컨설팅"]["기본시간"]
    days = _day_hours(person, qs)
    if qs:
        return {"pay": None, "text": "", "questions": qs, "count": 0}
    n = sum(len(hs) for _, hs in days)
    n_extra = sum(1 for _, hs in days if any(h > limit for h in hs))
    pay = base * n + extra * n_extra
    lines = [f"{pay:,}원", f"지도(컨설팅): 기본 {base:,}원×{n}회"]
    if n_extra:
        lines.append(f"+ 초과 {extra:,}원×{n_extra}회")
    return {"pay": pay, "text": "\n".join(lines), "questions": [], "count": n}


def calc_committee(person, rates):
    """위원회 참석수당: 일당 기본 100,000, 하루 2시간 이상이면 초과 50,000(1일 1회)."""
    qs = []
    if not person.get("sessions"):
        qs.append(_q(person, "sessions", "회의 일시 정보가 없습니다."))
        return {"pay": None, "text": "", "questions": qs, "count": 0}
    c = rates["위원회"]
    days = _day_hours(person, qs)
    if qs:
        return {"pay": None, "text": "", "questions": qs, "count": 0}
    n_extra = sum(1 for _, hs in days if sum(hs, Fraction(0)) >= c["초과_기준시간"])
    pay = c["기본"] * len(days) + c["초과"] * n_extra
    lines = [f"{pay:,}원", f"위원회 참석수당: 기본 {c['기본']:,}원×{len(days)}일"]
    if n_extra:
        lines.append(f"+ 초과 {c['초과']:,}원×{n_extra}회")
    return {"pay": pay, "text": "\n".join(lines), "questions": [], "count": len(days)}


# ---------- 사람 1명 ----------
def calc_person(person, kind, rates):
    qs, warns = [], []
    if kind == "instructor":
        pay = calc_instructor(person, rates)
        man = calc_manuscript(person, rates, pay["hours"]) if pay["pay"] is not None else {"pay": 0, "text": "0원\n", "questions": [], "warnings": []}
    else:
        pay = calc_consulting(person, rates) if kind == "consulting" else calc_committee(person, rates)
        man = {"pay": 0, "text": "0원\n", "questions": [], "warnings": []}
    qs += pay["questions"] + man["questions"]
    warns += man.get("warnings", [])
    inc = person.get("income_type")
    if inc not in ("기타", "사업"):
        qs.append(_q(person, "income_type", "소득 구분(기타소득 / 사업소득)을 알려주세요.", ["기타", "사업"]))
    travel = person.get("travel") or {}
    t_amt = int(travel.get("amount") or 0)
    t_text = f"{t_amt:,}원\n{travel.get('text', '')}"
    sessions = person.get("sessions") or []
    if sessions and kind == "instructor":
        b = _sessions_text(sessions, "강의 일시", "hours")
    elif sessions:
        b = _sessions_text(sessions, "컨설팅 일시" if kind == "consulting" else "회의 일시", "count")
    else:
        b = ""
    res = {
        "name": person.get("name", ""), "org": person.get("org", ""), "position": person.get("position", ""),
        "account": person.get("account", ""), "income_type": inc, "category": person.get("category"),
        "b_text": b, "g_text": pay["text"], "h_text": man["text"], "i_text": t_text,
        "note": person.get("note", ""), "warnings": warns,
        "questions": qs, "complete": not qs,
    }
    if qs:
        return res
    total = pay["pay"] + man["pay"] + t_amt
    inc_tax, loc_tax = calc_tax(total, pay["pay"] + man["pay"], inc, rates)
    travel_terms = (travel.get("parts") or [t_amt]) if t_amt else []
    terms = [pay["pay"], man["pay"]] + [int(p) for p in travel_terms]
    terms = [t for t in terms if t] or [0]
    res.update({
        "instructor_pay": pay["pay"], "manuscript_pay": man["pay"], "travel": t_amt, "total": total,
        "j_value": total,
        "j_formula": ("=" + "+".join(str(t) for t in terms)) if len(terms) > 1 else total,
        "income_tax": inc_tax, "local_tax": loc_tax, "deduction": inc_tax + loc_tax,
        "net": total - inc_tax - loc_tax,
    })
    return res


# ---------- 물품·경비 ----------
def calc_purchase(purchase):
    items = []
    for it in purchase.get("items", []):
        items.append({"name": it.get("name", ""), "amount": int(it.get("qty", 0)) * int(it.get("unit_price", 0))})
    return {"items": items, "total": sum(i["amount"] for i in items)}


def calc_expense(expense):
    lines, qs = [], []
    for ln in expense.get("lines", []):
        factors = ln.get("factors") or []
        amt = int(ln.get("unit_price", 0))
        for f in factors:
            amt *= int(f)
        if ln.get("amount") not in (None, "") and int(ln["amount"]) != amt:
            qs.append({"person": "", "field": f"expense.{ln.get('label', '')}",
                       "message": f"{ln.get('label', '')}: 입력 금액 {int(ln['amount']):,}원과 산출 금액 {amt:,}원이 다릅니다."})
        ft = ln.get("factor_text") or " × ".join(str(f) for f in factors)
        text = f"{ln.get('label', '')}: {int(ln.get('unit_price', 0)):,}원" + (f" × {ft}" if factors else "") + f" = {amt:,}원" if factors \
            else f"{ln.get('label', '')}: {amt:,}원"
        lines.append({"label": ln.get("label", ""), "amount": amt, "text": text})
    return {"lines": lines, "total": sum(l["amount"] for l in lines)}, qs


# ---------- 사례 전체 ----------
def compute_case(case, rates=None):
    """case['computed']를 채워 case를 돌려준다."""
    rates = rates or load_rates()
    comp = {"total": None, "total_line": "", "people": [], "questions": []}
    totals = {}
    if case.get("allowance"):
        al = case["allowance"]
        kind = al.get("kind", "instructor")
        comp["people"] = [calc_person(p, kind, rates) for p in al.get("people", [])]
        for p in comp["people"]:
            comp["questions"] += p["questions"]
        if comp["people"] and all(p["complete"] for p in comp["people"]):
            totals["allowance"] = sum(p["total"] for p in comp["people"])
            comp["allowance"] = {k: sum(p[k] for p in comp["people"])
                                 for k in ("instructor_pay", "manuscript_pay", "travel", "total", "income_tax", "local_tax", "deduction", "net")}
    if case.get("purchase"):
        comp["purchase"] = calc_purchase(case["purchase"])
        totals["purchase"] = comp["purchase"]["total"]
    if case.get("expense"):
        comp["expense"], qs = calc_expense(case["expense"])
        comp["questions"] += qs
        totals["expense"] = comp["expense"]["total"]
    if not comp["questions"]:
        for key in ("allowance", "expense", "purchase"):
            if key in totals:
                comp["total"] = totals[key]
                comp["total_line"] = format_amount_line(totals[key])
                break
    case["computed"] = comp
    return case


def main(argv):
    if len(argv) != 2:
        print("사용법: python amount.py case.json")
        return 2
    with open(argv[1], encoding="utf-8") as f:
        case = json.load(f)
    compute_case(case)
    with open(argv[1], "w", encoding="utf-8") as f:
        json.dump(case, f, ensure_ascii=False, indent=2)
    comp = case["computed"]
    print("총액:", comp["total_line"] or "(계산 보류)")
    for q in comp["questions"]:
        print(f"질문[{q['person']}/{q['field']}]: {q['message']}")
    return 1 if comp["questions"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
