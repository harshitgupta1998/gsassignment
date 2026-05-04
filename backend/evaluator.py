import json
from pathlib import Path


EXPECTED_RULE_COUNTS = {
    "sample_1": 9,
    "sample_2": 5,
    "sample_3": 5,
}


def main() -> None:
    output_dir = Path(__file__).resolve().parent / "output"
    failures: list[str] = []
    for sample, expected_count in EXPECTED_RULE_COUNTS.items():
        path = output_dir / f"{sample}.json"
        if not path.exists():
            failures.append(f"{sample}: missing output file")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual_count = len(payload.get("rules", []))
        if actual_count < expected_count:
            failures.append(f"{sample}: expected at least {expected_count} rules, got {actual_count}")

    if failures:
        print("Evaluation failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("Evaluation passed: all samples produced the expected minimum rule counts.")


if __name__ == "__main__":
    main()
