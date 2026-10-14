#!/usr/bin/env python3
"""HWPX 기안문 점검. 사용: python hwpx_check.py out.hwpx [case.json]

(a) zip 구조·XML·스타일 참조 검사 (b) 텍스트 추출 (c) case.json 있으면 render_lines와 줄 단위 비교, 단계별 왼쪽 여백·내어쓰기, 굴림체 12pt 검사
실패가 하나라도 있으면 종료코드 1.
"""
import json
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_hwpx import BLANK, FONT_FACE, LEVELS, line_text, render_header, render_lines  # noqa: E402

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
SPACE_TAGS = {f"{{{HP}}}{n}" for n in ("tab", "nbSpace", "fwSpace")}
REQUIRED = ["Contents/content.hpf", "Contents/header.xml", "Contents/section0.xml"]


def extract_paragraphs(zf):
    """section0.xml의 문단별 텍스트(문단 순서 유지)."""
    root = etree.fromstring(zf.read("Contents/section0.xml"))
    return ["".join(_t_text(t) for t in p.iter(f"{{{HP}}}t")) for p in root.iter(f"{{{HP}}}p")]


def _t_text(t):
    """hp:t 텍스트. 탭·묶음 빈칸(nbSpace)·고정폭 빈칸(fwSpace)은 공백 한 칸으로 본다."""
    out = t.text or ""
    for c in t:
        out += (" " if c.tag in SPACE_TAGS else "") + (c.tail or "")
    return out


def check_formatting(zf, draft, texts_paras, results):
    """본문 줄의 문단 모양(왼쪽 여백·내어쓰기)과 글꼴(굴림체)·크기(12pt) 검사."""
    ns = {"hh": "http://www.hancom.co.kr/hwpml/2011/head", "hc": "http://www.hancom.co.kr/hwpml/2011/core",
          "hp": HP}
    head = etree.fromstring(zf.read("Contents/header.xml"))
    sec = etree.fromstring(zf.read("Contents/section0.xml"))

    margins = {}
    for pr in head.iterfind(".//hh:paraPr", ns):
        m = pr.find(".//hp:case//hh:margin", ns)
        if m is None:
            m = pr.find(".//hh:margin", ns)
        margins[pr.get("id")] = (int(m.find("hc:left", ns).get("value")),
                                 int(m.find("hc:intent", ns).get("value")))

    # 문단(텍스트 있는 것만) -> (paraPrIDRef, 첫 run charPrIDRef)
    allp = [(p.get("paraPrIDRef"), p.find("hp:run", ns).get("charPrIDRef"), t)
            for p, t in zip(sec.iter(f"{{{HP}}}p"), texts_paras)]
    title_idx = max(i for i, a in enumerate(allp) if a[2] == render_header(draft)[-1])
    body = allp[title_idx + 2:]  # 제목 뒤 빈 줄 1개 건너뜀
    lines = render_lines(draft)
    bad = []
    for (level, text), (pid, _, actual) in zip(lines, body):
        want = (0, 0) if level == BLANK else LEVELS[level][1:]
        if margins.get(pid) != want:
            bad.append(f"{text[:15]!r}: 기대 {level}{want} / 실제 {margins.get(pid)}")
    # 에듀파인 붙여넣기에서 탭·특수 빈칸은 깨지므로 간격은 일반 공백만 허용
    special = sorted({e.tag.split("}")[1] for e in sec.iter() if e.tag in SPACE_TAGS})
    results.append(("간격은 일반 공백만(탭·특수 빈칸 없음)", not special, f"발견: {special}" if special else ""))
    blank_ok = [line_text(level, t) for level, t in lines] == [a[2] for a in body]
    results.append(("빈 줄 위치(1. 묶음 뒤·붙임 앞)·줄 수·줄 앞 공백 일치", blank_ok, ""))
    results.append(("단계별 왼쪽 여백·내어쓰기 일치", not bad and len(lines) == len(body), " | ".join(bad)))

    # 글꼴: 모든 fontface의 font 이름 / 본문 charPr 높이
    faces = {f.get("face") for f in head.iterfind(".//hh:font", ns)}
    results.append((f"글꼴 {FONT_FACE}", faces == {FONT_FACE}, f"발견: {sorted(faces)}"))
    heights = {c.get("id"): int(c.get("height")) for c in head.iterfind(".//hh:charPr", ns)}
    sizes = {heights[c] for _, c, t in body if t.strip()}
    results.append(("본문 글자 크기 12pt", sizes == {1200}, f"발견: {sorted(sizes)}"))
    head_sizes = {heights[c] for _, c, t in allp[:title_idx + 1]
                  if t.strip() and t != render_header(draft)[0]}
    results.append(("머리 줄 글자 크기 12pt(기관명 제외)", head_sizes == {1200}, f"발견: {sorted(head_sizes)}"))


def check_structure(zf, results):
    def ok(name, cond, detail=""):
        results.append((name, bool(cond), detail))

    names = zf.namelist()
    ok("mimetype 첫 엔트리", names and names[0] == "mimetype")
    if "mimetype" in names:
        ok("mimetype 무압축", zf.getinfo("mimetype").compress_type == zipfile.ZIP_STORED)
        ok("mimetype 값", zf.read("mimetype").decode().strip() == "application/hwp+zip")
    for r in REQUIRED:
        ok(f"{r} 존재", r in names)

    parsed = {}
    for n in names:
        if n.endswith((".xml", ".hpf")):
            try:
                parsed[n] = etree.fromstring(zf.read(n))
                ok(f"XML 파싱 {n}", True)
            except etree.XMLSyntaxError as e:
                ok(f"XML 파싱 {n}", False, str(e))

    if "Contents/header.xml" in parsed and "Contents/section0.xml" in parsed:
        head = zf.read("Contents/header.xml").decode("utf-8")
        sec = zf.read("Contents/section0.xml").decode("utf-8")
        for attr, tag in [("charPrIDRef", "charPr"), ("paraPrIDRef", "paraPr"), ("styleIDRef", "style")]:
            defined = set(re.findall(rf'<hh:{tag} id="(\d+)"', head))
            used = set(re.findall(rf'{attr}="(\d+)"', sec))
            missing = sorted(used - defined, key=int)
            ok(f"{tag} 참조 id가 header에 존재", not missing, f"없는 id: {missing}" if missing else "")


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("사용: python hwpx_check.py out.hwpx [case.json]")
    path = sys.argv[1]
    results = []
    with zipfile.ZipFile(path) as zf:
        check_structure(zf, results)
        paras = extract_paragraphs(zf)

    texts = [p for p in paras if p.strip()]
    print("== 추출 텍스트 ==")
    for t in texts:
        print(t)
    print()

    if len(sys.argv) == 3:
        draft = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))["draft"]
        expected = render_header(draft) + [line_text(lv, t) for lv, t in render_lines(draft) if t]
        same = texts == expected
        detail = ""
        if not same:
            diff = [f"{i + 1}줄: 기대 {e!r} / 실제 {a!r}"
                    for i, (e, a) in enumerate(zip(expected, texts)) if e != a]
            if len(expected) != len(texts):
                diff.append(f"줄 수 다름: 기대 {len(expected)} / 실제 {len(texts)}")
            detail = " | ".join(diff)
        results.append(("render_lines와 줄 단위 일치", same, detail))
        with zipfile.ZipFile(path) as zf:
            check_formatting(zf, draft, paras, results)

    print("== 점검 결과 ==")
    for name, passed, detail in results:
        print(f"[{'통과' if passed else '실패'}] {name}" + (f" - {detail}" if detail else ""))
    failed = [r for r in results if not r[1]]
    print(f"\n통과 {len(results) - len(failed)} / 실패 {len(failed)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
