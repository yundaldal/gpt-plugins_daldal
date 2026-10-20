import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins" / "pumui-daldal" / "skills" / "pumui" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import questions


class QuestionFlowTests(unittest.TestCase):
    def test_catalog_has_explicit_options_and_custom_input(self):
        self.assertEqual(questions.validate_catalog(), [])
        catalog = questions.load_catalog()
        self.assertTrue(catalog["policy"]["every_question_requires_choice_and_custom_input"])
        for question in catalog["questions"]:
            self.assertGreaterEqual(len(question["options"]), 2)
            self.assertEqual(question["custom_input"]["id"], "custom")

    def test_answered_state_accepts_option_or_custom_and_rejects_implicit_text(self):
        valid = {"questions": {"type.confirm": {"status": "answered", "answer": {"mode": "custom", "value": "A4"}}}}
        self.assertEqual(questions.validate_state(valid), [])
        invalid = {"questions": {"type.confirm": {"status": "answered", "answer": "A4"}}}
        self.assertTrue(questions.validate_state(invalid))
        unknown_option = {"questions": {"type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "not-a-choice"}}}}
        self.assertTrue(questions.validate_state(unknown_option))

    def test_pending_required_does_not_reask_answered(self):
        state = {"questions": {"type.confirm": {"status": "answered", "answer": {"mode": "option", "value": "recommended"}}}}
        self.assertEqual(questions.pending_required(["type.confirm", "source.conflict"], state), ["source.conflict"])

    def test_context_selects_only_questions_triggered_by_intake_facts(self):
        ids = [q["id"] for q in questions.required_questions({"source_conflict": True, "travel_unspecified": True})]
        self.assertEqual(ids, ["source.conflict", "travel.present"])

    def test_source_revision_marks_old_answers_stale(self):
        state = {"source_revision": "r1", "questions": {"field.confirm": {"status": "answered", "answer": {"mode": "option", "value": "accept"}}}}
        refreshed = questions.refresh_for_revision(state, "r2")
        self.assertEqual(refreshed["questions"]["field.confirm"]["status"], "stale")


if __name__ == "__main__":
    unittest.main()
