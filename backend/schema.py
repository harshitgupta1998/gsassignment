from typing import Any, Dict, List, Optional


ALLOWED_OPERATORS = {">", ">=", "<", "<=", "=", "required", "not_allowed"}


def make_rule(
    *,
    rule_id: str,
    source_document: str,
    section: str,
    clause: str,
    category: str,
    subject: str,
    operator: str,
    value: Any = None,
    unit: Optional[str] = None,
    scope: Optional[str] = None,
    condition: Optional[Dict[str, Any]] = None,
    exception: Optional[Dict[str, Any]] = None,
    basis: Optional[str] = None,
    raw_text: str,
    extraction_method: str,
    confidence: float = 0.8,
    notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "id": rule_id,
        "source_document": source_document,
        "section": section,
        "clause": clause,
        "category": category,
        "subject": subject,
        "operator": operator,
        "value": value,
        "unit": unit,
        "scope": scope,
        "condition": condition,
        "exception": exception,
        "basis": basis,
        "raw_text": raw_text,
        "extraction": {
            "method": extraction_method,
            "confidence": confidence,
            "notes": notes or [],
        },
    }


def empty_document(source_document: str, section: str, title: str) -> Dict[str, Any]:
    return {
        "source_document": source_document,
        "section": section,
        "title": title,
        "rules": [],
        "validation": {
            "status": "not_validated",
            "warnings": [],
        },
    }
