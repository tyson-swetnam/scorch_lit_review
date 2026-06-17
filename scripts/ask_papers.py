#!/usr/bin/env python3
"""Citation-grounded Q&A over the SCORCH corpus (PaperQA2-inspired).

A small, native re-implementation of the *pattern* behind PaperQA2 (grounded,
citation-backed answers over a paper corpus) — NOT the PaperQA2 project itself.
It runs entirely on the Anthropic Claude API stack already used in this repo.

Grounding strategy (preferred): upload the PDFs in PDF_DIR via the Files API and
attach them as ``document`` blocks with citations enabled, so Claude answers from
the full text and returns ``cited_text`` spans pointing back into each PDF.

Fallback: if PDF_DIR has no PDFs, answer from the extracted review summaries
(title + citation + paper_summary + conclusions_summary) as plain-text context.
The answer is then clearly labelled as grounded in summaries, not full text, and
no citation spans are available.

Usage:
    python scripts/ask_papers.py "How does extreme heat affect mortality in Phoenix?"
    python scripts/ask_papers.py --max-papers 4 "What adaptations reduce heat risk?"
    python scripts/ask_papers.py --dry-run "test question"   # show inputs, no API call
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from scorch import config, records  # noqa: E402

FILES_BETA = "files-api-2025-04-14"


def list_pdfs(limit: int) -> list[Path]:
    if not config.PDF_DIR.exists():
        return []
    return sorted(config.PDF_DIR.glob("*.pdf"))[:limit]


def load_review_contexts(limit: int) -> list[dict]:
    """Fallback grounding: title/citation/summary/conclusions from review JSON."""
    contexts: list[dict] = []
    for review_dir in (config.REVIEW_DIR, config.BASE_DIR / "examples" / "reviews"):
        for path in records.iter_review_files(review_dir):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            contexts.append({
                "title": records.get_path(data, "metadata", "title") or "Untitled",
                "citation": records.get_path(data, "metadata", "citation_apa7") or "N/A",
                "summary": records.get_path(data, "summary", "paper_summary") or "N/A",
                "conclusions": records.get_path(data, "summary", "conclusions_summary") or "N/A",
            })
            if len(contexts) >= limit:
                return contexts
    return contexts


def ask_with_pdfs(question: str, pdfs: list[Path]):
    """Upload PDFs and ask with citations enabled. Returns (response, cost)."""
    from anthropic import Anthropic

    client = Anthropic()
    content: list[dict] = []
    for p in pdfs:
        with open(p, "rb") as fh:
            meta = client.beta.files.upload(
                file=(p.name, fh, "application/pdf"), betas=[FILES_BETA]
            )
        content.append({
            "type": "document",
            "source": {"type": "file", "file_id": meta.id},
            "title": p.name,
            "citations": {"enabled": True},
        })
    content.append({"type": "text", "text": question})

    response = client.beta.messages.create(
        model=config.SYNTHESIS_MODEL,
        max_tokens=1500,
        betas=[FILES_BETA],
        messages=[{"role": "user", "content": content}],
    )
    cost = config.estimate_cost(
        config.SYNTHESIS_MODEL, response.usage.input_tokens, response.usage.output_tokens
    )
    return response, cost


def ask_with_reviews(question: str, contexts: list[dict]):
    """Fallback: ask using extracted summaries as plain text. Returns (response, cost)."""
    from anthropic import Anthropic

    client = Anthropic()
    blocks = []
    for c in contexts:
        blocks.append(
            f"Title: {c['title']}\n"
            f"Citation: {c['citation']}\n"
            f"Summary: {c['summary']}\n"
            f"Conclusions: {c['conclusions']}"
        )
    corpus = "\n\n---\n\n".join(blocks)
    prompt = (
        "Answer the question using ONLY the extracted paper summaries below, from the "
        "SCORCH arid-Southwest climate-health review. Cite papers inline by "
        "first-author/year. If the summaries do not contain the answer, say so. Begin "
        "your answer with the exact line '(grounded in extracted summaries, not full text)'.\n\n"
        f"Question: {question}\n\n"
        f"Extracted summaries:\n\n{corpus}"
    )
    response = client.messages.create(
        model=config.SYNTHESIS_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    cost = config.estimate_cost(
        config.SYNTHESIS_MODEL, response.usage.input_tokens, response.usage.output_tokens
    )
    return response, cost


def print_answer_and_citations(response) -> None:
    """Print answer text, then any citation spans found on text blocks."""
    citations_found = []
    print("\n=== Answer ===\n")
    for block in response.content:
        if getattr(block, "type", None) != "text":
            continue
        print(block.text)
        cites = getattr(block, "citations", None)
        if cites:
            citations_found.extend(cites)

    if not citations_found:
        return
    print("\n=== Sources / citations ===\n")
    for cite in citations_found:
        cited_text = (getattr(cite, "cited_text", "") or "").strip().replace("\n", " ")
        if len(cited_text) > 160:
            cited_text = cited_text[:157] + "..."
        title = getattr(cite, "document_title", None) or getattr(cite, "title", None) or ""
        # Location varies by citation type (page range, char range, block index).
        loc_parts = []
        for attr in ("start_page_number", "end_page_number", "start_char_index",
                     "end_char_index", "start_block_index", "end_block_index"):
            val = getattr(cite, attr, None)
            if val is not None:
                loc_parts.append(f"{attr}={val}")
        loc = f" [{', '.join(loc_parts)}]" if loc_parts else ""
        label = f"{title}" if title else "(source)"
        print(f"- {label}{loc}: \"{cited_text}\"")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Citation-grounded Q&A over the SCORCH corpus (PaperQA2-inspired)."
    )
    parser.add_argument("question", nargs="+", help="The question (one or more words).")
    parser.add_argument("--max-papers", type=int, default=6, help="Max PDFs/reviews to ground in.")
    parser.add_argument("--dry-run", action="store_true", help="Show which PDFs/reviews would be used; no API call.")
    args = parser.parse_args()

    question = " ".join(args.question)
    pdfs = list_pdfs(args.max_papers)

    if pdfs:
        print(f"Grounding in {len(pdfs)} PDF(s) from {config.PDF_DIR} (citations enabled):")
        for p in pdfs:
            print(f"  - {p.name}")
        if args.dry_run:
            print("\n[dry run] no upload, no API call.")
            return 0
        response, cost = ask_with_pdfs(question, pdfs)
    else:
        contexts = load_review_contexts(args.max_papers)
        print(f"No PDFs in {config.PDF_DIR}; falling back to {len(contexts)} extracted review summary(ies):")
        for c in contexts:
            print(f"  - {c['title']}")
        if args.dry_run:
            print("\n[dry run] no API call. (Answer would be labelled 'grounded in extracted summaries'.)")
            return 0
        if not contexts:
            print("No PDFs and no reviews available to ground an answer. Nothing to do.")
            return 1
        response, cost = ask_with_reviews(question, contexts)

    print_answer_and_citations(response)
    print(f"\nEstimated cost: ~${cost:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
