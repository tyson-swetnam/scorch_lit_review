#!/usr/bin/env python3
"""
Interactive DuckDB literature analyst.

Query and analyze the SCORCH literature review database using
natural language prompts powered by Claude.
"""
import os
import sys
import duckdb
from pathlib import Path

# Check if SDK is available
try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic package not found. Install with: pip install anthropic")
    sys.exit(1)


class LiteratureAnalyst:
    """Interactive analyst for querying DuckDB literature database"""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.db_path = base_dir / "duckdb/scorch_reviews.duckdb"

        # Check database exists
        if not self.db_path.exists():
            print(f"\n{'='*60}")
            print("ERROR: Database not found")
            print(f"{'='*60}")
            print(f"\nExpected location: {self.db_path}")
            print("\nRun convert_to_duckdb.py first to create the database.")
            print(f"{'='*60}\n")
            sys.exit(1)

        # Check for API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print(f"\n{'='*60}")
            print("ERROR: ANTHROPIC_API_KEY not found")
            print(f"{'='*60}")
            print("\nSet your API key:")
            print("  export ANTHROPIC_API_KEY='your-key-here'")
            print(f"{'='*60}\n")
            sys.exit(1)

        self.client = Anthropic(api_key=api_key)
        self.con = duckdb.connect(str(self.db_path), read_only=False)

    def get_schema_info(self) -> str:
        """Get database schema information"""
        tables = self.con.execute("SHOW TABLES").fetchall()

        schema_info = "Database Schema:\n\n"

        for table in tables:
            table_name = table[0]
            schema_info += f"Table: {table_name}\n"

            columns = self.con.execute(f"DESCRIBE {table_name}").fetchall()
            for col in columns:
                col_name = col[0]
                col_type = col[1]
                schema_info += f"  - {col_name}: {col_type}\n"
            schema_info += "\n"

        return schema_info

    def execute_query(self, query: str):
        """Execute a SQL query and return formatted results"""
        try:
            result = self.con.execute(query).fetchall()
            columns = [desc[0] for desc in self.con.description]
            return result, columns, None
        except Exception as e:
            return None, None, str(e)

    def analyze_request(self, user_request: str, schema_info: str, conversation_history: list):
        """Use Claude to convert natural language to SQL and explain results"""

        system_prompt = """You are an expert DuckDB analyst specializing in climate-health literature review data.

Your database contains SCORCH (Southwest Center on Resilience for Climate Change and Health) literature reviews extracted from PDFs.

When the user asks a question:
1. Generate a DuckDB SQL query to answer their question
2. Explain what the query does
3. After seeing results, provide insights and interpretation

Return your response in this format:

QUERY:
```sql
[Your SQL query here]
```

EXPLANATION:
[What this query does and why]

If you need to see schema details, you can request them.
If the user's question is unclear, ask for clarification.
"""

        messages = conversation_history + [
            {
                "role": "user",
                "content": f"""Database Schema:
{schema_info}

User Request: {user_request}

Please provide a SQL query to answer this request."""
            }
        ]

        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            temperature=0.0,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text

    def extract_sql_from_response(self, response: str) -> str:
        """Extract SQL query from Claude's response"""
        lines = response.split('\n')
        in_sql = False
        sql_lines = []

        for line in lines:
            if '```sql' in line.lower():
                in_sql = True
                continue
            elif '```' in line and in_sql:
                break
            elif in_sql:
                sql_lines.append(line)

        return '\n'.join(sql_lines).strip()

    def format_results(self, results, columns):
        """Format query results as a table"""
        if not results:
            return "No results found."

        # Calculate column widths
        col_widths = [len(col) for col in columns]
        for row in results:
            for i, val in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(val)))

        # Header
        header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
        separator = "-+-".join("-" * width for width in col_widths)

        # Rows
        rows = []
        for row in results:
            rows.append(" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)))

        return f"{header}\n{separator}\n" + "\n".join(rows)

    def interactive_session(self):
        """Run an interactive query session"""
        print("="*60)
        print("SCORCH Literature Analyst")
        print("="*60)
        print(f"Database: {self.db_path}")
        print(f"Rows: {self.con.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]}")
        print("="*60)
        print("\nAsk questions about your literature review data.")
        print("Examples:")
        print("  - What tables are in the database?")
        print("  - How many papers were published each year?")
        print("  - Show me papers with high relevance ratings")
        print("  - What are the most common health outcomes?")
        print("\nType 'exit' or 'quit' to end the session.\n")

        schema_info = self.get_schema_info()
        conversation_history = []

        while True:
            try:
                user_input = input("\n🔍 Query: ").strip()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("\n✓ Session ended. Goodbye!")
                    break

                if not user_input:
                    continue

                # Get Claude's response
                print("\n💭 Analyzing...")
                response = self.analyze_request(user_input, schema_info, conversation_history)

                # Extract and execute SQL
                sql = self.extract_sql_from_response(response)

                if sql:
                    print("\n📊 SQL Query:")
                    print(sql)
                    print()

                    results, columns, error = self.execute_query(sql)

                    if error:
                        print(f"✗ Query Error: {error}\n")
                        # Add error to conversation
                        conversation_history.append({
                            "role": "user",
                            "content": user_input
                        })
                        conversation_history.append({
                            "role": "assistant",
                            "content": response
                        })
                        conversation_history.append({
                            "role": "user",
                            "content": f"The query returned an error: {error}. Please fix it."
                        })
                    else:
                        print("✓ Results:")
                        print(self.format_results(results, columns))
                        print(f"\n({len(results)} rows)")

                        # Add successful exchange to history
                        conversation_history.append({
                            "role": "user",
                            "content": user_input
                        })
                        conversation_history.append({
                            "role": "assistant",
                            "content": response
                        })
                else:
                    print("\n💬 Response:")
                    print(response)

                # Keep conversation history manageable
                if len(conversation_history) > 10:
                    conversation_history = conversation_history[-10:]

            except KeyboardInterrupt:
                print("\n\n✓ Session ended. Goodbye!")
                break
            except Exception as e:
                print(f"\n✗ Error: {e}")

    def run_single_query(self, query_text: str):
        """Run a single query and exit"""
        print("="*60)
        print("SCORCH Literature Analyst - Single Query Mode")
        print("="*60)

        schema_info = self.get_schema_info()

        print(f"\n🔍 Query: {query_text}\n")
        print("💭 Analyzing...")

        response = self.analyze_request(query_text, schema_info, [])
        sql = self.extract_sql_from_response(response)

        if sql:
            print("\n📊 SQL Query:")
            print(sql)
            print()

            results, columns, error = self.execute_query(sql)

            if error:
                print(f"✗ Query Error: {error}")
            else:
                print("✓ Results:")
                print(self.format_results(results, columns))
                print(f"\n({len(results)} rows)")
        else:
            print("\n💬 Response:")
            print(response)


def main():
    # Dynamically determine base directory (parent of scripts/)
    base_dir = Path(__file__).parent.parent.resolve()
    analyst = LiteratureAnalyst(base_dir)

    # Check if query provided as argument
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        analyst.run_single_query(query)
    else:
        analyst.interactive_session()


if __name__ == "__main__":
    main()
