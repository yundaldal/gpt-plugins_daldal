"""Run the complete local pipeline without saving the submitted case JSON."""
import json
import hashlib
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
import document_adapter  # noqa: E402
import readiness  # noqa: E402
import validate_case  # noqa: E402
import questions  # noqa: E402
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


def compute_revision(case_path, input_dir=None):
    digest = hashlib.sha256()
    case_path = Path(case_path).resolve(strict=True)
    case_bytes = case_path.read_bytes()
    digest.update(b"case\0")
    case_identity = str(case_path).casefold().encode("utf-8")
    digest.update(len(case_identity).to_bytes(8, "big"))
    digest.update(case_identity)
    digest.update(len(case_bytes).to_bytes(8, "big"))
    digest.update(case_bytes)
    if input_dir:
        input_root = Path(input_dir)
        if not input_root.is_dir():
            raise ValueError("input_dir must be an existing directory")
        digest.update(b"input\0")
        for path in sorted(input_root.rglob("*"), key=lambda item: item.relative_to(input_root).as_posix()):
            if path.is_file():
                relative = path.relative_to(input_root).as_posix().encode("utf-8")
                contents = path.read_bytes()
                digest.update(len(relative).to_bytes(8, "big"))
                digest.update(relative)
                digest.update(len(contents).to_bytes(8, "big"))
                digest.update(contents)
    return digest.hexdigest()


def _inspected_input(value, input_dir):
    if not isinstance(value, str) or not value.strip() or input_dir is None:
        return False
    candidate = Path(value.strip())
    if candidate.is_absolute():
        return False
    try:
        root = Path(input_dir).resolve(strict=True)
        path = (root / candidate).resolve(strict=True)
        path.relative_to(root)
        if not path.is_file():
            return False
        inspected = document_adapter.inspect(path)
    except (OSError, RuntimeError, ValueError):
        return False
    return inspected.get("status") == "ok" and bool(inspected.get("blocks"))


def validate_resolution_actions(state, input_dir=None):
    """Require concrete, inspected input files for add/replace/review branches."""
    if not isinstance(state, dict) or not isinstance(state.get("questions"), dict):
        return ["question states are missing"]
    errors = []
    required_file_actions = {
        ("intake.readiness", "add"),
        ("source.unreadable", "replace"),
        ("rate.confirm", "review"),
    }
    for question_id, entry in state["questions"].items():
        if not isinstance(question_id, str) or not isinstance(entry, dict):
            continue
        answer = entry.get("answer")
        if not isinstance(answer, dict) or answer.get("mode") != "option":
            continue
        action = (question_id.split("::", 1)[0], answer.get("value"))
        if action in required_file_actions and entry.get("status") in {"answered", "deferred"}:
            if not _inspected_input(answer.get("custom_value"), input_dir):
                errors.append(f"{question_id} action requires a readable file inside input_dir")
    return errors


def main(argv):
    state_only = len(argv) == 5 and argv[3] == "--question-state"
    state_with_input = len(argv) == 6 and argv[4] == "--question-state"
    if not state_only and not state_with_input:
        print("사용법: python run_case.py case.json output_root [input_dir] [--question-state state.json]")
        return 2
    case_path, output_root = Path(argv[1]), Path(argv[2])
    input_dir = argv[3] if len(argv) in (4, 6) and not state_only else None
    state_path = Path(argv[4] if state_only else argv[5]) if state_only or state_with_input else None
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("[오류] case.json을 읽을 수 없거나 JSON 형식이 아닙니다.")
        return 2
    try:
        current_revision = compute_revision(case_path, input_dir)
    except (OSError, ValueError):
        print("[중단] 입력 자료를 읽거나 revision을 계산할 수 없습니다.")
        return 2

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("[중단] question-state JSON을 읽을 수 없습니다.")
        return 2
    errors = questions.validate_state(state)
    if errors:
        print("[중단] 질문 응답 상태를 확인해 주세요.")
        for error in errors:
            print(f"  {error}")
        return 2
    expected_ids = [q["id"] for q in questions.required_questions(state.get("context", {}))]
    if set(expected_ids) != set(state.get("required_question_ids", [])):
        print("[중단] 질문 상태의 적용 대상이 현재 intake 사실과 일치하지 않습니다.")
        return 2
    if state.get("source_revision") != current_revision:
        state = questions.refresh_for_revision(state, current_revision)
        stale_ids = [
            qid for qid in state.get("required_question_ids", [])
            if isinstance(state.get("questions", {}).get(qid), dict)
            and state["questions"][qid].get("status") == "stale"
        ]
        print("[중단] 자료 또는 case가 바뀌어 확인 답변을 다시 받아야 합니다.")
        for qid in stale_ids:
            print(f"  {qid}")
        return 2
    binding_errors = questions.validate_case_bindings(case, state)
    if binding_errors:
        print("[중단] 확인 질문의 필드 연결을 현재 case와 대조해 주세요.")
        for error in binding_errors:
            print(f"  {error}")
        return 2
    action_errors = validate_resolution_actions(state, input_dir)
    if action_errors:
        print("[중단] 선택한 자료 조치의 입력 파일을 확인해 주세요.")
        for error in action_errors:
            print(f"  {error}")
        return 2
    state = questions.refresh_for_revision(state, current_revision)
    pending = questions.pending_required(state.get("required_question_ids", []), state)
    if pending:
        print("[중단] 필수 확인 질문에 답해 주세요.")
        for qid in pending:
            print(f"  {qid}")
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

    if failed:
        print(f"[점검 실패] 자동 점검 {len(failed)}건이 통과하지 못했습니다. 결과 폴더: {destination.name} (case.json은 저장하지 않았습니다.)")
        return 1
    print(f"[완료] 결과 폴더: {destination.name} (case.json은 저장하지 않았습니다.)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
