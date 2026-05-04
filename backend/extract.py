import argparse
import json
from pathlib import Path
from typing import Any

from deterministic_extractor import extract_clause
from llm_extractor import extract_with_llm
from parser import split_clauses
from samples import SAMPLES
from schema import empty_document
from validator import should_fallback, validate_document


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


def extract_deterministic(source_document: str, sample: dict[str, str]) -> dict[str, Any]:
    document = empty_document(source_document, sample["section"], sample["title"])
    clauses = split_clauses(sample["text"])
    for clause in clauses:
        document["rules"].extend(extract_clause(
            source_document=source_document,
            section=sample["section"],
            clause=clause.label,
            category=sample["category"],
            text=clause.text,
        ))
    return validate_document(document)


def extract_hybrid(source_document: str, sample: dict[str, str], mode: str) -> dict[str, Any]:
    clauses = split_clauses(sample["text"])
    if mode == "deterministic":
        return extract_deterministic(source_document, sample)

    try:
        llm_payload = extract_with_llm(
            source_document=source_document,
            section=sample["section"],
            category=sample["category"],
            clauses=clauses,
        )
        document = empty_document(source_document, sample["section"], sample["title"])
        document["rules"] = llm_payload["rules"]
        document = validate_document(document)
        fallback, reasons = should_fallback(document, len(clauses))
        if mode == "llm" or not fallback:
            return document

        deterministic = extract_deterministic(source_document, sample)
        deterministic["validation"]["warnings"].insert(
            0,
            "Used deterministic fallback because: " + "; ".join(reasons),
        )
        return deterministic
    except Exception as exc:
        if mode == "llm":
            raise
        deterministic = extract_deterministic(source_document, sample)
        deterministic["validation"]["warnings"].insert(
            0,
            f"Used deterministic fallback because LLM extraction failed: {exc}",
        )
        deterministic["validation"]["status"] = "passed_with_warnings"
        return deterministic


def write_outputs(results: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for source_document, payload in results.items():
        with (OUTPUT_DIR / f"{source_document}.json").open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
            file.write("\n")

    combined = {
        "documents": list(results.values()),
        "rules": [rule for document in results.values() for rule in document["rules"]],
    }
    with (OUTPUT_DIR / "all_rules.json").open("w", encoding="utf-8") as file:
        json.dump(combined, file, indent=2)
        file.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured policy rules from sample text.")
    parser.add_argument(
        "--mode",
        choices=["hybrid", "llm", "deterministic"],
        default="hybrid",
        help="hybrid uses LLM first and deterministic fallback; deterministic requires no API key.",
    )
    parser.add_argument(
        "--sample",
        choices=list(SAMPLES.keys()),
        help="Run a single sample instead of all samples.",
    )
    args = parser.parse_args()

    selected = {args.sample: SAMPLES[args.sample]} if args.sample else SAMPLES
    results = {
        source_document: extract_hybrid(source_document, sample, args.mode)
        for source_document, sample in selected.items()
    }
    write_outputs(results)
    total_rules = sum(len(payload["rules"]) for payload in results.values())
    print(f"Wrote {total_rules} rules to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
