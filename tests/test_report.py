from pathlib import Path

import report

ROOT = Path(__file__).resolve().parents[1]


def test_report_is_generated_from_outputs():
    assert (ROOT / "REPORT.md").read_text() == report.build(ROOT / "outputs")
