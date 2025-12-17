# SCORCH SDK Scripts

Standalone Python scripts for batch processing PDFs and managing the literature review database using the Claude SDK.

## Prerequisites

```bash
pip install anthropic duckdb
export ANTHROPIC_API_KEY='your-api-key-here'
```

## Scripts

### 1. batch_process_pdfs.py

Batch processes PDFs using direct Claude API calls with parallel execution.

**Features:**
- Processes 4 PDFs concurrently (configurable batch size)
- Each PDF gets independent 1M token context
- Incremental processing (skips already-reviewed PDFs)
- Automatic JSON validation and error handling

**Usage:**
```bash
python scripts/batch_process_pdfs.py
```

**Output:**
- Creates `reviews/*_review.json` for each PDF
- Reports success/error status for each file
- Shows batch progress and final summary

---

### 2. convert_to_duckdb.py

Converts JSON review files to DuckDB database with incremental updates.

**Features:**
- Incremental updates (only adds new reviews)
- No API key required (pure Python/DuckDB)
- Automatic schema creation
- Exports to Parquet format

**Usage:**
```bash
python scripts/convert_to_duckdb.py
```

**Output:**
- Updates `duckdb/scorch_reviews.duckdb`
- Exports `duckdb/scorch_reviews.parquet`
- Reports new vs. existing reviews

**Database Schema:**
- `reviews` - Main table with metadata and assessments
- `health_outcome_variables` - Health outcomes tracked
- `climate_weather_variables` - Climate variables analyzed
- `cofactor_variables` - Confounding factors
- `vulnerable_populations` - Population groups identified
- `correlations` - Statistical relationships reported

---

### 3. query_literature.py

Interactive database analyst powered by Claude for natural language queries.

**Features:**
- Ask questions in plain English
- Automatic SQL generation and execution
- Conversational context maintained
- Single query or interactive mode

**Usage:**

Interactive mode:
```bash
python scripts/query_literature.py
```

Single query mode:
```bash
python scripts/query_literature.py "How many papers were published each year?"
```

**Example Questions:**
- "What tables are in the database?"
- "How many papers have high relevance ratings?"
- "Show me the most common health outcomes"
- "Which papers focus on vulnerable populations?"
- "Give me papers published after 2020 about heat exposure"

---

## Complete Workflow

### Full Pipeline
```bash
# 1. Add PDFs to pdfs/ directory

# 2. Extract data from all PDFs
python scripts/batch_process_pdfs.py

# 3. Convert to database
python scripts/convert_to_duckdb.py

# 4. Query the data
python scripts/query_literature.py
```

### Incremental Updates
```bash
# Add new PDFs to pdfs/ directory

# Process only new PDFs
python scripts/batch_process_pdfs.py

# Add only new reviews to database
python scripts/convert_to_duckdb.py
```

---

## Comparison: SDK Scripts vs. Claude Code Agents

| Feature | SDK Scripts | Claude Code Agents |
|---------|-------------|-------------------|
| **Execution** | Standalone Python | Within Claude Code session |
| **API Key** | Required (env var) | Managed by Claude Code |
| **Batch Processing** | Native parallel execution | Sequential or manual |
| **Context** | 1M per PDF | Shared session context |
| **Interactivity** | Command-line only | Full Claude Code tools |
| **Automation** | Ideal for cron jobs | Interactive workflow |

**Use SDK Scripts when:**
- Processing large batches of PDFs
- Running automated pipelines
- Deploying on servers/CI systems
- Maximizing parallel throughput

**Use Claude Code Agents when:**
- Working interactively
- Debugging extractions
- One-off PDF analysis
- Leveraging full Claude Code toolset

---

## Troubleshooting

**API Key Error:**
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

**Database Not Found:**
Run `convert_to_duckdb.py` first to create the database.

**JSON Parse Errors:**
Check `reviews/*_debug.txt` files for raw responses.

**Memory Issues:**
Reduce batch size in `batch_process_pdfs.py` (line 234):
```python
batch_size = 2  # Lower from default 4
```

---

## Development

All scripts use:
- **Model:** `claude-sonnet-4-5-20250929`
- **Temperature:** 0.0 (deterministic)
- **Schema:** `schema/scorch_extraction_schema.json`

To modify extraction behavior, edit the schema file. Scripts automatically load the current schema.
