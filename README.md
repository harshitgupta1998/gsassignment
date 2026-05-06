# Policy Rule Extraction

This repo contains a small backend pipeline that extracts structured JSON rules from policy document excerpts. The default architecture is LLM-first with deterministic validation and fallback.

## Repository Layout

```text
backend/
  extract.py                 # CLI entrypoint
  samples.py                 # input excerpts
  llm_extractor.py           # primary LLM extraction path
  deterministic_extractor.py # fallback extractor and baseline
  validator.py               # schema and consistency checks
  normalizer.py              # money, percentage, operator helpers
  parser.py                  # section clause splitting
  evaluator.py               # simple bonus evaluation harness
  output/                    # generated JSON output
frontend/
  index.html                 # dependency-free analyst review UI
  app.js
  styles.css
  README.md
```

## How To Run

The deterministic path has no external dependencies:

```bash
python3 backend/extract.py --mode deterministic
```

The default hybrid mode tries the LLM first and falls back to deterministic extraction if no API key is available, the LLM fails, or validation finds major issues:

```bash
python3 backend/extract.py
```

To use the LLM path, install dependencies and set an API key:

```bash
python3 -m pip install -r backend/requirements.txt
export OPENAI_API_KEY="your-api-key"
python3 backend/extract.py --mode hybrid
```

Optional model override:

```bash
export OPENAI_MODEL="gpt-4o-mini"
```

Run the simple evaluation harness:

```bash
python3 backend/evaluator.py
```

Run the optional frontend review UI:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/frontend/
```

Generated files are written to:

```text
backend/output/sample_1.json
backend/output/sample_2.json
backend/output/sample_3.json
backend/output/all_rules.json

Samples directory
-----------------

The sample source texts are now stored as individual text files in `backend/samples/`.
This makes it easier to add or edit samples without touching Python code. The project will load these files at import-time via `backend/samples.py` and expose them as the `SAMPLES` mapping used by `extract.py`.

To add a new sample:

1. Create a file named `backend/samples/sample_N.txt` (where `sample_N` is the key you will use).
2. Update `backend/samples.py` if you want a different title, section, or category for the new key (the file loader expects a filename that matches the `SAMPLES` key).

Run extraction for a single sample:

```bash
python3 backend/extract.py --sample sample_1
```

Run the helper that performs extraction then serves the frontend (creates `.server.pid`):

```bash
./run.sh --mode hybrid --port 8000
```

Notes
-----
- Keep `.env` out of version control — there is an `.env.example` showing the expected variables (copy it to `.env` when you need to run LLM mode).
- For meaningful evaluation, replace `backend/ground_truth/*.json` with human-reviewed ground-truth files rather than the extractor outputs.
```

## Approach

I used a hybrid pipeline:

1. Split each document into clauses such as `(a)` or `(iii)`.
2. Send the clauses to an LLM with a strict JSON schema prompt.
3. Validate the returned rules for required fields, controlled operators, conditional language, and numeric traceability.
4. Fall back to deterministic extraction if the LLM path fails or looks incomplete.
5. Write both per-document JSON and a combined rule file.

I chose this because policy text is semantic. A pure regex solution can extract simple thresholds, but it struggles when the sentence contains conditions, exceptions, or multiple constraints. At the same time, an LLM by itself is not enough: downstream systems need stable fields, normalized values, and confidence that numbers were not hallucinated. The deterministic layer gives the pipeline a runnable baseline and a validation guardrail.

## Schema Design

Each rule contains normalized fields plus the original source text:

- `subject`: what the rule constrains
- `operator`: controlled operator such as `>=`, `<=`, `=`, `required`
- `value` and `unit`: normalized threshold or fee value
- `scope`: applicant, policy, portfolio, payment, or application
- `condition`: when the rule applies
- `exception`: alternate thresholds, caps, floors, or exception logic
- `basis`: denominator or calculation basis, such as total portfolio value
- `raw_text`: source clause for analyst review and auditability
- `extraction`: method, confidence, and notes

Keeping `raw_text` is important because analysts need traceability. The structured fields are useful for downstream systems, but the source clause is the audit trail.

## What LLMs Do Well Here

LLMs are useful for clauses where the meaning is not just a nearby number and keyword.

Sample 1(c) has two related rules in one clause: applicant credit score must be at least 680, and no more than 15% of portfolio value may come from applicants with scores between 680 and 700. A regex can find the numbers, but an LLM is better at understanding that the 15% constraint is portfolio-level rather than applicant-level.

Sample 1(g) has an exception: annual income must be at least $35,000 unless the applicant is in an approved assistance program, in which case the minimum is $25,000. LLMs are good at mapping this into a base rule plus exception.

Sample 3(d) says the fee equals 3 months of the annual service fee if the policy is cancelled within the first 24 months. That is not just a dollar or percentage threshold; it is a calculated fee with a condition.

## Where LLMs Struggle

LLMs can miss or merge constraints when a clause contains several numbers. Sample 1(c) contains 680, 15%, 680, and 700; a weak extraction may return only the credit score rule and omit the portfolio cap.

LLMs can also normalize operators inconsistently. For example, “shall not exceed,” “no more than,” and “not be less than” should become `<=`, `<=`, and `>=`. The validator and normalizer help keep that consistent.

Finally, LLMs may produce plausible fields that are not directly supported by the source. The validation layer checks that numeric values are traceable to the raw clause and warns when conditional language like “unless,” “provided that,” “if,” or “subject to” appears without a condition or exception.

## Evaluation Plan For 500 Documents

For a larger rollout, I would create a ground truth dataset labeled by analysts. The evaluation should measure:

- Rule detection recall: did the pipeline find every rule?
- Field-level precision and recall for subject, operator, value, unit, scope, condition, and exception.
- Split and merge errors: did one clause become too many or too few rules?
- Numeric accuracy: did every extracted threshold match the source?
- Exception accuracy: did conditional and exception clauses preserve the right logic?
- Category accuracy: eligibility, concentration limit, fee, and other rule types.

I would sample documents across policy types and complexity levels, then reserve a blind test set. For production, I would also track analyst override rates and build regression tests from every corrected extraction.

## Production Improvements

For production I would add:

- Document ingestion for PDF, DOCX, OCR, and HTML.
- Source-span offsets so every extracted field links to exact text.
- JSON Schema or Pydantic validation with versioned schemas.
- LLM structured outputs or function calling.
- Confidence scoring based on model output, validator warnings, and deterministic agreement.
- Human review UI for low-confidence rules.
- Batch processing with retries, logging, and cost tracking.
- A regression suite built from analyst-reviewed documents.
- A policy ontology so subjects and categories are standardized across customers.

## Frontend

The `frontend/` folder contains a small static analyst review interface. It loads `backend/output/all_rules.json`, lets a reviewer switch between sample documents, filter/search extracted rules, inspect validation notes, and view each rule beside the source clause that produced it. It has no build step or JavaScript dependencies.
