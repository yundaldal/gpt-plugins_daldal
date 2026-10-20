"""Contextual question catalog and answer-state validation for the intake flow."""
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR.parent / "resources" / "questions.json"
VALID_STATES = {"pending", "answered", "deferred", "not_applicable", "stale"}
INSTANCE_ID = re.compile(r"^(?P<base>[a-z][a-z0-9.]*?)::(?P<scope>person|session)\[(?P<index>0|[1-9][0-9]*)\]$")


def _parse_question_id(question_id, catalog):
    if not isinstance(question_id, str):
        return None
    if question_id in catalog:
        return question_id, None
    match = INSTANCE_ID.fullmatch(question_id)
    if not match:
        return None
    base_id, scope = match.group("base"), match.group("scope")
    question = catalog.get(base_id)
    if not question or scope not in question.get("repeatable_scopes", []):
        return None
    return base_id, scope


def _context_question_ids(context, catalog):
    """Return contextual IDs and schema errors, including explicit repeated instances."""
    if not isinstance(context, dict):
        return [], {}, ["context must be an object"]

    ids = []
    errors = []
    explicit = context.get("required_question_ids", [])
    if not isinstance(explicit, list):
        errors.append("context required_question_ids must be an array")
        explicit = []
    ids.extend(explicit)

    triggers = {
        "type.confirm": ("type_missing", "type_ambiguous"),
        "intake.readiness": ("source_missing",),
        "source.unreadable": ("source_unreadable",),
        "source.conflict": ("source_conflict",),
        "field.confirm": ("extracted_value_needs_confirmation",),
        "travel.present": ("travel_unspecified",),
        "attachment.include": ("attachment_ambiguous",),
        "rate.confirm": ("rate_unconfirmed",),
    }
    triggered = [qid for qid, fields in triggers.items() if any(context.get(field) for field in fields)]

    instances = context.get("question_instances", {})
    if not isinstance(instances, dict):
        errors.append("context question_instances must be an object")
        instances = {}
    expanded = {}
    bindings = {}
    for base_id, scopes in instances.items():
        if base_id not in catalog:
            errors.append(f"unknown repeated question id: {base_id}")
            continue
        if not isinstance(scopes, dict):
            errors.append(f"question_instances[{base_id}] must be an object")
            continue
        allowed_scopes = set(catalog[base_id].get("repeatable_scopes", []))
        for scope, descriptors in scopes.items():
            if scope not in allowed_scopes:
                errors.append(f"repeat scope is not allowed for question: {base_id}::{scope}")
                continue
            if not isinstance(descriptors, list) or not descriptors:
                errors.append(f"repeat instances must be a non-empty array: {base_id}::{scope}")
                continue
            for index, descriptor in enumerate(descriptors):
                question_id = f"{base_id}::{scope}[{index}]"
                if (not isinstance(descriptor, dict) or descriptor.get("index") != index
                        or isinstance(descriptor.get("index"), bool)
                        or not isinstance(descriptor.get("field_path"), str)
                        or not descriptor["field_path"].strip() or "value" not in descriptor):
                    errors.append(f"repeat instance needs a matching index, field_path, and value: {question_id}")
                    continue
                if base_id == "travel.present" and scope == "person" and descriptor["field_path"] != f"allowance.people[{index}].travel.amount":
                    errors.append(f"travel question binding must target the matching person amount: {question_id}")
                if base_id in {"field.confirm", "source.conflict"} and scope == "session":
                    if not isinstance(descriptor.get("source_id"), str) or not descriptor["source_id"].strip():
                        errors.append(f"session confirmation needs a stable source_id: {question_id}")
                    if not isinstance(descriptor.get("source_revision"), str) or not descriptor["source_revision"].strip():
                        errors.append(f"session confirmation needs a source_revision: {question_id}")
                expanded.setdefault(base_id, []).append(question_id)
                bindings[question_id] = {key: descriptor[key] for key in ("index", "field_path", "value", "source_id", "source_revision") if key in descriptor}

    explicit_by_base = {}
    for question_id in explicit:
        parsed = _parse_question_id(question_id, catalog)
        if parsed:
            explicit_by_base.setdefault(parsed[0], []).append(question_id)
    for base_id, instance_ids in expanded.items():
        if base_id not in explicit_by_base and base_id not in triggered:
            errors.append(f"question_instances supplied for a non-required question: {base_id}")
            continue
        concrete_ids = explicit_by_base.get(base_id, [])
        if concrete_ids == [base_id]:
            ids = [item for item in ids if item != base_id]
            ids.extend(instance_ids)
        elif concrete_ids and concrete_ids != instance_ids:
            errors.append(f"question_instances do not match explicit IDs: {base_id}")

    for base_id in ("field.confirm", "source.conflict"):
        if (base_id in triggered or base_id in explicit_by_base) and base_id not in expanded:
            errors.append(f"{base_id} requires explicit source-bound session instances")

    for base_id in triggered:
        if base_id not in explicit_by_base:
            ids.extend(expanded.get(base_id, [base_id]))

    seen = set()
    for question_id in ids:
        if isinstance(question_id, str) and question_id in seen:
            errors.append(f"duplicate required question id: {question_id}")
        if isinstance(question_id, str):
            seen.add(question_id)
        if _parse_question_id(question_id, catalog) is None:
            errors.append(f"unknown or invalid required question id: {question_id}")
    for question_id in ids:
        parsed = _parse_question_id(question_id, catalog)
        if parsed and parsed[1] and question_id not in bindings:
            errors.append(f"repeated question needs an explicit field binding: {question_id}")
    return ids, bindings, errors


def load_catalog(path=CATALOG_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def required_questions(context, path=CATALOG_PATH):
    """Return applicable questions in catalog order from explicit intake facts."""
    catalog = load_catalog(path)["questions"]
    catalog_by_id = {question["id"]: question for question in catalog}
    ids, _, _ = _context_question_ids(context or {}, catalog_by_id)
    id_set = {question_id for question_id in ids if isinstance(question_id, str)}
    result = []
    for question in catalog:
        matches = [question_id for question_id in ids if _parse_question_id(question_id, catalog_by_id) and _parse_question_id(question_id, catalog_by_id)[0] == question["id"]]
        for question_id in matches:
            if question_id in id_set:
                result.append({**question, "id": question_id})
                id_set.remove(question_id)
    return result


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
        options = question.get("options", [])
        has_direct_input = any(
            isinstance(option, dict) and option.get("id") == "custom"
            and option.get("value") == "custom" and option.get("label") == "직접 입력"
            for option in options
        )
        if not isinstance(custom, dict) or not custom.get("id") or not custom.get("label") or not has_direct_input:
            errors.append(f"question needs an explicit direct-input choice: {qid}")
    return errors


def validate_state(state, catalog_path=CATALOG_PATH):
    """Validate state without accepting a free-form answer as an implicit choice."""
    if not isinstance(state, dict):
        return ["question state must be an object"]
    full_catalog = load_catalog(catalog_path)
    catalog = {q["id"]: q for q in full_catalog["questions"]}
    errors = []
    question_entries = state.get("questions", {})
    if not isinstance(question_entries, dict):
        return ["questions must be an object"]
    for qid, entry in question_entries.items():
        parsed_id = _parse_question_id(qid, catalog)
        if parsed_id is None:
            errors.append(f"unknown question id: {qid}")
            continue
        base_id = parsed_id[0]
        if not isinstance(entry, dict) or entry.get("status") not in VALID_STATES:
            errors.append(f"invalid state for question: {qid}")
            continue
        if entry["status"] == "answered":
            answer = entry.get("answer")
            if not isinstance(answer, dict) or answer.get("mode") != "option":
                errors.append(f"answered question needs an explicit catalog option: {qid}")
                continue
            if answer.get("value") not in {o.get("value") for o in catalog[base_id].get("options", [])}:
                errors.append(f"option answer is not in catalog: {qid}")
            if answer.get("value") == "custom" and (not isinstance(answer.get("custom_value"), str) or not answer["custom_value"].strip()):
                errors.append(f"direct-input option needs a non-empty custom_value: {qid}")
            if "custom_value" in answer and (not isinstance(answer["custom_value"], str) or not answer["custom_value"].strip()):
                errors.append(f"custom follow-up is empty: {qid}")
    required_ids = state.get("required_question_ids", [])
    if not isinstance(required_ids, list):
        return errors + ["required_question_ids must be an array"]
    string_required_ids = [qid for qid in required_ids if isinstance(qid, str)]
    if len(string_required_ids) != len(set(string_required_ids)):
        errors.append("required_question_ids must not contain duplicates")
    for qid in required_ids:
        if _parse_question_id(qid, catalog) is None:
            errors.append(f"unknown required question id: {qid}")
    context_ids, context_bindings, context_errors = _context_question_ids(state.get("context", {}), catalog)
    errors.extend(context_errors)
    if set(string_required_ids) != {qid for qid in context_ids if isinstance(qid, str)} or len(string_required_ids) != len(required_ids):
        errors.append("required_question_ids do not match contextual question IDs")
    allowed_na = set(full_catalog.get("policy", {}).get("allow_not_applicable", []))
    for qid in required_ids:
        parsed_id = _parse_question_id(qid, catalog)
        if parsed_id is None:
            continue
        base_id = parsed_id[0]
        if not isinstance(qid, str):
            continue
        entry = question_entries.get(qid, {})
        if not isinstance(entry, dict):
            errors.append(f"required question state is missing: {qid}")
            continue
        if entry.get("status") == "not_applicable" and base_id not in allowed_na:
            errors.append(f"required question cannot be not_applicable: {qid}")
        answer = entry.get("answer")
        if not isinstance(answer, dict):
            answer = {}
        if entry.get("status") == "answered" and answer.get("mode") == "option":
            followups = set(full_catalog.get("policy", {}).get("custom_required_for", {}).get(base_id, []))
            if answer.get("value") in followups and (not isinstance(answer.get("custom_value"), str) or not answer["custom_value"].strip()):
                errors.append(f"option requires custom follow-up: {qid}")
        if entry.get("status") == "answered" and parsed_id[1]:
            binding = context_bindings.get(qid)
            answer_binding = answer.get("binding")
            if not isinstance(answer_binding, dict) or answer_binding.get("field_path") != (binding or {}).get("field_path"):
                errors.append(f"answered repeated question must retain its field binding: {qid}")
                answer_binding = {}
            for key in ("index", "source_id", "source_revision"):
                if binding and key in binding and answer_binding.get(key) != binding[key]:
                    errors.append(f"repeated answer {key} does not match its field binding: {qid}")
            if (binding and "value" in binding
                    and not (base_id == "field.confirm" and answer.get("value") in {"edit", "custom"})
                    and answer_binding.get("value") != binding["value"]):
                errors.append(f"repeated answer value does not match its field binding: {qid}")
            if base_id == "travel.present":
                amount = binding.get("value") if binding else None
                if answer_binding.get("index") != (binding or {}).get("index") or answer_binding.get("value") != amount:
                    errors.append(f"travel answer binding must match the person's amount: {qid}")
                if answer.get("value") == "none" and (isinstance(amount, bool) or amount != 0):
                    errors.append(f"travel none answer must match a zero amount: {qid}")
                elif answer.get("value") in {"amount", "custom"}:
                    expected = _decimal_value(amount)
                    supplied = _decimal_value(answer.get("custom_value"))
                    if expected is None or supplied is None or expected != supplied:
                        errors.append(f"travel amount answer must match the bound amount: {qid}")
    return errors


def _decimal_value(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _resolve_case_path(case, field_path):
    current = case
    for raw_component in field_path.split("."):
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)(?:\[([0-9]+)\])?", raw_component)
        if not match or not isinstance(current, dict) or match.group(1) not in current:
            return None, False
        current = current[match.group(1)]
        if match.group(2) is not None:
            index = int(match.group(2))
            if not isinstance(current, list) or index >= len(current):
                return None, False
            current = current[index]
    return current, True


def validate_case_bindings(case, state, catalog_path=CATALOG_PATH):
    """Ensure question field bindings still point to the values in the submitted case."""
    if not isinstance(state, dict):
        return ["question state must be an object"]
    catalog = {q["id"]: q for q in load_catalog(catalog_path)["questions"]}
    _, bindings, errors = _context_question_ids(state.get("context", {}), catalog)
    if errors:
        return errors
    question_entries = state.get("questions", {})
    if not isinstance(question_entries, dict):
        return ["questions must be an object"]
    for question_id, binding in bindings.items():
        current, found = _resolve_case_path(case, binding["field_path"])
        parsed_id = _parse_question_id(question_id, catalog)
        entry = question_entries.get(question_id, {})
        answer = entry.get("answer", {}) if isinstance(entry, dict) else {}
        if not isinstance(answer, dict) or entry.get("status") != "answered":
            continue
        if not found:
            errors.append(f"question field path does not resolve in the submitted case: {question_id}")
            continue
        answer_binding = answer.get("binding")
        if parsed_id and parsed_id[0] in {"field.confirm", "source.conflict"}:
            if not isinstance(answer_binding, dict):
                errors.append(f"session confirmation answer needs an explicit binding: {question_id}")
                continue
            expected_source = {key: binding.get(key) for key in ("source_id", "source_revision")}
            if (answer_binding.get("index") != binding["index"] or answer_binding.get("field_path") != binding["field_path"]
                    or any(answer_binding.get(key) != value for key, value in expected_source.items())):
                errors.append(f"session confirmation answer source binding does not match: {question_id}")
                continue
            if binding.get("source_revision") != state.get("source_revision"):
                errors.append(f"session confirmation source revision does not match the question state: {question_id}")
                continue
            if parsed_id[0] == "source.conflict":
                if answer_binding.get("value") != binding["value"] or current != binding["value"]:
                    errors.append(f"resolved conflict does not match the target case field: {question_id}")
                if answer.get("value") not in {"latest", "confirm", "custom"}:
                    errors.append(f"source conflict answer is not a recognized choice: {question_id}")
                if answer.get("value") in {"confirm", "custom"} and answer.get("custom_value") != current:
                    errors.append(f"resolved conflict value must match the target case field: {question_id}")
            elif answer.get("value") == "accept":
                if answer_binding.get("value") != binding["value"] or current != binding["value"]:
                    errors.append(f"accepted extraction does not match the target case field: {question_id}")
            elif answer.get("value") in {"edit", "custom"}:
                edited = _decimal_value(answer.get("custom_value"))
                target = _decimal_value(current)
                same_value = current == answer.get("custom_value") if isinstance(current, str) else edited is not None and target == edited
                if not answer.get("custom_value") or not same_value or answer_binding.get("value") != current:
                    errors.append(f"edited value does not match the target case field: {question_id}")
            else:
                errors.append(f"session confirmation answer is not a recognized choice: {question_id}")
        elif parsed_id and parsed_id[0] == "travel.present":
            if current != binding["value"]:
                errors.append(f"question field binding does not match the submitted case: {question_id}")
        elif current != binding["value"]:
            errors.append(f"question field binding does not match the submitted case: {question_id}")

    for question_id in state.get("required_question_ids", []):
        parsed = _parse_question_id(question_id, catalog)
        if not parsed or parsed[1]:
            continue
        base_id = parsed[0]
        entry = question_entries.get(question_id, {})
        if not isinstance(entry, dict) or entry.get("status") != "answered":
            continue
        answer = entry.get("answer", {})
        if not isinstance(answer, dict):
            continue
        if base_id == "type.confirm":
            selected_type = case.get("type") if isinstance(case, dict) else None
            if answer.get("value") == "recommended":
                if state.get("context", {}).get("recommended_type") != selected_type:
                    errors.append("recommended type answer must match the case type")
            elif answer.get("value") in {"choose", "custom"}:
                if answer.get("custom_value") != selected_type:
                    errors.append("custom type answer must match the case type")
        elif base_id == "attachment.include":
            draft = case.get("draft", {}) if isinstance(case, dict) else {}
            attachments = draft.get("attachments") if isinstance(draft, dict) else None
            if not isinstance(attachments, list):
                errors.append("attachment answer needs a draft.attachments array")
            elif answer.get("value") == "use" and not attachments:
                errors.append("use answer requires the current attachment list in the case")
            elif answer.get("value") in {"edit", "custom"}:
                try:
                    supplied = json.loads(answer.get("custom_value", ""))
                except (TypeError, json.JSONDecodeError):
                    supplied = None
                if not isinstance(supplied, list) or supplied != attachments:
                    errors.append("attachment edit must be a JSON array matching the case")
    return errors


def pending_required(question_ids, state):
    if not isinstance(state, dict):
        return list(question_ids)
    questions = state.get("questions", {})
    if not isinstance(questions, dict):
        return list(question_ids)
    catalog = {q["id"]: q for q in load_catalog()["questions"]}
    allowed_na = set(load_catalog().get("policy", {}).get("allow_not_applicable", []))
    pending = []
    for qid in question_ids:
        entry = questions.get(qid)
        if isinstance(entry, dict) and entry.get("status") == "answered":
            continue
        parsed = _parse_question_id(qid, catalog)
        if isinstance(entry, dict) and entry.get("status") == "not_applicable" and parsed and parsed[0] in allowed_na:
            continue
        pending.append(qid)
    return pending


def refresh_for_revision(state, source_revision):
    """Mark prior answers stale when the source revision changes."""
    refreshed = json.loads(json.dumps(state if isinstance(state, dict) else {}, ensure_ascii=False))
    previous = refreshed.get("source_revision")
    if previous and source_revision and previous != source_revision:
        for entry in (refreshed.get("questions") or {}).values():
            if isinstance(entry, dict) and entry.get("status") == "answered":
                entry["status"] = "stale"
    if source_revision:
        refreshed["source_revision"] = source_revision
    return refreshed
