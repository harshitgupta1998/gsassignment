from typing import Any

from normalizer import numeric_values_from_text
from schema import ALLOWED_OPERATORS


def validate_rule(rule: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    required = ["id", "source_document", "section", "clause", "category", "subject", "operator", "raw_text"]
    for field in required:
        if field not in rule or rule[field] in (None, ""):
            warnings.append(f"Missing required field: {field}")

    if rule.get("operator") not in ALLOWED_OPERATORS:
        warnings.append(f"Unexpected operator: {rule.get('operator')}")

    raw_values = numeric_values_from_text(rule.get("raw_text", ""))
    value = rule.get("value")
    if isinstance(value, (int, float)) and value not in raw_values:
        warnings.append(f"Numeric value {value} was not directly found in source text")

    return warnings


def validate_document(document: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    rules = document.get("rules", [])
    for rule in rules:
        for warning in validate_rule(rule):
            warnings.append(f"{rule.get('id', 'unknown')}: {warning}")

    clauses: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for rule in rules:
        clauses.setdefault((rule.get("clause", ""), rule.get("raw_text", "")), []).append(rule)
    for (clause, raw_text), clause_rules in clauses.items():
        raw_lower = raw_text.lower()
        if any(marker in raw_lower for marker in ["unless", "provided that", "if ", "subject to"]):
            has_context = any(
                bool(rule.get("condition") or rule.get("exception") or rule.get("basis"))
                for rule in clause_rules
            )
            if not has_context:
                warnings.append(
                    f"clause {clause}: Clause appears conditional or qualified but no condition/exception/basis was extracted"
                )

    document["validation"] = {
        "status": "passed" if not warnings else "passed_with_warnings",
        "warnings": warnings,
    }
    return document


def should_fallback(llm_document: dict[str, Any], clause_count: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    rules = llm_document.get("rules", [])
    if not rules:
        reasons.append("LLM returned no rules")
    if len(rules) < clause_count:
        reasons.append(f"LLM returned fewer rules ({len(rules)}) than clauses ({clause_count})")
    warning_count = len(llm_document.get("validation", {}).get("warnings", []))
    if warning_count > 3:
        reasons.append(f"LLM output had {warning_count} validation warnings")
    return bool(reasons), reasons
