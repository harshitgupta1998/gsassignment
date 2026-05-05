import json
from pathlib import Path
from typing import Any

from validator import validate_rule
import json
from typing import Tuple


EXPECTED_RULE_COUNTS = {
    "sample_1": 7,
    "sample_2": 5,
    "sample_3": 5,
}


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_sample(sample_name: str, payload: dict[str, Any], failures: list[str]) -> None:
    rules = payload.get("rules", [])
    # Basic count check
    expected = EXPECTED_RULE_COUNTS.get(sample_name)
    actual = len(rules)
    if expected is not None and actual < expected:
        failures.append(f"{sample_name}: expected at least {expected} rules, got {actual}")

    # Unique ID check
    ids = [r.get("id") for r in rules]
    dup_ids = set([i for i in ids if ids.count(i) > 1])
    if dup_ids:
        failures.append(f"{sample_name}: duplicate rule ids found: {', '.join(map(str, dup_ids))}")

    # Category breakdown
    categories: dict[str, int] = {}
    for r in rules:
        categories[r.get("category", "(none)")] = categories.get(r.get("category", "(none)"), 0) + 1
    print(f"{sample_name}: {actual} rules — categories: {categories}")

    # Rule-level validation
    for r in rules:
        rid = r.get("id", "<no-id>")
        warnings = validate_rule(r)
        for w in warnings:
            failures.append(f"{sample_name}/{rid}: {w}")

    # Duplicate raw_text detection
    raw_texts = [r.get("raw_text", "") for r in rules]
    dup_texts = set([t for t in raw_texts if raw_texts.count(t) > 1 and t.strip()])
    if dup_texts:
        failures.append(f"{sample_name}: duplicate raw_text detected for {len(dup_texts)} text(s)")

    # Low-confidence LLM rules
    low_conf: list[str] = []
    for r in rules:
        ex = r.get("extraction") or {}
        method = ex.get("method")
        conf = ex.get("confidence")
        if method == "llm" and isinstance(conf, (int, float)) and conf < 0.5:
            low_conf.append(r.get("id", "<no-id>"))
    if low_conf:
        failures.append(f"{sample_name}: {len(low_conf)} llm-extracted rules with low confidence: {', '.join(low_conf[:5])}")


def rule_key(rule: dict[str, Any]) -> Tuple[str, str, str, str]:
    """Create a comparable key for a rule: (subject, operator, value_json, unit)"""
    subj = (rule.get("subject") or "").strip().lower()
    op = (rule.get("operator") or "").strip().lower()
    val = rule.get("value")
    try:
        # JSON-stable representation for value (handles list/number/string/null)
        val_json = json.dumps(val, sort_keys=True, separators=(",", ":"))
    except Exception:
        val_json = str(val)
    unit = (rule.get("unit") or "").strip().lower()
    return subj, op, val_json, unit


def evaluate_against_ground_truth(sample_name: str, payload: dict[str, Any]) -> Tuple[int, int, int]:
    """Return (tp, fp, fn) when ground truth is available under backend/ground_truth/{sample}.json
    If no ground truth file, returns (-1, -1, -1).
    """
    gt_path = Path(__file__).resolve().parent / "ground_truth" / f"{sample_name}.json"
    if not gt_path.exists():
        return -1, -1, -1
    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    gold_rules = gt.get("rules", [])
    pred_rules = payload.get("rules", [])

    gold_keys = {rule_key(r) for r in gold_rules}
    pred_keys = {rule_key(r) for r in pred_rules}

    tp = len(pred_keys & gold_keys)
    fp = len(pred_keys - gold_keys)
    fn = len(gold_keys - pred_keys)
    return tp, fp, fn


def main() -> None:
    output_dir = Path(__file__).resolve().parent / "output"
    failures: list[str] = []
    total_tp = total_fp = total_fn = 0
    evaluated_samples = 0

    # gather sample output files (falls back to EXPECTED_RULE_COUNTS keys)
    sample_keys = list(EXPECTED_RULE_COUNTS.keys())
    for sample in sample_keys:
        path = output_dir / f"{sample}.json"
        if not path.exists():
            failures.append(f"{sample}: missing output file")
            continue
        payload = load_payload(path)
        analyze_sample(sample, payload, failures)
        tp, fp, fn = evaluate_against_ground_truth(sample, payload)
        if tp >= 0:
            evaluated_samples += 1
            total_tp += tp
            total_fp += fp
            total_fn += fn
            prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
            rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            print(f"After {evaluated_samples} sample(s): micro-precision={prec:.3f}, micro-recall={rec:.3f}, micro-f1={f1:.3f}")

    if failures:
        print("Evaluation failed:")
        for f in failures:
            print(f"- {f}")
        raise SystemExit(1)

    print("Evaluation passed: all checks succeeded.")


if __name__ == "__main__":
    main()
