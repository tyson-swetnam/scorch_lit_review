#!/usr/bin/env python3
"""Batch-extract SCORCH reviews from PDFs with a tiered, verified pipeline.

Pipeline per PDF (stages are opt-in via flags):

    upload (Files API, once)
      -> screen   [Haiku 4.5]  cheap include/exclude on the arid-SW gate (--screen)
      -> extract  [Sonnet 4.6] full 46-field JSON, validated against the schema
      -> verify   [Opus 4.8]   flags likely hallucinations / N/A-policy violations (--verify)

Modernizations over the original script:
- Uses current models (Opus 4.8 / Sonnet 4.6 / Haiku 4.5) from scorch.config.
- Uploads each PDF once via the Files API and references it by file_id across
  stages (no repeated base64).
- Caches the large schema/system prefix with prompt caching (~90% cheaper prefix).
- Validates every extraction against scorch_extraction_schema.json and runs one
  repair pass on failure, instead of scraping the first {...} and hoping.
- Records provenance (model, token usage, cost estimate) in extraction_metadata.

Requires ANTHROPIC_API_KEY. Run `--dry-run` to preview work with no API calls.

    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/batch_process_pdfs.py --screen --verify
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from scorch import config, records  # noqa: E402

FILES_BETA = "files-api-2025-04-14"


def unprocessed_pdfs() -> list[Path]:
    done = {p.stem.replace("_review", "") for p in records.iter_review_files(config.REVIEW_DIR)}
    return [p for p in sorted(config.PDF_DIR.glob("*.pdf")) if p.stem not in done]


def extraction_system_prompt(schema: dict) -> list[dict]:
    """Cached system prefix: instructions + the full schema (stable across PDFs)."""
    text = (
        "You are a SCORCH climate-health literature extraction agent. Extract data "
        "from the attached research PDF into a JSON object that conforms EXACTLY to "
        "the JSON Schema below.\n\n"
        "Rules:\n"
        "1. Use the string \"N/A\" when information is absent — NEVER fabricate.\n"
        "2. Respect every enum and type; use [] for empty arrays and null for absent numbers.\n"
        "3. Output ONLY the JSON object — no markdown fences, no commentary.\n\n"
        "JSON Schema:\n" + json.dumps(schema, indent=2)
    )
    # cache_control marks this (large, stable) block as cacheable.
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from a model response, tolerating stray prose/fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].lstrip("json").strip() if "```" in text[3:] else text
    start, end = text.find("{"), text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(text[start:end])


def _text(message) -> str:
    return "".join(b.text for b in message.content if getattr(b, "type", None) == "text")


def _usage_cost(model: str, usage) -> float:
    return config.estimate_cost(
        model,
        getattr(usage, "input_tokens", 0) + getattr(usage, "cache_read_input_tokens", 0),
        getattr(usage, "output_tokens", 0),
    )


class Pipeline:
    def __init__(self, client, schema: dict, *, screen: bool, verify: bool):
        self.client = client
        self.schema = schema
        self.system = extraction_system_prompt(schema)
        self.do_screen = screen
        self.do_verify = verify

    async def upload(self, pdf: Path):
        with open(pdf, "rb") as fh:
            meta = await self.client.beta.files.upload(
                file=(pdf.name, fh, "application/pdf"), betas=[FILES_BETA]
            )
        return meta.id

    def _document(self, file_id: str) -> dict:
        return {"type": "document", "source": {"type": "file", "file_id": file_id}}

    async def screen(self, file_id: str) -> dict:
        msg = await self.client.beta.messages.create(
            model=config.SCREEN_MODEL, max_tokens=400, betas=[FILES_BETA],
            messages=[{"role": "user", "content": [
                self._document(file_id),
                {"type": "text", "text":
                    "Screen this paper for the SCORCH review (arid/semi-arid SW US & "
                    "northern Mexico climate-health). Reply ONLY as JSON: "
                    '{"focuses_on_arid_semiarid_sw_us_mexico": bool, '
                    '"includes_primary_data_for_region": bool, "reason": "one sentence"}'},
            ]}],
        )
        result = parse_json_object(_text(msg))
        result["_cost"] = _usage_cost(config.SCREEN_MODEL, msg.usage)
        return result

    async def extract(self, file_id: str, pdf_name: str) -> tuple[dict, float]:
        cost = 0.0
        prompt = ("Extract the complete SCORCH review JSON for the attached PDF, "
                  "conforming exactly to the schema in the system prompt.")
        async with self.client.beta.messages.stream(
            model=config.EXTRACT_MODEL, max_tokens=config.EXTRACT_MAX_TOKENS,
            betas=[FILES_BETA], system=self.system,
            messages=[{"role": "user", "content": [self._document(file_id),
                                                    {"type": "text", "text": prompt}]}],
        ) as stream:
            msg = await stream.get_final_message()
        cost += _usage_cost(config.EXTRACT_MODEL, msg.usage)
        data = parse_json_object(_text(msg))

        errors = records.validate_review(data, self.schema)
        if errors:  # one repair pass
            repair = ("The JSON failed schema validation. Fix ONLY these issues and "
                      "return the full corrected JSON object:\n- " + "\n- ".join(errors[:20]))
            rmsg = await self.client.beta.messages.create(
                model=config.EXTRACT_MODEL, max_tokens=config.EXTRACT_MAX_TOKENS,
                betas=[FILES_BETA], system=self.system,
                messages=[
                    {"role": "user", "content": [self._document(file_id),
                                                 {"type": "text", "text": prompt}]},
                    {"role": "assistant", "content": json.dumps(data)},
                    {"role": "user", "content": repair},
                ],
            )
            cost += _usage_cost(config.EXTRACT_MODEL, rmsg.usage)
            data = parse_json_object(_text(rmsg))

        self._stamp(data, pdf_name)
        return data, cost

    async def verify(self, file_id: str, data: dict) -> tuple[dict, float]:
        msg = await self.client.beta.messages.create(
            model=config.VERIFY_MODEL, max_tokens=1500, betas=[FILES_BETA],
            messages=[{"role": "user", "content": [
                self._document(file_id),
                {"type": "text", "text":
                    "Audit this extracted SCORCH review against the PDF. Identify fields "
                    "that appear fabricated, unsupported, or that should be \"N/A\". Reply "
                    'ONLY as JSON: {"flags": [{"field": str, "issue": str}], "ok": bool}.\n\n'
                    + json.dumps(data)},
            ]}],
        )
        audit = parse_json_object(_text(msg))
        return audit, _usage_cost(config.VERIFY_MODEL, msg.usage)

    def _stamp(self, data: dict, pdf_name: str) -> None:
        meta = data.setdefault("extraction_metadata", {})
        meta.update({
            "extraction_date": datetime.now().strftime("%Y-%m-%d"),
            "extractor_agent": "scorch-batch-pipeline",
            "extraction_model": config.EXTRACT_MODEL,
            "source_pdf_filename": pdf_name,
            "schema_version": config.SCHEMA_VERSION,
        })

    async def process(self, pdf: Path) -> dict:
        out = config.REVIEW_DIR / f"{pdf.stem}_review.json"
        cost = 0.0
        try:
            file_id = await self.upload(pdf)

            if self.do_screen:
                scr = await self.screen(file_id)
                cost += scr.pop("_cost", 0.0)
                if not (scr.get("focuses_on_arid_semiarid_sw_us_mexico")
                        or scr.get("includes_primary_data_for_region")):
                    print(f"  ⊘ Screened out: {pdf.name} — {scr.get('reason', '')}")
                    return {"pdf": pdf.name, "status": "screened_out", "cost": cost}

            data, ecost = await self.extract(file_id, pdf.name)
            cost += ecost

            if self.do_verify:
                audit, vcost = await self.verify(file_id, data)
                cost += vcost
                data["extraction_metadata"]["verification"] = {
                    "model": config.VERIFY_MODEL, "ok": audit.get("ok"),
                    "flags": audit.get("flags", []),
                }
                if audit.get("flags"):
                    print(f"  ⚠ {pdf.name}: verifier flagged {len(audit['flags'])} field(s)")

            data["extraction_metadata"]["estimated_cost_usd"] = round(cost, 4)
            out.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"  ✓ {pdf.name} -> {out.name}  (${cost:.3f})")
            return {"pdf": pdf.name, "status": "success", "cost": cost}
        except Exception as exc:  # noqa: BLE001 - report and continue the batch
            print(f"  ✗ {pdf.name}: {type(exc).__name__}: {exc}")
            return {"pdf": pdf.name, "status": "error", "error": str(exc), "cost": cost}


async def run(pdfs: list[Path], *, screen: bool, verify: bool) -> list[dict]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    schema = records.load_schema(config.SCHEMA_PATH)
    pipeline = Pipeline(client, schema, screen=screen, verify=verify)
    sem = asyncio.Semaphore(config.BATCH_CONCURRENCY)

    async def guarded(pdf):
        async with sem:
            return await pipeline.process(pdf)

    return await asyncio.gather(*(guarded(p) for p in pdfs))


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-extract SCORCH reviews from PDFs.")
    parser.add_argument("--screen", action="store_true", help="Cheap Haiku include/exclude pass first.")
    parser.add_argument("--verify", action="store_true", help="Opus audit pass after extraction.")
    parser.add_argument("--dry-run", action="store_true", help="List work; make no API calls.")
    args = parser.parse_args()

    config.REVIEW_DIR.mkdir(exist_ok=True)
    pdfs = unprocessed_pdfs()
    if not pdfs:
        print("✓ No unprocessed PDFs found.")
        return 0

    print(f"Found {len(pdfs)} unprocessed PDF(s); models: screen={config.SCREEN_MODEL} "
          f"extract={config.EXTRACT_MODEL} verify={config.VERIFY_MODEL}")
    if args.dry_run:
        for p in pdfs:
            print(f"  • {p.name}")
        print("(dry run — no API calls)")
        return 0

    results = asyncio.run(run(pdfs, screen=args.screen, verify=args.verify))

    ok = sum(r["status"] == "success" for r in results)
    total_cost = sum(r.get("cost", 0.0) for r in results)
    print(f"\n{'='*60}\nDONE: {ok}/{len(results)} extracted  |  est. ${total_cost:.2f}")
    print("Next: python scripts/convert_to_duckdb.py && python scripts/build_okf.py")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
