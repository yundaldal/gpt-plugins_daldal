import sys
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "pumui-daldal" / "skills" / "pumui" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import questions
import run_case


class QuestionFlowTests(unittest.TestCase):
    def test_catalog_has_explicit_options_and_custom_input(self):
        self.assertEqual(questions.validate_catalog(), [])
        catalog = questions.load_catalog()
        self.assertTrue(catalog["policy"]["every_question_requires_choice_and_custom_input"])
        for question in catalog["questions"]:
            self.assertGreaterEqual(len(question["options"]), 2)
            self.assertIn({"id": "custom", "label": "직접 입력", "value": "custom"}, question["options"])
            self.assertEqual(question["custom_input"]["id"], "custom")

    def test_answered_state_requires_explicit_option_including_direct_input(self):
        valid = {"questions": {"type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "custom", "custom_value": "A4"}}}}
        self.assertEqual(questions.validate_state(valid), [])
        invalid = {"questions": {"type.confirm": {"status": "answered", "answer": "A4"}}}
        self.assertTrue(questions.validate_state(invalid))
        skipped_choice = {"questions": {"type.confirm": {"status": "answered", "answer": {"mode": "custom", "value": "A4"}}}}
        self.assertTrue(questions.validate_state(skipped_choice))
        missing_direct_value = {"questions": {"type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "custom"}}}}
        self.assertTrue(questions.validate_state(missing_direct_value))
        unknown_option = {"questions": {"type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "not-a-choice"}}}}
        self.assertTrue(questions.validate_state(unknown_option))

    def test_pending_required_does_not_reask_answered(self):
        state = {"questions": {"type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "recommended"}}}}
        self.assertEqual(questions.pending_required(["type.confirm", "source.conflict"], state), ["source.conflict"])

    def test_context_selects_only_questions_triggered_by_intake_facts(self):
        ids = [q["id"] for q in questions.required_questions({"source_conflict": True, "travel_unspecified": True})]
        self.assertEqual(ids, ["source.conflict", "travel.present"])

    def test_repeat_counts_do_not_leak_questions_into_unrelated_context(self):
        context = {"case_type": "B1", "question_instances": {"travel.present": {"person": [
            {"index": 0, "field_path": "allowance.people[0].travel.amount", "value": 0},
        ]}}}
        self.assertEqual(questions.required_questions(context), [])
        self.assertTrue(questions.validate_state({"context": context, "required_question_ids": [], "questions": {}}))

    def test_repeated_question_instances_are_independent(self):
        context = {"travel_unspecified": True, "question_instances": {"travel.present": {"person": [
            {"index": 0, "field_path": "allowance.people[0].travel.amount", "value": 0},
            {"index": 1, "field_path": "allowance.people[1].travel.amount", "value": 1200},
        ]}}}
        state = {"context": context, "required_question_ids": ["travel.present::person[0]", "travel.present::person[1]"], "questions": {
            "travel.present::person[0]": {"status": "answered", "answer": {"mode": "option", "value": "none", "binding": {"index": 0, "field_path": "allowance.people[0].travel.amount", "value": 0}}},
            "travel.present::person[1]": {"status": "pending"},
        }}
        self.assertEqual(questions.validate_state(state), [])
        self.assertEqual(questions.pending_required(state["required_question_ids"], state), ["travel.present::person[1]"])

    def test_repeated_session_instances_are_catalogued_and_required(self):
        context = {"extracted_value_needs_confirmation": True, "question_instances": {"field.confirm": {"session": [
            {"index": 0, "field_path": "sessions[0].title", "value": "SYNTHETIC_SOURCE_A", "source_id": "synthetic-a", "source_revision": "r1"},
            {"index": 1, "field_path": "sessions[1].title", "value": "SYNTHETIC_SOURCE_B", "source_id": "synthetic-b", "source_revision": "r1"},
        ]}}}
        state = {"source_revision": "r1", "context": context, "required_question_ids": ["field.confirm::session[0]", "field.confirm::session[1]"], "questions": {
            "field.confirm::session[0]": {"status": "answered", "answer": {"mode": "option", "value": "accept", "binding": {"index": 0, "field_path": "sessions[0].title", "value": "SYNTHETIC_SOURCE_A", "source_id": "synthetic-a", "source_revision": "r1"}}},
            "field.confirm::session[1]": {"status": "answered", "answer": {"mode": "option", "value": "edit", "custom_value": "SYNTHETIC_EDIT", "binding": {"index": 1, "field_path": "sessions[1].title", "value": "SYNTHETIC_EDIT", "source_id": "synthetic-b", "source_revision": "r1"}}},
        }}
        self.assertEqual([q["id"] for q in questions.required_questions(context)], state["required_question_ids"])
        self.assertEqual(questions.validate_state(state), [])
        case = {"sessions": [{"title": "SYNTHETIC_SOURCE_A"}, {"title": "SYNTHETIC_EDIT"}]}
        self.assertEqual(questions.validate_case_bindings(case, state), [])
        case["sessions"][1]["title"] = "SYNTHETIC_UNRELATED_EDIT"
        self.assertTrue(questions.validate_case_bindings(case, state))

    def test_source_conflict_answer_is_bound_to_resolved_case_value(self):
        context = {"source_conflict": True, "question_instances": {"source.conflict": {"session": [
            {"index": 0, "field_path": "sessions[0].title", "value": "SYNTHETIC_LATEST", "source_id": "synthetic-new", "source_revision": "r1"},
        ]}}}
        state = {"source_revision": "r1", "context": context, "required_question_ids": ["source.conflict::session[0]"], "questions": {
            "source.conflict::session[0]": {"status": "answered", "answer": {"mode": "option", "value": "latest", "binding": {"index": 0, "field_path": "sessions[0].title", "value": "SYNTHETIC_LATEST", "source_id": "synthetic-new", "source_revision": "r1"}}},
        }}
        self.assertEqual(questions.validate_state(state), [])
        self.assertEqual(questions.validate_case_bindings({"sessions": [{"title": "SYNTHETIC_LATEST"}]}, state), [])
        self.assertTrue(questions.validate_case_bindings({"sessions": [{"title": "SYNTHETIC_OLD"}]}, state))

    def test_extracted_value_and_conflict_questions_require_source_bindings(self):
        for question_id, fact in (("field.confirm", "extracted_value_needs_confirmation"), ("source.conflict", "source_conflict")):
            with self.subTest(question_id=question_id):
                state = {"context": {fact: True}, "required_question_ids": [question_id], "questions": {question_id: {"status": "pending"}}}
                self.assertTrue(questions.validate_state(state))

    def test_type_and_attachment_choices_must_match_the_case(self):
        type_context = {"type_missing": True, "recommended_type": "A1"}
        type_state = {"context": type_context, "required_question_ids": ["type.confirm"], "questions": {
            "type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "recommended"}},
        }}
        self.assertEqual(questions.validate_case_bindings({"type": "A1"}, type_state), [])
        self.assertTrue(questions.validate_case_bindings({"type": "A2"}, type_state))

        attachment_state = {"context": {"attachment_ambiguous": True}, "required_question_ids": ["attachment.include"], "questions": {
            "attachment.include": {"status": "answered", "answer": {"mode": "option", "value": "use"}},
        }}
        self.assertEqual(questions.validate_case_bindings({"draft": {"attachments": [{"name": "SYNTHETIC", "count": "1부"}]}}, attachment_state), [])
        self.assertTrue(questions.validate_case_bindings({"draft": {"attachments": []}}, attachment_state))
        edited_state = {"context": {"attachment_ambiguous": True}, "required_question_ids": ["attachment.include"], "questions": {
            "attachment.include": {"status": "answered", "answer": {"mode": "option", "value": "edit", "custom_value": '[{"name":"SYNTHETIC","count":"1부"}]'}},
        }}
        self.assertEqual(questions.validate_case_bindings({"draft": {"attachments": [{"name": "SYNTHETIC", "count": "1부"}]}}, edited_state), [])
        edited_state["questions"]["attachment.include"]["answer"]["custom_value"] = "[]"
        self.assertTrue(questions.validate_case_bindings({"draft": {"attachments": [{"name": "SYNTHETIC", "count": "1부"}]}}, edited_state))

    def test_travel_amount_followup_must_equal_bound_case_amount(self):
        context = {"travel_unspecified": True, "question_instances": {"travel.present": {"person": [
            {"index": 0, "field_path": "allowance.people[0].travel.amount", "value": 1200},
        ]}}}
        state = {"context": context, "required_question_ids": ["travel.present::person[0]"], "questions": {
            "travel.present::person[0]": {"status": "answered", "answer": {"mode": "option", "value": "amount", "custom_value": "900", "binding": {"index": 0, "field_path": "allowance.people[0].travel.amount", "value": 1200}}},
        }}
        self.assertTrue(questions.validate_state(state))

    def test_required_ids_must_match_context_and_catalog_scopes(self):
        mismatched = {"required_question_ids": ["type.confirm"], "questions": {}}
        unsupported_instance = {"context": {"type_missing": True}, "required_question_ids": ["type.confirm::person[0]"], "questions": {}}
        self.assertTrue(questions.validate_state(mismatched))
        self.assertTrue(questions.validate_state(unsupported_instance))

    def test_required_choice_followup_and_custom_values_are_validated(self):
        base = {"context": {"type_missing": True}, "required_question_ids": ["type.confirm"], "questions": {
            "type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "choose"}},
        }}
        self.assertTrue(questions.validate_state(base))
        base["questions"]["type.confirm"]["answer"]["custom_value"] = "SYNTHETIC_TYPE"
        self.assertEqual(questions.validate_state(base), [])
        base["questions"]["type.confirm"]["answer"]["custom_value"] = " "
        self.assertTrue(questions.validate_state(base))

    def test_source_revision_marks_old_answers_stale(self):
        state = {"source_revision": "r1", "questions": {"field.confirm": {"status": "answered", "answer": {"mode": "option", "value": "accept"}}}}
        refreshed = questions.refresh_for_revision(state, "r2")
        self.assertEqual(refreshed["questions"]["field.confirm"]["status"], "stale")

    def test_generation_requires_state_file_and_blocks_unresolved_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = root / "case.json"; case.write_text(json.dumps({"source_revision": "r2"}), encoding="utf-8")
            output = root / "output"
            self.assertEqual(run_case.main(["run_case.py", str(case), str(output)]), 2)
            state = root / "state.json"
            state.write_text(json.dumps({"context": {"type_missing": True}, "source_revision": "r1", "required_question_ids": ["type.confirm"], "questions": {"type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "recommended"}}}}), encoding="utf-8")
            output_text = StringIO()
            with redirect_stdout(output_text):
                self.assertEqual(run_case.main(["run_case.py", str(case), str(output), "--question-state", str(state)]), 2)
            self.assertIn("type.confirm", output_text.getvalue())

    def test_revision_binds_case_and_input_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = root / "case.json"
            case.write_text('{"synthetic":true}', encoding="utf-8")
            copied_case = root / "case-copy.json"
            copied_case.write_text('{"synthetic":true}', encoding="utf-8")
            self.assertNotEqual(run_case.compute_revision(case), run_case.compute_revision(copied_case))
            inputs = root / "input"
            inputs.mkdir()
            source = inputs / "source.txt"
            source.write_text("SYNTHETIC_A", encoding="utf-8")
            first = run_case.compute_revision(case, inputs)
            source.write_text("SYNTHETIC_B", encoding="utf-8")
            self.assertNotEqual(first, run_case.compute_revision(case, inputs))

    def test_add_replace_and_rate_review_require_an_inspected_input_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "input"
            inputs.mkdir()
            (inputs / "synthetic.txt").write_text("SYNTHETIC_SOURCE", encoding="utf-8")
            for question_id, fact, choice in (
                ("intake.readiness", "source_missing", "add"),
                ("source.unreadable", "source_unreadable", "replace"),
                ("rate.confirm", "rate_unconfirmed", "review"),
            ):
                context = {fact: True}
                state = {"context": context, "required_question_ids": [question_id], "questions": {
                    question_id: {"status": "deferred", "answer": {"mode": "option", "value": choice, "custom_value": "synthetic.txt"}},
                }}
                self.assertEqual(questions.validate_state(state), [])
                self.assertEqual(run_case.validate_resolution_actions(state, inputs), [])
                state["questions"][question_id]["answer"]["custom_value"] = "missing.txt"
                self.assertTrue(run_case.validate_resolution_actions(state, inputs))
                self.assertEqual(questions.pending_required([question_id], state), [question_id])

    def test_rate_review_with_verified_file_can_be_marked_answered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inputs = root / "input"
            inputs.mkdir()
            (inputs / "synthetic.txt").write_text("SYNTHETIC_RATE_SOURCE", encoding="utf-8")
            state = {"context": {"rate_unconfirmed": True}, "required_question_ids": ["rate.confirm"], "questions": {
                "rate.confirm": {"status": "answered", "answer": {"mode": "option", "value": "review", "custom_value": "synthetic.txt"}},
            }}
            self.assertEqual(questions.validate_state(state), [])
            self.assertEqual(run_case.validate_resolution_actions(state, inputs), [])
            self.assertEqual(questions.pending_required(state["required_question_ids"], state), [])

    def test_empty_resolved_state_is_accepted_by_question_gate(self):
        state = {"required_question_ids": [], "questions": {}}
        self.assertEqual(questions.validate_state(state), [])
        self.assertEqual(questions.pending_required([], state), [])

    def test_empty_context_cannot_skip_schema_required_case_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = root / "case.json"
            case.write_text(json.dumps({"type": "A1"}), encoding="utf-8")
            state = root / "state.json"
            state.write_text(json.dumps({
                "context": {},
                "source_revision": run_case.compute_revision(case),
                "required_question_ids": [],
                "questions": {},
            }), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(run_case.main(["run_case.py", str(case), str(root / "output"), "--question-state", str(state)]), 2)


if __name__ == "__main__":
    unittest.main()
