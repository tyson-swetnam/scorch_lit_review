#!/usr/bin/env python3
"""
Batch process PDFs using Claude Agent SDK with independent contexts.

Each PDF gets its own agent with a dedicated 1M token context window,
allowing for true parallel processing without context sharing.
"""
import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Check if SDK is available
try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not found. Install with: pip install anthropic")
    sys.exit(1)


class PDFProcessor:
    """Processes PDFs using independent Claude agent instances"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.pdf_dir = base_dir / "pdfs"
        self.review_dir = base_dir / "reviews"
        self.schema_path = base_dir / "schema/scorch_extraction_schema.json"

        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("\n" + "="*60)
            print("ERROR: ANTHROPIC_API_KEY not found")
            print("="*60)
            print("\nSet your API key:")
            print("  export ANTHROPIC_API_KEY='your-key-here'")
            print("\nOr run within Claude Code using Task tool instead")
            print("="*60 + "\n")
            sys.exit(1)

        self.client = Anthropic(api_key=api_key)

    def find_unprocessed_pdfs(self):
        """Find PDFs that don't have corresponding review files"""
        pdfs = list(self.pdf_dir.glob("*.pdf"))
        existing_reviews = {
            r.stem.replace("_review", "")
            for r in self.review_dir.glob("*_review.json")
        }
        unprocessed = [p for p in pdfs if p.stem not in existing_reviews]
        return unprocessed

    def load_schema(self) -> dict:
        """Load the SCORCH extraction schema"""
        with open(self.schema_path, 'r') as f:
            return json.load(f)

    async def process_single_pdf(self, pdf_path: Path) -> dict:
        """Process a single PDF with an independent agent instance"""

        review_filename = pdf_path.stem + "_review.json"
        output_path = self.review_dir / review_filename

        print(f"📄 Processing: {pdf_path.name}")

        # Load schema
        schema = self.load_schema()

        # Read PDF as base64
        import base64
        with open(pdf_path, 'rb') as f:
            pdf_data = base64.standard_b64encode(f.read()).decode('utf-8')

        prompt = f"""You are a SCORCH literature review extraction agent. Analyze this climate-health research PDF and extract structured data according to the schema below.

**SCORCH Extraction Schema:**
{json.dumps(schema, indent=2)}

**Instructions:**
1. Read the PDF document carefully
2. Answer all 46 questions following the schema structure exactly
3. Use "N/A" when information is not present - NEVER fabricate data
4. Follow all enum constraints and data types
5. Include these extraction_metadata fields:
   - extraction_date: "{datetime.now().strftime("%Y-%m-%d")}"
   - extractor_agent: "scorch-pdf-analyzer-sdk"
   - source_pdf_filename: "{pdf_path.name}"
   - schema_version: "1.1"

**Output:**
Provide ONLY the complete JSON object following the schema. No markdown, no explanation, just valid JSON.
"""

        try:
            # Create message with PDF document - independent context
            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=16000,
                temperature=0.0,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Try to find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                review_data = json.loads(json_str)

                # Write to file
                with open(output_path, 'w') as f:
                    json.dump(review_data, f, indent=2)

                print(f"  ✓ Success: {review_filename} ({len(json_str)} bytes)")
                return {
                    "pdf": pdf_path.name,
                    "status": "success",
                    "output": str(output_path)
                }
            else:
                print(f"  ✗ Error: No JSON found in response")
                return {
                    "pdf": pdf_path.name,
                    "status": "error",
                    "error": "No JSON found in response"
                }

        except json.JSONDecodeError as e:
            print(f"  ✗ Error: Invalid JSON - {e}")
            # Save raw response for debugging
            debug_path = self.review_dir / f"{pdf_path.stem}_debug.txt"
            with open(debug_path, 'w') as f:
                f.write(response_text)
            return {
                "pdf": pdf_path.name,
                "status": "error",
                "error": f"Invalid JSON: {e}"
            }
        except Exception as e:
            print(f"  ✗ Error: {pdf_path.name} - {e}")
            return {
                "pdf": pdf_path.name,
                "status": "error",
                "error": str(e)
            }

    async def process_batch(self, pdfs: list, batch_size: int = 4):
        """Process PDFs in batches with parallel execution"""

        all_results = []

        for i in range(0, len(pdfs), batch_size):
            batch = pdfs[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(pdfs) + batch_size - 1) // batch_size

            print(f"\n{'='*60}")
            print(f"Batch {batch_num}/{total_batches} - Processing {len(batch)} PDFs in parallel")
            print(f"{'='*60}")

            # Process batch in parallel - each agent has independent 1M context
            tasks = [self.process_single_pdf(pdf) for pdf in batch]
            results = await asyncio.gather(*tasks)
            all_results.extend(results)

            # Report batch results
            successes = sum(1 for r in results if r["status"] == "success")
            print(f"\n📊 Batch {batch_num} complete: {successes}/{len(batch)} succeeded")

        return all_results

    def print_summary(self, results: list):
        """Print final summary of processing"""
        total = len(results)
        successes = sum(1 for r in results if r["status"] == "success")
        errors = sum(1 for r in results if r["status"] == "error")
        partial = sum(1 for r in results if r["status"] == "partial")

        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total PDFs: {total}")
        print(f"  ✓ Success: {successes}")
        print(f"  ⚠ Partial: {partial}")
        print(f"  ✗ Errors:  {errors}")

        if errors > 0:
            print(f"\nFailed PDFs:")
            for r in results:
                if r["status"] == "error":
                    print(f"  - {r['pdf']}: {r.get('error', 'Unknown error')}")


async def main():
    # Dynamically determine base directory (parent of scripts/)
    base_dir = Path(__file__).parent.parent.resolve()
    processor = PDFProcessor(base_dir)

    # Find unprocessed PDFs
    unprocessed = processor.find_unprocessed_pdfs()

    if not unprocessed:
        print("✓ No unprocessed PDFs found. All PDFs have reviews!")
        return

    print(f"Found {len(unprocessed)} unprocessed PDF(s):")
    for pdf in unprocessed:
        print(f"  - {pdf.name}")

    # Process in batches
    batch_size = 4  # Adjust based on system resources
    results = await processor.process_batch(unprocessed, batch_size=batch_size)

    # Print summary
    processor.print_summary(results)

    # Check for successful completions
    successes = [r for r in results if r["status"] == "success"]
    if successes:
        print(f"\n✓ Created {len(successes)} new review file(s)")
        print(f"\nNext step: Run duckdb-schema-converter to update database")


if __name__ == "__main__":
    asyncio.run(main())
