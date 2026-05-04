import re
from dataclasses import dataclass

from normalizer import clean_text


@dataclass
class Clause:
    label: str
    text: str


CLAUSE_PATTERN = re.compile(r"\(([a-z]+|[ivxlcdm]+)\)\s*", re.IGNORECASE)


def split_clauses(text: str) -> list[Clause]:
    matches = list(CLAUSE_PATTERN.finditer(text))
    clauses: list[Clause] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        clauses.append(Clause(label=match.group(1), text=clean_text(text[start:end])))
    return clauses
