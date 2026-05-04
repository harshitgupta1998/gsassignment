import re
from decimal import Decimal
from typing import Any, Union


OPERATOR_PHRASES = [
    ("shall not be less than", ">="),
    ("not be less than", ">="),
    ("at least", ">="),
    ("not exceed", "<="),
    ("no more than", "<="),
    ("maximum", "<="),
    ("minimum", ">="),
    ("below", "<"),
    ("under", "<"),
    ("above", ">"),
    ("more than", ">"),
    ("exceeding", ">"),
    ("equal to", "="),
]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_money(value: str) -> int:
    return int(value.replace("$", "").replace(",", ""))


def normalize_number(value: str) -> Union[int, float]:
    parsed = Decimal(value.replace(",", ""))
    return int(parsed) if parsed == parsed.to_integral() else float(parsed)


def normalize_operator(text: str, default: str = "=") -> str:
    lower = text.lower()
    for phrase, operator in OPERATOR_PHRASES:
        if phrase in lower:
            return operator
    return default


def numeric_values_from_text(text: str) -> list[Any]:
    values: list[Any] = []
    for match in re.finditer(r"\$[\d,]+(?:\.\d+)?|\d+(?:\.\d+)?%", text):
        token = match.group(0)
        if token.startswith("$"):
            values.append(normalize_money(token))
        elif token.endswith("%"):
            values.append(normalize_number(token[:-1]))
    for match in re.finditer(r"(?<![$\d.])\d+(?:\.\d+)?(?![%\d])", text):
        values.append(normalize_number(match.group(0)))
    return values
