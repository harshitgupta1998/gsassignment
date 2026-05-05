import json
import os
from typing import Any, Optional

from parser import Clause


SYSTEM_PROMPT = """You extract policy rules from legal and insurance text.
Return only JSON. Do not include markdown or any explanation text.

Be strict about the schema and machine-readable output:
- Every numeric threshold, condition, exception, cap, floor, or fee should become a rule or a structured nested field.
- Preserve the raw source text for traceability in the `raw_text` field.

Operator rules:
- Allowed operator values: >, >=, <, <=, =, required, not_allowed, between
- DO NOT use the word "if" as an operator. Conditional language ("if", "provided that", "unless", "subject to", etc.) must be represented using the `condition` or `exception` objects on the rule (preferably with `subject`, `operator`, and `value` when possible).
- For ranges use operator "between" and set `value` to a two-element list [min, max].

Extraction guidance:
- Populate `extraction.confidence` with a numeric value between 0.0 and 1.0.
- If you cannot reliably extract a structured operator or numeric value, do not invent one; instead leave the field null and add a short note in `extraction.notes` describing the ambiguity.
- Use stable, machine-friendly `id` strings (no newlines).
- Return a top-level JSON object with a `rules` array; each rule must follow the schema shown in the user prompt. Return only valid JSON.

Be concise and strict. Do not emit any explanatory text, markdown, or extra fields outside the described schema."""


def build_prompt(
    *,
    source_document: str,
    section: str,
    category: str,
    clauses: list[Clause],
) -> str:
    clause_payload = [{"clause": clause.label, "text": clause.text} for clause in clauses]
    return json.dumps({
        "task": "Extract structured policy rules from these clauses.",
        "source_document": source_document,
        "section": section,
        "default_category": category,
        "schema": {
            "rules": [{
                "id": "stable rule id",
                "source_document": source_document,
                "section": section,
                "clause": "clause label",
                "category": "eligibility | concentration_limit | fee | other",
                "subject": "what the rule constrains",
                "operator": "> | >= | < | <= | = | required | not_allowed",
                "value": "number, string, list, or null",
                "unit": "USD | percent | score | days | months | years | null",
                "scope": "applicant | policy | portfolio | payment | application | null",
                "condition": "object or null",
                "exception": "object or null",
                "basis": "basis for percentage/fee or null",
                "raw_text": "exact clause text",
                "extraction": {
                    "method": "llm",
                    "confidence": "0.0 to 1.0",
                    "notes": ["short notes if helpful"]
                }
            }]
        },
        "clauses": clause_payload,
    }, indent=2)


def extract_with_llm(
    *,
    source_document: str,
    section: str,
    category: str,
    clauses: list[Clause],
    model: Optional[str] = None,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is not installed. Run: pip install -r backend/requirements.txt") from exc

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(
                source_document=source_document,
                section=section,
                category=category,
                clauses=clauses,
            )},
        ],
    )
    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    if "rules" not in data:
        raise RuntimeError("LLM response did not include a rules array")
    for rule in data["rules"]:
        rule.setdefault("extraction", {})
        rule["extraction"]["method"] = "llm"
    return data
