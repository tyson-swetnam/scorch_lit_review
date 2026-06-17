#!/usr/bin/env python3
"""Export PDF reports for the SCORCH literature corpus into ``reviews/``.

Generates:
  * ``reviews/scorch_duckdb_summary.pdf`` — an analytical summary built from
    **live** DuckDB queries (so it cannot drift from the database).
  * ``reviews/<stem>_review.pdf``         — a complete, human-readable rendering
    of every ``reviews/<stem>_review.json`` extraction.

Pure-Python (reportlab); needs no system PDF engine (no LaTeX/weasyprint/wkhtmltopdf).
Run from the repo root with the project venv:

    .venv/bin/python scripts/export_review_pdfs.py

No API key required. ``reviews/`` is gitignored/regenerable, so these PDFs are
regenerable artifacts like the JSON and the DuckDB file.
"""

from __future__ import annotations

# Import duckdb before any sys.path juggling so the top-level ``duckdb/`` data
# directory can never shadow the library (repo convention).
import duckdb

import json
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
)

BASE = Path(__file__).resolve().parent.parent
REVIEWS = BASE / "reviews"
DB_PATH = BASE / "duckdb" / "scorch_reviews.duckdb"

# duckdb is already imported above, so the repo root can safely go on sys.path now.
import sys  # noqa: E402
sys.path.append(str(BASE))
from scorch import records  # noqa: E402

USABLE = 6.5 * inch  # letter width (8.5in) minus two 1in margins
TODAY = date.today().isoformat()

# Brand-ish palette
NAVY = colors.HexColor("#1a3a5c")
TEAL = colors.HexColor("#2c7a7b")
LIGHT = colors.HexColor("#eef3f7")
GREY = colors.HexColor("#666666")
GREEN = colors.HexColor("#216e39")

# --- typographic normalization (keep ° and accents; tame smart punctuation) ---
_TRANS = {
    0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"',
    0x2013: "-", 0x2014: "-", 0x2026: "...", 0x00A0: " ",
}


def clean(s: str) -> str:
    return str(s).translate(_TRANS)


def esc(s) -> str:
    return escape(clean(s))


# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
def make_styles():
    ss = getSampleStyleSheet()
    out = {}
    out["title"] = ParagraphStyle("scorchTitle", parent=ss["Title"],
                                  fontSize=20, leading=24, textColor=NAVY, spaceAfter=4)
    out["subtitle"] = ParagraphStyle("scorchSub", parent=ss["Normal"],
                                     fontSize=10, leading=13, textColor=GREY, spaceAfter=2)
    out["h2"] = ParagraphStyle("scorchH2", parent=ss["Heading2"],
                               fontSize=13, leading=16, textColor=NAVY,
                               spaceBefore=14, spaceAfter=4)
    out["h3"] = ParagraphStyle("scorchH3", parent=ss["Heading3"],
                               fontSize=10.5, leading=13, textColor=TEAL,
                               spaceBefore=8, spaceAfter=2)
    out["body"] = ParagraphStyle("scorchBody", parent=ss["Normal"],
                                 fontSize=9, leading=12, spaceAfter=4)
    out["cell"] = ParagraphStyle("scorchCell", parent=ss["Normal"], fontSize=8.5, leading=11)
    out["cellb"] = ParagraphStyle("scorchCellB", parent=ss["Normal"],
                                  fontSize=8.5, leading=11, fontName="Helvetica-Bold")
    out["cellh"] = ParagraphStyle("scorchCellH", parent=ss["Normal"],
                                  fontSize=8.5, leading=11, fontName="Helvetica-Bold",
                                  textColor=colors.white)
    out["bullet"] = ParagraphStyle("scorchBullet", parent=ss["Normal"],
                                   fontSize=9, leading=12)
    out["small"] = ParagraphStyle("scorchSmall", parent=ss["Normal"],
                                  fontSize=8, leading=10.5, textColor=GREY)
    return out


# --------------------------------------------------------------------------- #
# Generic flowable builders
# --------------------------------------------------------------------------- #
def kv_table(rows, S, label_w=1.9 * inch):
    """2-column [label, value] table."""
    data = [[Paragraph(f"<b>{esc(k)}</b>", S["cell"]), Paragraph(esc(v), S["cell"])]
            for k, v in rows]
    t = Table(data, colWidths=[label_w, USABLE - label_w], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfd8e0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def grid_table(headers, rows, S, weights=None):
    """Header + body table for a list of records."""
    n = len(headers)
    if weights is None:
        weights = [1] * n
    tot = sum(weights)
    widths = [USABLE * w / tot for w in weights]
    data = [[Paragraph(esc(h), S["cellh"]) for h in headers]]
    for r in rows:
        data.append([Paragraph(esc(c), S["cell"]) for c in r])
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfd8e0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def bullets(items, S):
    li = [ListItem(Paragraph(esc(x), S["bullet"]), leftIndent=10) for x in items]
    return ListFlowable(li, bulletType="bullet", start="•", leftIndent=14)


def humanize(key: str) -> str:
    acron = {"Apa7": "APA7", "Us": "US", "Sw": "SW", "Scorch": "SCORCH",
             "Id": "ID", "Pdf": "PDF", "Q1": "Q1", "Q2": "Q2", "Q3": "Q3",
             "Obj": "Obj", "Na": "N/A", "Emap": "EMAP", "Usgcrp": "USGCRP",
             "Epa": "EPA", "Ada": "ADA"}
    words = key.replace("_", " ").split()
    out = []
    for w in words:
        t = w.capitalize()
        out.append(acron.get(t, t))
    return " ".join(out)


def fmt_scalar(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if v == "":
        return "(empty)"
    return str(v)


def is_scalar(v) -> bool:
    return v is None or isinstance(v, (str, int, float, bool))


def render_value(value, story, S):
    """Recursively render any JSON value into flowables (used inside a section)."""
    if isinstance(value, dict):
        scalars = {k: v for k, v in value.items() if is_scalar(v)}
        complex_ = {k: v for k, v in value.items() if not is_scalar(v)}
        if scalars:
            all_bool = all(isinstance(v, bool) for v in scalars.values())
            if all_bool and len(scalars) > 6:
                present = [humanize(k) for k, v in scalars.items() if v]
                absent = [humanize(k) for k, v in scalars.items() if not v]
                story.append(Paragraph(
                    "<b>Present (true):</b> " + (esc(", ".join(present)) if present else "(none)"),
                    S["body"]))
                story.append(Paragraph(
                    "<font color='#888888'><b>Absent (false):</b> "
                    + (esc(", ".join(absent)) if absent else "(none)") + "</font>",
                    S["small"]))
            else:
                story.append(kv_table([(humanize(k), fmt_scalar(v)) for k, v in scalars.items()], S))
                story.append(Spacer(1, 3))
        for k, v in complex_.items():
            story.append(Paragraph(humanize(k), S["h3"]))
            render_value(v, story, S)
    elif isinstance(value, list):
        if not value:
            story.append(Paragraph("<i>(none)</i>", S["small"]))
        elif all(isinstance(x, dict) for x in value):
            headers = []
            for d in value:
                for k in d:
                    if k not in headers:
                        headers.append(k)
            rows = [[fmt_scalar(d.get(h, "")) for h in headers] for d in value]
            weights = [2 if h in ("variable", "population_group", "vulnerability_reasons",
                                  "data_source", "summary") else 1 for h in headers]
            story.append(grid_table([humanize(h) for h in headers], rows, S, weights))
            story.append(Spacer(1, 3))
        else:
            story.append(bullets([fmt_scalar(x) for x in value], S))
    else:
        story.append(Paragraph(esc(fmt_scalar(value)), S["body"]))


def doc_template(path: Path) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path), pagesize=letter,
        leftMargin=1 * inch, rightMargin=1 * inch,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title=path.stem, author="SCORCH Literature Review pipeline",
    )


# --------------------------------------------------------------------------- #
# Per-paper review PDF
# --------------------------------------------------------------------------- #
SECTION_ORDER = [
    "screening", "metadata", "spatial_temporal", "study_characteristics",
    "data_tables", "methods", "health_outcomes", "exposures", "demographics",
    "interventions", "objectives_met", "research_questions",
    "unquantified_health_impacts", "associations_effects", "climate_projections",
    "vulnerable_populations", "climate_resilience", "relevance_summary",
    "limitations_gaps", "overall_relevance", "summary", "extraction_metadata",
]


def _page_label(entry: dict) -> str:
    ps, pe = entry.get("page_start"), entry.get("page_end")
    if ps is None:
        return "p.?"
    if pe and pe != ps:
        return f"pp.{ps}-{pe}"
    return f"p.{ps}"


def build_sources_section(data: dict, S) -> list:
    """A dedicated 'Sources' grid: every evidence_log entry (field, page, quote)."""
    log = (data.get("extraction_metadata") or {}).get("evidence_log") or []
    flow = [Paragraph("Sources / Provenance", S["h2"])]
    if not log:
        flow.append(Paragraph(
            "<i>No per-claim provenance recorded — this review predates schema v1.2. "
            "Re-extract to capture page + verbatim-quote citations.</i>", S["small"]))
        return flow
    flow.append(Paragraph(
        "Source page and verbatim quote backing each substantive value "
        "(from extraction_metadata.evidence_log).", S["small"]))
    rows = []
    for e in log:
        if not isinstance(e, dict):
            continue
        quote = (e.get("quote") or "").replace("\n", " ").strip()
        if len(quote) > 220:
            quote = quote[:217] + "..."
        rows.append([e.get("field_path", ""), _page_label(e), quote])
    flow.append(grid_table(["Field", "Page(s)", "Quote"], rows, S, weights=[2.2, 0.8, 5]))
    return flow


def build_review_pdf(json_path: Path, S) -> Path:
    data = json.loads(json_path.read_text())
    out = REVIEWS / (json_path.stem.replace("_review", "") + "_review.pdf")
    story = []
    meta = data.get("metadata", {})
    title = meta.get("title") or json_path.stem
    rating = data.get("overall_relevance", {}).get("relevance_rating", "N/A")

    # Evidence-coverage stat (schema v1.2): covered / substantive fields.
    n_sub = len(records.walk_substantive_paths(data))
    n_covered = n_sub - len(records.validate_evidence_coverage(data))
    coverage = f"{n_covered}/{n_sub} fields" if n_sub else "n/a"

    story.append(Paragraph("SCORCH Extraction Review", S["subtitle"]))
    story.append(Paragraph(esc(title), S["title"]))
    if meta.get("citation_apa7"):
        story.append(Paragraph(esc(meta["citation_apa7"]), S["small"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>Source PDF:</b> {esc(json_path.stem.replace('_review', '') + '.pdf')} &nbsp;|&nbsp; "
        f"<b>Relevance:</b> {esc(rating)} &nbsp;|&nbsp; "
        f"<b>Schema:</b> v{esc(data.get('extraction_metadata', {}).get('schema_version', '?'))} &nbsp;|&nbsp; "
        f"<b>Evidence coverage:</b> {esc(coverage)} &nbsp;|&nbsp; "
        f"<b>Generated:</b> {TODAY}", S["small"]))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceBefore=6, spaceAfter=2))

    keys = SECTION_ORDER + [k for k in data if k not in SECTION_ORDER]
    for k in keys:
        if k not in data:
            continue
        story.append(Paragraph(humanize(k), S["h2"]))
        value = data[k]
        # evidence_log gets its own Sources section below — don't dump it raw here.
        if k == "extraction_metadata" and isinstance(value, dict):
            value = {kk: vv for kk, vv in value.items() if kk != "evidence_log"}
        render_value(value, story, S)

    # Dedicated provenance appendix.
    story.extend(build_sources_section(data, S))

    doc_template(out).build(story)
    return out


# --------------------------------------------------------------------------- #
# DuckDB summary PDF
# --------------------------------------------------------------------------- #
OBJ_LABELS = {
    "obj_01_climate_health_impacts_arid": "1. Climate-health impacts (arid SW)",
    "obj_02_extreme_weather_health": "2. Extreme-weather effects on health",
    "obj_03_climate_health_forecasts": "3. 50-100 yr climate-health forecasts",
    "obj_04_vulnerable_communities": "4. Vulnerable communities",
    "obj_05_research_gaps": "5. Research gaps",
    "obj_06_solutions_adaptations": "6. Solutions / adaptations",
}


def build_summary_pdf(S) -> Path:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    counts = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
    n_papers = counts.get("reviews", 0)

    profile = con.execute("""
        SELECT source_pdf_filename, title, CAST(publication_year AS VARCHAR),
               spatial_scale, study_design, relevance_rating,
               includes_primary_data_for_region, analyzes_interventions,
               includes_projection_modeling
        FROM reviews ORDER BY TRY_CAST(publication_year AS INTEGER)
    """).fetchall()
    geo = con.execute("SELECT source_pdf_filename, UNNEST(geographic_areas) FROM reviews").fetchall()
    hoc = con.execute("""SELECT category, COUNT(DISTINCT source_pdf_filename)
                         FROM health_outcome_categories GROUP BY 1 ORDER BY 2 DESC, 1""").fetchall()
    exo = con.execute("""SELECT category, COUNT(DISTINCT source_pdf_filename)
                         FROM exposure_categories GROUP BY 1 ORDER BY 2 DESC, 1""").fetchall()
    res = con.execute("""SELECT category, COUNT(DISTINCT source_pdf_filename)
                         FROM resilience_categories GROUP BY 1 ORDER BY 2 DESC, 1""").fetchall()
    vps = con.execute("""SELECT v.source_pdf_filename, COUNT(*)
                         FROM vulnerable_populations v GROUP BY 1 ORDER BY 1""").fetchall()
    if "field_evidence" in tables:
        evidence_cov = con.execute("""
            SELECT r.source_pdf_filename,
                   COUNT(DISTINCT fe.field_path) AS cited_fields,
                   COUNT(fe.field_path) AS quotes
            FROM reviews r LEFT JOIN field_evidence fe USING (source_pdf_filename)
            GROUP BY 1 ORDER BY 1
        """).fetchall()
    else:
        evidence_cov = []
    con.close()

    # objectives come from the source JSON (not stored as DB columns)
    objs = {}
    for jp in sorted(REVIEWS.glob("*_review.json")):
        d = json.loads(jp.read_text())
        objs[d.get("extraction_metadata", {}).get("source_pdf_filename", jp.stem)] = \
            d.get("objectives_met", {})

    story = []
    story.append(Paragraph("SCORCH Literature Review", S["subtitle"]))
    story.append(Paragraph("DuckDB Database Summary", S["title"]))
    story.append(Paragraph(
        f"Generated {TODAY} &nbsp;|&nbsp; corpus: <b>{n_papers}</b> paper(s) &nbsp;|&nbsp; "
        f"source: <font face='Courier'>duckdb/scorch_reviews.duckdb</font> (live query)", S["subtitle"]))
    story.append(Paragraph(
        "Built directly from the database — every count below is queried live, not transcribed.",
        S["small"]))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceBefore=6, spaceAfter=2))

    # 1. Inventory
    story.append(Paragraph("1. Database inventory", S["h2"]))
    story.append(Paragraph(
        "The database is not one flat table: <b>reviews</b> holds one row per paper (PK "
        "<font face='Courier'>source_pdf_filename</font>); array data is fanned into normalized "
        "child tables and long-format category tables that join back on that key.", S["body"]))
    inv_rows = [[t, str(counts[t]) + ("  (empty)" if counts[t] == 0 else "")]
                for t in sorted(tables)]
    story.append(grid_table(["Table", "Rows"], inv_rows, S, weights=[3, 1]))
    empties = [t for t in tables if counts[t] == 0]
    if empties:
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            "Empty by design (not a load error): <b>" + esc(", ".join(sorted(empties)))
            + "</b> — both papers are qualitative meeting summaries with no effect estimates "
            "or cofactor variables.", S["small"]))

    # 2. Per-paper profiles
    story.append(Paragraph("2. Per-paper profiles", S["h2"]))
    headers = ["Paper", "Year", "Spatial scale", "Study design", "Relevance",
               "Primary data", "Interventions", "Projection modeling"]
    rows = []
    for (fn, title, yr, scale, design, rel, prim, interv, proj) in profile:
        rows.append([fn, yr, scale, design, rel,
                     "true" if prim else "false",
                     "true" if interv else "false",
                     "true" if proj else "false"])
    story.append(grid_table(headers, rows, S,
                            weights=[3, 1, 1.6, 2, 1.3, 1.3, 1.3, 1.6]))
    titles = {fn: title for (fn, title, *_rest) in profile}
    story.append(Spacer(1, 3))
    for fn, ttl in titles.items():
        story.append(Paragraph(f"<b>{esc(fn)}</b>: {esc(ttl)}", S["small"]))

    # 3. Geographic coverage
    story.append(Paragraph("3. Geographic coverage", S["h2"]))
    by_paper = {}
    for fn, area in geo:
        by_paper.setdefault(fn, []).append(area)
    for fn, areas in by_paper.items():
        story.append(Paragraph(f"<b>{esc(fn)}</b>", S["body"]))
        story.append(bullets(areas, S))
    story.append(Paragraph(
        "All locations are within Arizona — no coverage yet for New Mexico, Nevada, the "
        "California desert, west Texas, or northern Mexico.", S["small"]))

    # 4. Exposures & health outcomes
    story.append(Paragraph("4. Exposures & health-outcome categories", S["h2"]))
    story.append(Paragraph("Exposure categories (papers studying each):", S["h3"]))
    story.append(grid_table(["Exposure category", "# papers"],
                            [[humanize(c), str(n)] for c, n in exo], S, weights=[4, 1]))
    story.append(Paragraph("Health-outcome categories (papers studying each):", S["h3"]))
    story.append(grid_table(["Health-outcome category", "# papers"],
                            [[humanize(c), str(n)] for c, n in hoc], S, weights=[4, 1]))
    if {c for c, _ in hoc} <= {"heat"}:
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            "<b>Hazard monoculture:</b> every health-outcome category present is <i>heat</i> — "
            "no drought, dust/PM, wildfire smoke, flooding, or vector-borne disease yet.", S["small"]))

    # 5. Vulnerable populations
    story.append(Paragraph("5. Vulnerable populations", S["h2"]))
    story.append(grid_table(["Paper", "# vulnerable-population groups"],
                            [[fn, str(n)] for fn, n in vps], S, weights=[3, 1]))

    # 6. Resilience strategies (shared vs unique)
    story.append(Paragraph("6. Resilience / adaptation strategies", S["h2"]))
    res_rows = [[humanize(c), str(n), "SHARED" if n == n_papers and n_papers > 1 else "unique"]
                for c, n in res]
    story.append(grid_table(["Resilience category", "# papers", "Scope"], res_rows, S,
                            weights=[4, 1, 1.3]))

    # 7. SCORCH objective coverage
    story.append(Paragraph("7. SCORCH objective coverage", S["h2"]))
    story.append(Paragraph(
        "Objectives are not stored as DB columns; this matrix is read from each review's "
        "<font face='Courier'>objectives_met</font> block.", S["small"]))
    paper_fns = list(objs.keys())
    headers = ["SCORCH objective"] + paper_fns
    rows = []
    for key, label in OBJ_LABELS.items():
        rows.append([label] + [objs[fn].get(key, "—") for fn in paper_fns])
    story.append(grid_table(headers, rows, S, weights=[3] + [1.6] * len(paper_fns)))

    # 8. Takeaways / gaps (computed)
    story.append(Paragraph("8. Coverage gaps & takeaways", S["h2"]))
    n_proj = sum(1 for *_x, proj in profile if proj)
    gaps = [
        f"Forecasting gap (Objective 3 / Core Question 2): {n_proj} of {n_papers} papers perform "
        "projection modeling — the clearest gap; the only forward-looking datum is an externally "
        "cited (not modeled) projection.",
        "Quantitative-evidence gap: the correlations and cofactor_variables tables are empty — "
        "no effect sizes, confidence intervals, or significance values in the corpus.",
        "Hazard breadth: all exposure/outcome categories are heat; other arid-SW hazards are absent.",
        "Geography: Arizona-only, partitioned into a Phoenix/Maricopa axis and a Tucson/Pima axis "
        "with no overlap — complementary, not redundant.",
        "These are the obvious acquisition targets as the corpus grows; the schema is ready for "
        "quantitative papers (correlations table exists, currently empty).",
    ]
    story.append(bullets(gaps, S))

    # 9. Provenance coverage (schema v1.2)
    story.append(Paragraph("9. Provenance coverage", S["h2"]))
    story.append(Paragraph(
        "Per-claim source provenance stored in <font face='Courier'>field_evidence</font> "
        "(schema v1.2): a page number + verbatim quote for each substantive value.", S["small"]))
    cov_rows = [[fn, str(cited), str(quotes)] for fn, cited, quotes in evidence_cov]
    story.append(grid_table(["Paper", "Cited fields", "Evidence quotes"], cov_rows, S,
                            weights=[3, 1.3, 1.3]))
    zero = [fn for fn, _cited, quotes in evidence_cov if quotes == 0]
    if zero:
        story.append(Spacer(1, 3))
        story.append(Paragraph(
            "<b>No provenance yet:</b> " + esc(", ".join(zero))
            + " — re-extract under schema v1.2 to populate source citations.", S["small"]))

    out = REVIEWS / "scorch_duckdb_summary.pdf"
    doc_template(out).build(story)
    return out


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"DuckDB not found: {DB_PATH}\nRun scripts/convert_to_duckdb.py first.")
    S = make_styles()
    written = [build_summary_pdf(S)]
    for jp in sorted(REVIEWS.glob("*_review.json")):
        written.append(build_review_pdf(jp, S))
    print("Wrote:")
    for p in written:
        kb = p.stat().st_size / 1024
        print(f"  • {p.relative_to(BASE)}  ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
