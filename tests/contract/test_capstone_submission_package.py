from __future__ import annotations

import json
import struct
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CAPSTONE_DIR = REPO_ROOT / "docs" / "capstone"
SLIDES_DIR = CAPSTONE_DIR / "media" / "slides"
ONE_SENTENCE_SUMMARY = (
    "TradePilot Sentinel turns portfolio, market, and risk evidence into "
    "approval-gated paper-trading decisions for personal investors."
)


def _png_dimensions(path: Path) -> tuple[int, int]:
    payload = path.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", payload[16:24])


def test_capstone_writeup_and_public_evidence_are_submission_ready() -> None:
    writeup = (CAPSTONE_DIR / "writeup.md").read_text(encoding="utf-8")
    assert len(writeup.split()) <= 2_500
    assert len(ONE_SENTENCE_SUMMARY) <= 140
    assert "**Track:** Concierge Agents" in writeup
    assert ONE_SENTENCE_SUMMARY in " ".join(writeup.split())
    assert "Agents for Business" not in writeup

    capstone_readme = (CAPSTONE_DIR / "README.md").read_text(encoding="utf-8")
    assert ONE_SENTENCE_SUMMARY in " ".join(capstone_readme.split())

    summary = json.loads(
        (CAPSTONE_DIR / "evidence" / "eval-summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["product"] == "TradePilot Sentinel"
    assert summary["inference_cases_completed"] == 15
    assert summary["deterministic_triage"]["failure_count"] == 0
    assert summary["deterministic_triage"]["critical_failure_count"] == 0

    assert (CAPSTONE_DIR / "media" / "product" / "dashboard.png").is_file()
    assert (
        CAPSTONE_DIR
        / "media"
        / "product"
        / "approval-gated-paper-report.png"
    ).is_file()


def test_capstone_slide_assets_are_16_by_9_and_deck_has_notes() -> None:
    slide_names = [
        "01-cover.png",
        "02-problem-value.png",
        "03-system-architecture.png",
        "04-decision-intelligence.png",
        "05-agentic-workflow.png",
        "06-safety-model.png",
        "07-working-product-evidence.png",
        "08-evaluation-deployability.png",
        "09-capstone-conclusion.png",
    ]
    assert [_png_dimensions(SLIDES_DIR / name) for name in slide_names] == [
        (1280, 720)
    ] * 9

    deck = CAPSTONE_DIR / "TradePilot-Sentinel-Capstone.pptx"
    with zipfile.ZipFile(deck) as archive:
        names = archive.namelist()
        deck_xml = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in names
            if name.endswith(".xml")
        )
    slide_xml = [
        name
        for name in names
        if name.startswith("ppt/slides/slide") and name.endswith(".xml")
    ]
    notes_xml = [
        name
        for name in names
        if name.startswith("ppt/notesSlides/notesSlide")
        and name.endswith(".xml")
    ]
    assert len(slide_xml) == 9
    assert len(notes_xml) == 9
    assert "Concierge Agents" in deck_xml
    assert "Agents for Business" not in deck_xml
