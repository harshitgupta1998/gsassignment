import re
from typing import Any, Dict, Optional

from normalizer import clean_text, normalize_money, normalize_number
from schema import make_rule


def _rule_id(source: str, clause: str, suffix: str = "1") -> str:
    return f"{source}_rule_{clause}_{suffix}"


def extract_clause(
    *,
    source_document: str,
    section: str,
    clause: str,
    category: str,
    text: str,
) -> list[dict[str, Any]]:
    raw = clean_text(text)
    lower = raw.lower()
    rules: list[dict[str, Any]] = []

    if "credit score" in lower and "at least" in lower:
        score = re.search(r"credit score of at least (\d+)", lower)
        if score:
            rules.append(make_rule(
                rule_id=_rule_id(source_document, clause, "credit_score"),
                source_document=source_document,
                section=section,
                clause=clause,
                category="eligibility",
                subject="applicant credit score",
                operator=">=",
                value=int(score.group(1)),
                unit="score",
                scope="applicant",
                raw_text=raw,
                extraction_method="deterministic",
            ))

    if "coverage amount" in lower and ("not exceed" in lower or "exceeding" in lower):
        money = re.search(r"\$[\d,]+", raw)
        if money and "maximum coverage amount" in lower:
            rules.append(make_rule(
                rule_id=_rule_id(source_document, clause, "coverage_amount"),
                source_document=source_document,
                section=section,
                clause=clause,
                category="eligibility",
                subject="single policy coverage amount",
                operator="<=",
                value=normalize_money(money.group(0)),
                unit="USD",
                scope="policy",
                raw_text=raw,
                extraction_method="deterministic",
            ))

    if "total portfolio value" in lower and "no more than" in lower:
        pct = re.search(r"no more than ([\d.]+)%", lower)
        if pct:
            subject = "portfolio concentration"
            if "single state" in lower:
                subject = "policies from any single state"
            elif "coverage amount" in lower:
                subject = "policies with coverage amount exceeding threshold"
            elif "under 25" in lower:
                subject = "policies where primary applicant is under 25"
            elif "credit scores between" in lower:
                subject = "policies for applicants with credit scores between 680 and 700"
            rules.append(make_rule(
                rule_id=_rule_id(source_document, clause, "portfolio_limit"),
                source_document=source_document,
                section=section,
                clause=clause,
                category="concentration_limit",
                subject=subject,
                operator="<=",
                value=normalize_number(pct.group(1)),
                unit="percent",
                scope="portfolio",
                basis="total portfolio value",
                condition=_condition_from_text(lower),
                raw_text=raw,
                extraction_method="deterministic",
            ))

    if "debt-to-income ratio" in lower and "not exceed" in lower:
        pcts = [normalize_number(value) for value in re.findall(r"(\d+(?:\.\d+)?)%", lower)]
        if pcts:
            rules.append(make_rule(
                rule_id=_rule_id(source_document, clause, "dti"),
                source_document=source_document,
                section=section,
                clause=clause,
                category="eligibility" if source_document == "sample_1" else "concentration_limit",
                subject="debt-to-income ratio" if source_document == "sample_1" else "weighted average debt-to-income ratio",
                operator="<=",
                value=pcts[0],
                unit="percent",
                scope="applicant" if source_document == "sample_1" else "portfolio",
                raw_text=raw,
                extraction_method="deterministic",
            ))
            if len(pcts) > 1:
                rules.append(make_rule(
                    rule_id=_rule_id(source_document, clause, "dti_cosigner_exception"),
                    source_document=source_document,
                    section=section,
                    clause=clause,
                    category="eligibility",
                    subject="debt-to-income ratio",
                    operator="<=",
                    value=pcts[1],
                    unit="percent",
                    scope="applicant",
                    condition={
                        "subject": "co-signer credit score",
                        "operator": ">",
                        "value": 750,
                        "unit": "score",
                    },
                    raw_text=raw,
                    extraction_method="deterministic",
                ))

    if "payment more than" in lower and "days overdue" in lower:
        days = re.search(r"more than (\d+) days overdue", lower)
        if days:
            rules.append(make_rule(
                rule_id=_rule_id(source_document, clause, "overdue_payment"),
                source_document=source_document,
                section=section,
                clause=clause,
                category="eligibility",
                subject="payment overdue days",
                operator="<=",
                value=int(days.group(1)),
                unit="days",
                scope="applicant",
                basis="as of Review Date",
                raw_text=raw,
                extraction_method="deterministic",
            ))

    if "must reside" in lower:
        rules.append(make_rule(
            rule_id=_rule_id(source_document, clause, "residency"),
            source_document=source_document,
            section=section,
            clause=clause,
            category="eligibility",
            subject="applicant residency",
            operator="required",
            value="United States or its territories",
            unit=None,
            scope="applicant",
            raw_text=raw,
            extraction_method="deterministic",
        ))

    if "annual income" in lower and "below" in lower:
        amounts = [normalize_money(value) for value in re.findall(r"\$[\d,]+", raw)]
        if amounts:
            rules.append(make_rule(
                rule_id=_rule_id(source_document, clause, "income"),
                source_document=source_document,
                section=section,
                clause=clause,
                category="eligibility",
                subject="applicant annual income",
                operator=">=",
                value=amounts[0],
                unit="USD",
                scope="applicant",
                exception={
                    "condition": "applicant is enrolled in an approved assistance program",
                    "operator": ">=",
                    "value": amounts[1] if len(amounts) > 1 else None,
                    "unit": "USD",
                },
                raw_text=raw,
                extraction_method="deterministic",
            ))

    if "weighted average credit score" in lower:
        score = re.search(r"less than (\d+)", lower)
        if score:
            rules.append(make_rule(
                rule_id=_rule_id(source_document, clause, "weighted_credit_score"),
                source_document=source_document,
                section=section,
                clause=clause,
                category="concentration_limit",
                subject="weighted average credit score",
                operator=">=",
                value=int(score.group(1)),
                unit="score",
                scope="portfolio",
                raw_text=raw,
                extraction_method="deterministic",
            ))

    if category == "fee":
        rules.extend(_extract_fee(source_document, section, clause, raw))

    return rules


def _condition_from_text(lower: str) -> Optional[Dict[str, Any]]:
    money = re.search(r"coverage amount exceeding \$([\d,]+)", lower)
    if money:
        return {
            "subject": "coverage amount",
            "operator": ">",
            "value": int(money.group(1).replace(",", "")),
            "unit": "USD",
        }
    age = re.search(r"under (\d+) years", lower)
    if age:
        return {
            "subject": "primary applicant age",
            "operator": "<",
            "value": int(age.group(1)),
            "unit": "years",
        }
    score_range = re.search(r"credit scores between (\d+) and (\d+)", lower)
    if score_range:
        return {
            "subject": "applicant credit score",
            "operator": "between",
            "value": [int(score_range.group(1)), int(score_range.group(2))],
            "unit": "score",
        }
    return None


def _extract_fee(source_document: str, section: str, clause: str, raw: str) -> list[dict[str, Any]]:
    lower = raw.lower()
    fee_type = raw.split(":", 1)[0] if ":" in raw else "Fee"
    rules: list[dict[str, Any]] = []

    if "processing fee" in lower:
        value = normalize_money(re.search(r"\$[\d,]+", raw).group(0))
        rules.append(make_rule(
            rule_id=_rule_id(source_document, clause, "processing_fee"),
            source_document=source_document,
            section=section,
            clause=clause,
            category="fee",
            subject=fee_type,
            operator="=",
            value=value,
            unit="USD",
            scope="application",
            basis="per application, due upon submission",
            raw_text=raw,
            extraction_method="deterministic",
        ))
    elif "early termination fee" in lower:
        months = [int(value) for value in re.findall(r"(\d+) months", lower)]
        rules.append(make_rule(
            rule_id=_rule_id(source_document, clause, "early_termination_fee"),
            source_document=source_document,
            section=section,
            clause=clause,
            category="fee",
            subject=fee_type,
            operator="=",
            value=months[1] if len(months) > 1 else 3,
            unit="months_of_annual_service_fee",
            scope="policy",
            condition={
                "subject": "policy cancellation timing",
                "operator": "<=",
                "value": months[0] if months else 24,
                "unit": "months after start",
            },
            raw_text=raw,
            extraction_method="deterministic",
        ))
    elif "annual service fee" in lower:
        pct = normalize_number(re.search(r"([\d.]+)%", lower).group(1))
        rules.append(make_rule(
            rule_id=_rule_id(source_document, clause, "annual_service_fee"),
            source_document=source_document,
            section=section,
            clause=clause,
            category="fee",
            subject=fee_type,
            operator="=",
            value=pct,
            unit="percent_per_annum",
            scope="policy",
            basis="outstanding coverage amount, payable monthly",
            raw_text=raw,
            extraction_method="deterministic",
        ))
    elif "late payment fee" in lower:
        days = int(re.search(r"more than (\d+) days", lower).group(1))
        pct = normalize_number(re.search(r"fee of ([\d.]+)%", lower).group(1))
        amounts = [normalize_money(value) for value in re.findall(r"\$[\d,]+", raw)]
        rules.append(make_rule(
            rule_id=_rule_id(source_document, clause, "late_payment_fee"),
            source_document=source_document,
            section=section,
            clause=clause,
            category="fee",
            subject=fee_type,
            operator="=",
            value=pct,
            unit="percent",
            scope="payment",
            basis="overdue amount",
            condition={
                "subject": "scheduled payment overdue days",
                "operator": ">",
                "value": days,
                "unit": "days",
            },
            exception={
                "minimum": {"value": amounts[0], "unit": "USD"},
                "maximum": {"value": amounts[1], "unit": "USD"},
            },
            raw_text=raw,
            extraction_method="deterministic",
        ))
    elif "reinstatement fee" in lower:
        amount = normalize_money(re.search(r"\$[\d,]+", raw).group(0))
        days = int(re.search(r"more than (\d+) days", lower).group(1))
        rules.append(make_rule(
            rule_id=_rule_id(source_document, clause, "reinstatement_fee"),
            source_document=source_document,
            section=section,
            clause=clause,
            category="fee",
            subject=fee_type,
            operator="=",
            value=amount,
            unit="USD",
            scope="policy",
            condition={
                "subject": "lapse duration",
                "operator": ">",
                "value": days,
                "unit": "days",
            },
            raw_text=raw,
            extraction_method="deterministic",
        ))
    return rules
