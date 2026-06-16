#!/usr/bin/env python3
"""Build the OKF (Open Knowledge Format) wiki from review JSON files.

Projects the structured reviews into a graph of cross-linked markdown concept
documents under ``okf/``:

    okf/papers/<slug>.md          one Paper concept per reviewed article
    okf/health-outcomes/<slug>.md aggregated Concept pages (which papers study X)
    okf/exposures/<slug>.md
    okf/resilience/<slug>.md
    okf/populations/<slug>.md
    okf/regions/<slug>.md
    okf/index.md                  catalog (regenerated)
    okf/log.md                    append-only ingest history

The reviews/, pdfs/ and duckdb/ artifacts are gitignored as regenerable, so the
committed OKF markdown is the durable, human- and agent-readable knowledge layer.

Generated concept pages preserve any human/agent-curated content placed under a
``## Curator notes`` heading, so the wiki compounds rather than being clobbered.

Usage:
    python scripts/build_okf.py                 # from reviews/
    python scripts/build_okf.py --include-examples   # also examples/reviews/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from scorch import config, okf, records  # noqa: E402

CURATOR_HEADING = "## Curator notes"

# Concept dimensions: each paper contributes labels along these axes, and every
# label becomes an aggregated concept page listing the papers that touch it.
DIMENSIONS: dict[str, dict] = {
    "health-outcomes": {"kind": "category", "path": ("health_outcomes", "health_outcome_categories"),
                        "label": "Health outcome", "type": "health-outcome"},
    "exposures": {"kind": "category", "path": ("exposures", "exposure_categories"),
                 "label": "Exposure", "type": "exposure"},
    "resilience": {"kind": "category", "path": ("climate_resilience", "resilience_categories"),
                  "label": "Resilience measure", "type": "resilience-measure"},
    "populations": {"kind": "objects", "path": ("vulnerable_populations",), "key": "population_group",
                   "label": "Vulnerable population", "type": "population"},
    "regions": {"kind": "strings", "path": ("spatial_temporal", "geographic_areas"),
               "label": "Region", "type": "region"},
}


def load_reviews(include_examples: bool) -> list[dict]:
    dirs = [config.REVIEW_DIR]
    if include_examples:
        dirs.append(config.BASE_DIR / "examples" / "reviews")
    reviews = []
    for d in dirs:
        for path in records.iter_review_files(d):
            with open(path, "r", encoding="utf-8") as fh:
                reviews.append(json.load(fh))
    return reviews


def paper_slug(data: dict) -> str:
    fn = records.get_path(data, "extraction_metadata", "source_pdf_filename") or "paper"
    return okf.slugify(Path(fn).stem)


def concept_labels(data: dict, dim: dict) -> list[str]:
    value = records.get_path(data, *dim["path"], default=[] if dim["kind"] != "category" else {})
    if dim["kind"] == "category":
        return [okf.humanize(k) for k, v in (value or {}).items() if v is True]
    if dim["kind"] == "objects":
        return [o.get(dim["key"], "").strip() for o in (value or []) if o.get(dim["key"])]
    if dim["kind"] == "strings":
        return [s.strip() for s in (value or []) if isinstance(s, str) and s.strip()]
    return []


def extract_curator_notes(path: Path) -> str:
    if not path.exists():
        return ""
    _, body = okf.read_doc(path)
    idx = body.find(CURATOR_HEADING)
    return body[idx:].rstrip() + "\n" if idx != -1 else ""


def build_paper_page(data: dict, okf_dir: Path) -> dict:
    slug = paper_slug(data)
    papers_dir = okf_dir / "papers"
    self_path = papers_dir / f"{slug}.md"

    title = records.get_path(data, "metadata", "title") or "Untitled"
    is_example = "example" in (records.get_path(data, "extraction_metadata", "extractor_agent") or "").lower()

    labels_by_dim = {name: sorted(set(concept_labels(data, dim))) for name, dim in DIMENSIONS.items()}

    meta = {
        "type": "Paper",
        "title": title,
        "citation": records.get_path(data, "metadata", "citation_apa7"),
        "publication_year": records.get_path(data, "spatial_temporal", "publication_year"),
        "study_design": records.get_path(data, "study_characteristics", "study_design"),
        "setting": records.get_path(data, "study_characteristics", "setting"),
        "relevance_rating": records.get_path(data, "overall_relevance", "relevance_rating"),
        "geographic_areas": records.get_path(data, "spatial_temporal", "geographic_areas", default=[]),
        "source_pdf": records.get_path(data, "extraction_metadata", "source_pdf_filename"),
        "tags": sorted({okf.slugify(l) for labels in labels_by_dim.values() for l in labels}) or None,
        "status": "example" if is_example else "extracted",
        "timestamp": date.today().isoformat(),
    }

    lines: list[str] = [f"# {title}", ""]
    if is_example:
        lines += ["> **Example record** — synthetic, for demonstration. Not a real extraction.", ""]
    citation = records.get_path(data, "metadata", "citation_apa7")
    if citation:
        lines += [f"*{citation}*", ""]

    summary = records.get_path(data, "summary", "paper_summary")
    if summary and summary != "N/A":
        lines += ["## Summary", "", summary, ""]
    concl = records.get_path(data, "summary", "conclusions_summary")
    if concl and concl != "N/A":
        lines += ["## Conclusions", "", concl, ""]

    effect = records.get_path(data, "associations_effects", "effect_narrative")
    if effect and effect != "N/A":
        lines += ["## Key effect estimates", "", effect, ""]

    # Cross-links to concept pages, grouped by dimension.
    for name, dim in DIMENSIONS.items():
        labels = labels_by_dim[name]
        if not labels:
            continue
        links = ", ".join(
            okf.link(l, okf_dir / name / f"{okf.slugify(l)}.md", from_dir=papers_dir) for l in labels
        )
        lines += [f"## {dim['label']}s", "", links, ""]

    rating = meta["relevance_rating"]
    justification = records.get_path(data, "overall_relevance", "relevance_justification")
    if rating:
        lines += ["## Relevance", "", f"**{rating}.** {justification or ''}".strip(), ""]

    okf.write_doc(self_path, meta, "\n".join(lines))
    return {"slug": slug, "title": title, "rating": rating, "labels": labels_by_dim,
            "year": meta["publication_year"], "example": is_example}


def build_concept_page(dim_name: str, dim: dict, label: str, papers: list[dict], okf_dir: Path) -> None:
    dim_dir = okf_dir / dim_name
    slug = okf.slugify(label)
    self_path = dim_dir / f"{slug}.md"

    meta = {
        "type": "Concept",
        "category": dim["type"],
        "title": label,
        "tags": [dim["type"]],
        "paper_count": len(papers),
        "timestamp": date.today().isoformat(),
    }

    lines = [f"# {label}", "", f"*{dim['label']} concept — {len(papers)} paper(s) in the corpus.*", "",
             "## Studied by", ""]
    for p in sorted(papers, key=lambda x: (x["rating"] != "High", x["title"])):
        rating = f" — {p['rating']} relevance" if p["rating"] else ""
        target = okf_dir / "papers" / (p["slug"] + ".md")
        lines.append(f"- {okf.link(p['title'], target, from_dir=dim_dir)}{rating}")
    lines.append("")

    notes = extract_curator_notes(self_path)
    body = "\n".join(lines) + ("\n" + notes if notes else f"\n{CURATOR_HEADING}\n\n_(Add curated context here; preserved across rebuilds.)_\n")
    okf.write_doc(self_path, meta, body)


def write_index(papers: list[dict], concepts: dict, okf_dir: Path) -> None:
    meta = {"type": "Index", "title": "SCORCH Knowledge Base", "timestamp": date.today().isoformat(),
            "paper_count": len(papers)}
    lines = ["# SCORCH Knowledge Base — Index", "",
             "Open Knowledge Format projection of the SCORCH literature reviews. "
             "Each paper and concept is one markdown document; links form the graph.", "",
             f"**{len(papers)} paper(s)** across "
             + ", ".join(f"{len(v)} {name.replace('-', ' ')}" for name, v in concepts.items() if v) + ".", "",
             "## Conventions & schema", "",
             f"- {okf.link('OKF conventions', okf_dir / 'CONVENTIONS.md', from_dir=okf_dir)}",
             f"- {okf.link('Extraction schema', okf_dir / 'schema' / 'extraction-schema.md', from_dir=okf_dir)}",
             f"- {okf.link('scorch_reviews dataset', okf_dir / 'datasets' / 'scorch-reviews.md', from_dir=okf_dir)}",
             f"- {okf.link('Ingest log', okf_dir / 'log.md', from_dir=okf_dir)}", "",
             "## Papers", ""]
    if papers:
        for p in sorted(papers, key=lambda x: (str(x["year"]), x["title"]), reverse=True):
            tag = " *(example)*" if p["example"] else ""
            target = okf_dir / "papers" / (p["slug"] + ".md")
            lines.append(f"- {okf.link(p['title'], target, from_dir=okf_dir)} ({p['year']}){tag}")
    else:
        lines.append("_No papers yet. Run the extraction pipeline, then rebuild._")
    lines.append("")

    for name, dim in DIMENSIONS.items():
        items = concepts.get(name, {})
        if not items:
            continue
        lines += [f"## {dim['label']}s", ""]
        for label in sorted(items):
            lines.append(f"- {okf.link(label, okf_dir / name / f'{okf.slugify(label)}.md', from_dir=okf_dir)} "
                        f"({len(items[label])})")
        lines.append("")
    okf.write_doc(okf_dir / "index.md", meta, "\n".join(lines))


def update_log(papers: list[dict], okf_dir: Path) -> None:
    log_path = okf_dir / "log.md"
    header = "# Ingest log\n\nAppend-only, most recent last. One line per paper added to the wiki.\n"
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else header
    today = date.today().isoformat()
    added = []
    for p in papers:
        marker = f"papers/{p['slug']}.md"
        if marker not in existing:
            added.append(f"## [{today}] ingest | {p['title']}\n- {marker}\n")
    if added:
        log_path.write_text(existing.rstrip() + "\n\n" + "\n".join(added), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the OKF wiki from reviews.")
    parser.add_argument("--include-examples", action="store_true",
                       help="Also project examples/reviews/ (synthetic demo records).")
    args = parser.parse_args()

    reviews = load_reviews(args.include_examples)
    okf_dir = config.OKF_DIR
    okf_dir.mkdir(exist_ok=True)

    # Paper pages are fully generated (no curated content) -> safe to wipe.
    # Concept pages may carry "## Curator notes" -> overwrite in place and prune
    # stale ones afterward, so curated prose survives the rebuild.
    shutil.rmtree(okf_dir / "papers", ignore_errors=True)

    papers: list[dict] = []
    concepts: dict[str, dict[str, list[dict]]] = {name: {} for name in DIMENSIONS}

    for data in reviews:
        rec = build_paper_page(data, okf_dir)
        papers.append(rec)
        for name in DIMENSIONS:
            for label in rec["labels"][name]:
                concepts[name].setdefault(label, []).append(rec)

    for name, dim in DIMENSIONS.items():
        for label, ps in concepts[name].items():
            build_concept_page(name, dim, label, ps, okf_dir)
        # Prune concept pages for labels no longer present in the corpus.
        dim_dir = okf_dir / name
        if dim_dir.exists():
            keep = {okf.slugify(label) for label in concepts[name]}
            for stale in dim_dir.glob("*.md"):
                if stale.stem not in keep:
                    stale.unlink()

    write_index(papers, concepts, okf_dir)
    update_log(papers, okf_dir)

    total_concepts = sum(len(v) for v in concepts.values())
    print(f"✓ OKF wiki built: {len(papers)} paper(s), {total_concepts} concept page(s) → {okf_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
