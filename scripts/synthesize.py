#!/usr/bin/env python3
"""Generate cited evidence syntheses for OKF concept pages (STORM-inspired).

This is a small, native re-implementation of the *pattern* behind STORM
(Stanford's cited-synthesis system) — emphatically NOT the STORM project itself.
It runs entirely on the Anthropic Claude API stack already used in this repo.

For a target concept page (e.g. ``okf/exposures/heat.md``) it:

  1. Reads the page's ``## Studied by`` section and parses the ``../papers/<slug>.md``
     links to determine the evidence set.
  2. Maps each paper slug back to its review JSON by matching
     ``slugify(Path(source_pdf_filename).stem)`` across reviews/ + examples/reviews/.
  3. Asks ``config.SYNTHESIS_MODEL`` for a short, inline-cited synthesis of those
     papers' summaries (agreements, tensions, gaps — no invented findings).
  4. Writes the result back into the page under ``## Curator notes`` (the section
     scripts/build_okf.py preserves across rebuilds), so the wiki compounds.

Usage:
    python scripts/synthesize.py --dimension exposures --concept heat
    python scripts/synthesize.py --all              # every concept page under okf/
    python scripts/synthesize.py --all --dry-run    # list targets, no API call
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from scorch import config, okf, records  # noqa: E402

CURATOR_HEADING = "## Curator notes"
DIMENSIONS = ["health-outcomes", "exposures", "resilience", "populations", "regions"]
# Links in the "## Studied by" section look like ../papers/<slug>.md
PAPER_LINK_RE = re.compile(r"\.\./papers/([a-z0-9-]+)\.md")


def index_reviews() -> dict[str, dict]:
    """Map paper slug -> review dict, across reviews/ and examples/reviews/."""
    index: dict[str, dict] = {}
    for review_dir in (config.REVIEW_DIR, config.BASE_DIR / "examples" / "reviews"):
        for path in records.iter_review_files(review_dir):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            fn = records.get_path(data, "extraction_metadata", "source_pdf_filename") or path.stem
            index.setdefault(okf.slugify(Path(fn).stem), data)
    return index


def studied_by_slugs(body: str) -> list[str]:
    """Parse paper slugs from a concept page's '## Studied by' section."""
    start = body.find("## Studied by")
    if start == -1:
        return []
    # Section ends at the next top-level heading (e.g. ## Curator notes) or EOF.
    rest = body[start + len("## Studied by"):]
    end = rest.find("\n## ")
    section = rest if end == -1 else rest[:end]
    seen: list[str] = []
    for slug in PAPER_LINK_RE.findall(section):
        if slug not in seen:
            seen.append(slug)
    return seen


def gather_evidence(slugs: list[str], review_index: dict[str, dict]) -> list[dict]:
    """Collect title/citation/summary/effect for each matched paper slug."""
    evidence: list[dict] = []
    for slug in slugs:
        data = review_index.get(slug)
        if data is None:
            continue
        evidence.append({
            "title": records.get_path(data, "metadata", "title") or "Untitled",
            "citation": records.get_path(data, "metadata", "citation_apa7") or "N/A",
            "summary": records.get_path(data, "summary", "paper_summary") or "N/A",
            "effect": records.get_path(data, "associations_effects", "effect_narrative") or "N/A",
        })
    return evidence


def build_prompt(concept_title: str, evidence: list[dict]) -> str:
    blocks = []
    for i, e in enumerate(evidence, start=1):
        blocks.append(
            f"Paper {i}:\n"
            f"  Title: {e['title']}\n"
            f"  Citation: {e['citation']}\n"
            f"  Summary: {e['summary']}\n"
            f"  Key effects: {e['effect']}"
        )
    evidence_text = "\n\n".join(blocks)
    return (
        f"Write a 3-5 sentence evidence synthesis for the concept '{concept_title}' "
        "for the SCORCH arid-Southwest climate-health review, using ONLY the provided "
        "paper summaries. Cite papers inline by first-author/year drawn from their "
        "citation. Note agreements, tensions, and gaps. Do not invent findings.\n\n"
        f"Provided papers:\n\n{evidence_text}"
    )


def synthesize(concept_title: str, evidence: list[dict]) -> tuple[str, float]:
    """Call the synthesis model. Returns (text, estimated_cost_usd)."""
    from anthropic import Anthropic

    client = Anthropic()
    prompt = build_prompt(concept_title, evidence)
    message = client.messages.create(
        model=config.SYNTHESIS_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in message.content if block.type == "text").strip()
    cost = config.estimate_cost(
        config.SYNTHESIS_MODEL, message.usage.input_tokens, message.usage.output_tokens
    )
    return text, cost


def write_synthesis(path: Path, text: str) -> None:
    """Replace the page's '## Curator notes' section body with the synthesis."""
    meta, body = okf.read_doc(path)
    idx = body.find(CURATOR_HEADING)
    head = body[:idx].rstrip() if idx != -1 else body.rstrip()
    note = (
        f"{CURATOR_HEADING}\n\n"
        f"_Synthesis (STORM-inspired, model-generated {date.today().isoformat()}):_\n\n"
        f"{text}\n"
    )
    okf.write_doc(path, meta, f"{head}\n\n{note}")


def resolve_targets(args: argparse.Namespace) -> list[Path]:
    okf_dir = config.OKF_DIR
    if args.all:
        targets: list[Path] = []
        for dim in DIMENSIONS:
            targets.extend(sorted((okf_dir / dim).glob("*.md")))
        return targets
    page = okf_dir / args.dimension / f"{okf.slugify(args.concept)}.md"
    return [page]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate cited syntheses for OKF concept pages (STORM-inspired)."
    )
    parser.add_argument("--dimension", choices=DIMENSIONS, help="Concept dimension to target.")
    parser.add_argument("--concept", help="Concept slug (or title) within the dimension.")
    parser.add_argument("--all", action="store_true", help="Process every concept page under okf/.")
    parser.add_argument("--dry-run", action="store_true", help="List targets and evidence; no API call.")
    args = parser.parse_args()

    if not args.all and not (args.dimension and args.concept):
        parser.error("provide --all, or both --dimension and --concept")

    review_index = index_reviews()
    targets = resolve_targets(args)
    total_cost = 0.0
    wrote = 0

    for path in targets:
        if not path.exists():
            print(f"! skip (no such page): {path}")
            continue
        meta, body = okf.read_doc(path)
        title = meta.get("title") or path.stem
        slugs = studied_by_slugs(body)
        evidence = gather_evidence(slugs, review_index)

        if not evidence:
            print(f"- skip (no matched evidence): {title} [{path.relative_to(config.OKF_DIR.parent)}]")
            continue

        if args.dry_run:
            cites = ", ".join(e["citation"][:40] for e in evidence)
            print(f"would synthesize: {title} <- {len(evidence)} paper(s): {cites}")
            continue

        text, cost = synthesize(title, evidence)
        total_cost += cost
        write_synthesis(path, text)
        wrote += 1
        print(f"✓ {title}: synthesized from {len(evidence)} paper(s) (~${cost:.4f})")

    if args.dry_run:
        print(f"\n[dry run] {len(targets)} target page(s) inspected; no API calls, no writes.")
    else:
        print(f"\n✓ wrote {wrote} synthesis section(s); estimated total cost ~${total_cost:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
