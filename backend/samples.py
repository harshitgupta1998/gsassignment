from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = ROOT / "samples"

def _read_sample(name: str) -> str:
    path = SAMPLES_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Sample file not found: {path}")
    return path.read_text(encoding="utf-8").strip()

SAMPLES = {
    "sample_1": {
        "title": "Eligibility Criteria",
        "section": "SECTION 5.1 ELIGIBILITY CRITERIA",
        "category": "eligibility",
        "text": _read_sample("sample_1"),
    },
    "sample_2": {
        "title": "Concentration Limits",
        "section": "SECTION 7.3 PORTFOLIO CONCENTRATION LIMITS",
        "category": "concentration_limit",
        "text": _read_sample("sample_2"),
    },
    "sample_3": {
        "title": "Fee Schedule",
        "section": "SECTION 12.2 FEES AND CHARGES",
        "category": "fee",
        "text": _read_sample("sample_3"),
    },
}
