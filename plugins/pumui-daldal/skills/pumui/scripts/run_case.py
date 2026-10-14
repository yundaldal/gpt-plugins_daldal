"""Run the complete local pipeline without saving the submitted case JSON."""
import json
import os
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
import amount  # noqa: E402
import build_budget_upload  # noqa: E402
import build_hwpx  # noqa: E402
import build_xlsx  # noqa: E402
import harness  # noqa: E402
import readiness  # noqa: E402
import validate_case  # noqa: E402
from assemble import fill_draft_amounts  # noqa: E402

OUTPUT_ALLOWLIST = {
    "기안문.hwpx", "수당 지급 내역.xlsx", "물품 구입 목록.xlsx",
    "예산연결 업로드양식 결과.xlsx", "준비점검표.md", "점검결과.md",
}


def case_folder_name(case):
    title = re.sub(r"^\[품의\]\s*", "", case["draft"]["title"])
    title = re.sub(r'[\\/:*?"<>|\r\n]', "", title).strip().rstrip(".")
    return f"{title[:60].rstrip()}_{date.today():%Y%m%d}"


def unique_dir(root, name):
    path = Path(root) / name
    n = 2
    while path.exists():
        path = Path(root) / f"{name}_{n}"
        n += 1
    path.mkdir(parents=True)
    return path


def main(argv):
    if len(argv) not in (3, 4):
        print("사용법: python run_case.py case.json output_root [input_dir]")
        return 2
    case_path, output_root = Path(argv[1]), Path(argv[2])
    input_dir = argv[3] if len(argv) == 4 else None
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("[오류] case.json을 읽을 수 없거나 JSON 형식이 아닙니다.")
        return 2

    issues = validate_case.validate(case)
    if issues:
        print("[중단] 필수 입력을 확인해 주세요.")
        for issue in issues:
            print(f"  {issue['field']}: {issue['message']}")
        return 2

    # Normalize the title before readiness, HWPX creation, and output naming
    # so every entry point gets the same official [품의] prefix.
    case["draft"]["title"] = build_hwpx.normalized_title(case["draft"].get("title"))

    amount.compute_case(case)
    comp = case["computed"]
    if comp["questions"]:
        print("[중단] 계산에 필요한 정보를 더 확인해 주세요.")
        for q in comp["questions"]:
            print(f"  {q['field']}: {q['message']}")
        return 2
    print(f"[계산] 총액 {comp['total_line']}")

    case = fill_draft_amounts(case)
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pumui-work-") as temp_root:
        work = Path(temp_root)
        jobs = {"기안문.hwpx": lambda: build_hwpx.build(case["draft"], work / "기안문.hwpx")}
        if case.get("allowance"):
            jobs["수당 지급 내역.xlsx"] = lambda: build_xlsx.build_allowance(case, work / "수당 지급 내역.xlsx")
        if case.get("purchase"):
            jobs["물품 구입 목록.xlsx"] = lambda: build_xlsx.build_purchase(case, work / "물품 구입 목록.xlsx")
        if build_budget_upload.budget_rows(case) is not None:
            jobs[harness.BUDGET_NAME] = lambda: build_budget_upload.build(case, work / harness.BUDGET_NAME)
        with ThreadPoolExecutor() as pool:
            futures = [(name, pool.submit(fn)) for name, fn in jobs.items()]
            for name, future in futures:
                future.result()
                print(f"[생성] {name}")

        md, summary = readiness.build_report(case, readiness.list_input_files(input_dir))
        (work / "준비점검표.md").write_text(md, encoding="utf-8")
        print(f"[준비점검표] 필수 본문 누락 {summary['missing_body']}건")

        results = harness.run_checks(case, str(work))
        failed = harness.write_report(case, results, work / "점검결과.md")
        print(f"[자동 점검] 통과 {len(results) - len(failed)} / 실패 {len(failed)}")

        present = {path.name for path in work.iterdir() if path.is_file()}
        if not present <= OUTPUT_ALLOWLIST:
            print("[오류] 임시 산출물에 허용되지 않은 파일이 있어 결과 저장을 중단했습니다.")
            return 1
        destination = unique_dir(output_root, case_folder_name(case))
        for name in present:
            shutil.copy2(work / name, destination / name)

    print(f"[완료] 결과 폴더: {destination.name} (case.json은 저장하지 않았습니다.)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
