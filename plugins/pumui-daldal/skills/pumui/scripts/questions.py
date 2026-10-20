"""Contextual question catalog and answer-state validation for the intake flow."""
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR.parent / "resources" / "questions.json"
VALID_STATES = {"pending", "answered", "deferred", "not_applicable", "stale"}


def load_catalog(path=CATALOG_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def required_questions(context, path=CATALOG_PATH):
    """Return applicable questions in catalog order from explicit intake facts."""
    context = context or {}
    ids = set(context.get("required_question_ids") or [])
    if not ids:
        if context.get("type_missing") or context.get("type_ambiguous"):
            ids.add("type.confirm")
        if context.get("source_missing"):
            ids.add("intake.readiness")
        if context.get("source_unreadable"):
            ids.add("source.unreadable")
        if context.get("source_conflict"):
            ids.add("source.conflict")
        if context.get("extracted_value_needs_confirmation"):
            ids.add("field.confirm")
        if context.get("travel_unspecified"):
            ids.add("travel.present")
        if context.get("attachment_ambiguous"):
            ids.add("attachment.include")
        if context.get("rate_unconfirmed"):
            ids.add("rate.confirm")
        if context.get("hwpx_failed"):
            ids.add("recovery.txt")
    if ids:
        return [q for q in load_catalog(path)["questions"] if q["id"] in ids]
    return []


def validate_catalog(path=CATALOG_PATH):
    catalog = load_catalog(path)
    errors = []
    seen = set()
    for question in catalog.get("questions", []):
        qid = question.get("id")
        if not qid or qid in seen:
            errors.append(f"duplicate or missing id: {qid}")
        seen.add(qid)
        if not question.get("prompt") or len(question.get("options", [])) < 2:
            errors.append(f"question needs prompt and at least two options: {qid}")
        custom = question.get("custom_input")
        if not isinstance(custom, dict) or not custom.get("id") or not custom.get("label"):
            errors.append(f"question needs explicit custom input: {qid}")
    return errors


def validate_state(state, catalog_path=CATALOG_PATH):
    """Validate state without accepting a free-form answer as an implicit choice."""
    if not isinstance(state, dict):
        return ["question state must be an object"]
    catalog = {q["id"]: q for q in load_catalog(catalog_path)["questions"]}
    catalog_ids = set(catalog)
    errors = []
    for qid, entry in (state.get("questions") or {}).items():
        if qid not in catalog_ids:
            errors.append(f"unknown question id: {qid}")
            continue
        if not isinstance(entry, dict) or entry.get("status") not in VALID_STATES:
            errors.append(f"invalid state for question: {qid}")
            continue
        if entry["status"] == "answered":
            answer = entry.get("answer")
            if not isinstance(answer, dict) or not answer.get("mode") in {"option", "custom"}:
                errors.append(f"answered question needs option or custom mode: {qid}")
            elif answer["mode"] == "option" and answer.get("value") not in {o.get("value") for o in catalog[qid].get("options", [])}:
                errors.append(f"option answer is not in catalog: {qid}")
            elif answer["mode"] == "custom" and not str(answer.get("value", "")).strip():
                errors.append(f"custom answer is empty: {qid}")
    return errors


def pending_required(question_ids, state):
    state = state or {}
    questions = state.get("questions") or {}
    return [qid for qid in question_ids if questions.get(qid, {}).get("status") in {None, "pending", "deferred", "stale"}]


def refresh_for_revision(state, source_revision):
    """Mark prior answers stale when the source revision changes."""
    refreshed = json.loads(json.dumps(state or {}, ensure_ascii=False))
    previous = refreshed.get("source_revision")
    if previous and source_revision and previous != source_revision:
        for entry in (refreshed.get("questions") or {}).values():
            if entry.get("status") == "answered":
                entry["status"] = "stale"
    if source_revision:
        refreshed["source_revision"] = source_revision
    return refreshed
