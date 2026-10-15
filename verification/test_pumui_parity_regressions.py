"""Synthetic regressions for the 0.1.9 parity repair."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "pumui-daldal" / "skills" / "pumui" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import amount  # noqa: E402
import build_budget_upload  # noqa: E402
import harness  # noqa: E402
import hwpx_check  # noqa: E402
import readiness  # noqa: E402
import run_case  # noqa: E402
import validate_case  # noqa: E402


def synthetic_c3(*, related=None, with_purchase=True):
    draft = {
        "organization": "합성 교육기관",
        "title": "[품의] 합성 운영 경비",
        "purpose": "합성 테스트용 운영 경비를 지출하고자 합니다.",
        "items": [
            {"label": "기간", "value": "2026. 10. 1.(목)"},
            {"label": "장소", "value": "합성 장소"},
            {"label": "대상", "value": "합성 참가자"},
            {
                "label": "소요 금액",
                "value": "금6,000원(금육천원)",
                "subs": ["항목별 1) 합성 운영비: 2,000원 × 3 = 6,000원"],
            },
        ],
        "attachments": [{"name": "일반지출품의서", "count": "1부"}],
    }
    if related is not None:
        draft["related"] = related
    case = {
        "type": "C3",
        "department": "합성 운영부",
        "school_level": "합성 학교급 설정값",
        "draft": draft,
        "expense": {
            "lines": [
                {
                    "label": "합성 운영비",
                    "unit_price": 2000,
                    "factors": [3],
                    "amount": 6000,
                }
            ]
        },
    }
    if with_purchase:
        case["purchase"] = {
            "sheet_title": "합성 부속 물품 목록",
            "org": "합성 운영부",
            "items": [{"name": "합성 준비 물품", "qty": 3, "unit_price": 2000}],
        }
    return case


def synthetic_a4_committee():
    case = synthetic_c3(related=[], with_purchase=False)
    case["type"] = "A4"
    case.pop("expense")
    case.pop("school_level")
    type_config = next(
        section["A4"]
        for section in validate_case._load_config().values()
        if isinstance(section, dict) and "A4" in section
    )
    body_specs = next(
        value
        for value in type_config.values()
        if isinstance(value, list)
        and value
        and isinstance(value[0], dict)
        and "label" in value[0]
        and "required" in value[0]
    )
    case["draft"]["items"] = [
        {"label": spec["label"], "value": "SYNTHETIC_REQUIRED_VALUE"}
        for spec in body_specs
        if spec.get("required")
    ]
    case["draft"]["attachments"] = [{"name": "SYNTHETIC_COMMITTEE_ATTACHMENT", "count": "1"}]
    rates = validate_case._load_rates()
    case["rate_confirmation"] = {
        "confirmed": True,
        "year": rates.get("프로필", {}).get("연도"),
        "organization": case["draft"]["organization"],
    }
    case["allowance"] = {
        "kind": "committee",
        "sheet_title": "SYNTHETIC_COMMITTEE_ALLOWANCE",
        "people": [
            {
                "name": "SYNTHETIC_PERSON",
                "org": "SYNTHETIC_ORG",
                "position": "SYNTHETIC_POSITION",
                "income_type": "기타",
                "category": "SYNTHETIC_COMMITTEE_ROLE",
                "sessions": [{"date": "2026-10-01", "start": "09:00", "end": "11:00"}],
                "travel": {"amount": 0},
            }
        ],
    }
    return case


class PumuiParityRegressionTests(unittest.TestCase):
    def test_hwpx_recovery_policy_keeps_hwpx_default_and_requires_txt_consent(self):
        skill = (ROOT / "plugins" / "pumui-daldal" / "skills" / "pumui" / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "plugins" / "pumui-daldal" / "README.md").read_text(encoding="utf-8")
        manifest = json.loads((ROOT / "plugins" / "pumui-daldal" / "plugin.json").read_text(encoding="utf-8"))
        prompt = manifest["extensions"]["com.openai"]["interface"]["defaultPrompt"]

        for document in (skill, readme):
            self.assertIn("기본 산출물", document)
            self.assertIn("기안문.hwpx", document)
            self.assertIn("먼저", document)
            self.assertIn("Python/Data Analysis", document)
            self.assertIn("셸", document)
            self.assertIn("공개 플러그인 ZIP", document)
            self.assertIn("HWPX 파일을 생성하지 못했습니다. 일반 텍스트(.txt) 초안을 만들어도 괜찮을까요?", document)
            self.assertIn("동의하기 전에는", document)
            self.assertIn("`.txt` 파일을 만들지", document)
            self.assertIn("본문 미리보기", document)
            self.assertIn("미완료", document)

        self.assertEqual(manifest["extensions"]["com.openai"]["interface"]["capabilities"], ["Interactive"])
        self.assertEqual(manifest["version"], "0.1.10")
        self.assertIn("기안문.hwpx를 기본으로 먼저 시도", prompt)
        self.assertIn("일반 텍스트(.txt) 초안을 만들어도 괜찮을까요?", prompt)
        self.assertIn("명시적으로 동의하기 전에는 .txt를 만들지", prompt)

    def test_A4_committee_allowance_validates_without_consulting_only_rules(self):
        case = synthetic_a4_committee()
        issues = validate_case.validate(case)

        self.assertEqual(issues, [])
        amount.compute_case(case)
        self.assertEqual(case["computed"]["questions"], [])
        self.assertGreater(case["computed"]["total"], 0)

    def test_C3_mixed_case_validates_and_keeps_school_level_configurable(self):
        case = synthetic_c3(related=[])

        issues = validate_case.validate(case)

        self.assertNotIn("allowance/purchase/expense", {i["field"] for i in issues})
        self.assertNotIn("purchase.items", {i["field"] for i in issues})
        self.assertNotIn("school_level", {i["field"] for i in issues})

    def test_explicit_empty_related_list_is_valid_but_omission_is_not(self):
        explicit_case = synthetic_c3(related=[], with_purchase=False)
        explicit_empty = validate_case.validate(explicit_case)
        omitted = validate_case.validate(synthetic_c3(related=None, with_purchase=False))

        self.assertNotIn("draft.related", {i["field"] for i in explicit_empty})
        self.assertIn("draft.related", {i["field"] for i in omitted})
        report, summary = readiness.build_report(explicit_case, [])
        self.assertIn("관련 문서 | 필수 | ➖ 해당 없음", report)
        self.assertEqual(summary["missing_body"], 0)

    def test_readiness_report_summarizes_input_file_types_without_names(self):
        private_names = ["PRIVATE_DUMMY_7741.xlsx", "PRIVATE_DUMMY_7742.pdf"]

        report, _summary = readiness.build_report(synthetic_c3(related=[]), private_names)

        for private_name in private_names:
            self.assertNotIn(private_name, report)
        self.assertIn("XLSX", report)
        self.assertIn("PDF", report)
        self.assertIn("2", report)

    def test_C3_purchase_annex_does_not_change_expense_total_or_budget_rows(self):
        case = synthetic_c3(related=[])
        amount.compute_case(case)

        self.assertEqual(case["computed"]["total"], 6000)
        self.assertEqual(
            build_budget_upload.budget_rows(case),
            [("합성 준비 물품", 3, 2000)],
        )
        self.assertEqual(
            harness.expected_budget_rows(case),
            [("합성 준비 물품", 3, 2000)],
        )

    def test_C3_mixed_total_mismatch_requires_user_reconciliation(self):
        case = synthetic_c3(related=[])
        case["purchase"]["items"][0]["qty"] = 1

        issues = validate_case.validate(case)

        mismatch = next((i for i in issues if i["field"] == "purchase.total"), None)
        self.assertIsNotNone(mismatch)
        self.assertIn("합계", mismatch["message"])

    def test_harness_tax_uses_its_own_constants(self):
        with patch.object(harness, "RATES_PATH", "Z:/synthetic-no-rate-file.json"):
            self.assertEqual(harness.calc_tax("기타", 125001, 0), (10000, 1000))
            self.assertEqual(harness.calc_tax("사업", 50000, 100001), (3000, 300))

    def test_failure_report_shows_safe_cell_id_and_redacts_dynamic_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            failed = harness.write_report(
                synthetic_c3(related=[]),
                [("예산연결 업로드", False, "cell:D4; value=PRIVATE_DUMMY_7741")],
                report,
            )
            rendered = report.read_text(encoding="utf-8")

        self.assertEqual(len(failed), 1)
        self.assertIn("D4", rendered)
        self.assertNotIn("PRIVATE_DUMMY_7741", rendered)

    def test_hwpx_failure_diagnostics_keep_safe_check_and_line_ids_only(self):
        failure = "[\uC2E4\uD328]"
        stdout = "\n".join(
            [
                f"{failure} render_lines\uC640 \uC785\uB825 \uBB38\uC7A5 \uC77C\uCE58 - line:4",
                f"{failure} \uB2E8\uACC4\uBCC4 \uC67C\uCABD \uC5EC\uBC31\u00B7\uB0B4\uC5B4\uC4F0\uAE30 \uC77C\uCE58 - line:8",
                f"{failure} render_lines\uC640 \uC785\uB825 \uBB38\uC7A5 \uC77C\uCE58 - line:9 expected=PRIVATE_DUMMY_8051",
            ]
        )
        process = SimpleNamespace(returncode=1, stdout=stdout, stderr="PRIVATE_DUMMY_8053")

        with patch.object(harness.subprocess, "run", return_value=process):
            _name, passed, detail = harness.check_hwpx(synthetic_c3(related=[]), "SYNTHETIC_TEST.hwpx")[0]

        self.assertFalse(passed)
        self.assertIn("field:hwpx.render_text", detail)
        self.assertIn("field:hwpx.paragraph_layout", detail)
        self.assertIn("field:hwpx.line[4]", detail)
        self.assertIn("field:hwpx.line[8]", detail)
        self.assertNotIn("field:hwpx.line[9]", detail)
        self.assertNotIn("PRIVATE_DUMMY_805", detail)

    def test_hwpx_checker_line_diagnostics_never_echo_paragraph_values(self):
        identifiers = hwpx_check._line_diff_ids(
            ["PRIVATE_DUMMY_9901", "SYNTHETIC_EXPECTED"],
            ["SYNTHETIC_ACTUAL", "PRIVATE_DUMMY_9902"],
        )

        self.assertEqual(identifiers, ["line:1", "line:2"])
        self.assertNotIn("PRIVATE_DUMMY", " ".join(identifiers))

    def test_run_case_does_not_claim_completion_when_harness_fails(self):
        case = synthetic_c3(related=[], with_purchase=False)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            case_path = tmp_path / "synthetic-case.json"
            case_path.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
            output_root = tmp_path / "output"

            def write_synthetic_artifact(_draft, path):
                Path(path).write_bytes(b"synthetic test artifact")

            def write_synthetic_budget(_case, path):
                Path(path).write_bytes(b"synthetic test spreadsheet")
                return path

            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(run_case.build_hwpx, "build", side_effect=write_synthetic_artifact))
                stack.enter_context(patch.object(run_case.build_budget_upload, "build", side_effect=write_synthetic_budget))
                stack.enter_context(patch.object(run_case.readiness, "build_report", return_value=("합성 점검표", {"missing_body": 0})))
                stack.enter_context(patch.object(run_case.harness, "run_checks", return_value=[("합성 셀 점검", False, "cell:HWPX")]))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    return_code = run_case.main(["run_case.py", str(case_path), str(output_root)])

        self.assertEqual(return_code, 1)
        self.assertIn("[점검 실패]", output.getvalue())
        self.assertNotIn("[완료]", output.getvalue())

    def test_synthetic_C3_full_run_builds_hwpx_and_numeric_excel_totals(self):
        case = synthetic_c3(related=[])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_path = root / "synthetic-case.json"
            case_path.write_text(json.dumps(case, ensure_ascii=False), encoding="utf-8")
            output_root = root / "output"
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                return_code = run_case.main(["run_case.py", str(case_path), str(output_root)])

            self.assertEqual(return_code, 0, output.getvalue())
            result_dir = next(path for path in output_root.iterdir() if path.is_dir())
            hwpx_path = result_dir / harness.HWPX_NAME
            purchase_path = result_dir / "물품 구입 목록.xlsx"
            budget_path = result_dir / harness.BUDGET_NAME
            self.assertTrue(hwpx_path.is_file())
            self.assertTrue(purchase_path.is_file())
            self.assertTrue(budget_path.is_file())

            with zipfile.ZipFile(hwpx_path) as archive:
                hwpx_text = "\n".join(harness.extract_paragraphs(archive))
            self.assertIn("[품의]", hwpx_text)

            purchase_ws = openpyxl.load_workbook(purchase_path, data_only=False).active
            self.assertIsInstance(purchase_ws["G5"].value, (int, float))
            self.assertEqual(purchase_ws["G5"].value, 6000)

            budget_ws = openpyxl.load_workbook(budget_path, data_only=False).active
            self.assertIn(budget_ws["D2"].value, (None, ""))
            self.assertIsInstance(budget_ws["F2"].value, (int, float))
            self.assertEqual(budget_ws["F2"].value, 6000)


if __name__ == "__main__":
    unittest.main()
