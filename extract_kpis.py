import os
import json
import pyodbc
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
    api_key=os.getenv("OPENAI_KEY"),
    api_version="2024-02-01"
)

KPI_PROMPT = """Extract financial KPIs from this earnings call answer.
Return a JSON array. Each item must have:
- company: company name
- metric_name: e.g. "revenue", "gross_margin", "operating_expenses", "guidance"
- metric_value: the numeric value or range as a string e.g. "94.9B", "45.2%"
- period: time period e.g. "Q4 2024", "FY2024", "Q1 2025 guidance"

Return only valid JSON, no explanation, no markdown.
If no financial KPIs are present, return an empty array [].

Answer to analyze:
"""

def extract_kpis_from_answer(answer, query_id, source_doc):
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_CHAT_DEPLOYMENT"),
        messages=[
            {"role": "user", "content": KPI_PROMPT + answer}
        ],
        temperature=0,
        max_tokens=300
    )

    raw = response.choices[0].message.content.strip()

    try:
        kpis = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  Warning: could not parse KPI JSON — {raw[:100]}")
        return []

    return [
        {**kpi, "query_id": query_id, "source_doc": source_doc}
        for kpi in kpis
        if all(k in kpi for k in ["company", "metric_name", "metric_value", "period"])
    ]

def run_kpi_extraction():
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USERNAME')};"
        f"PWD={os.getenv('SQL_PASSWORD')};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # fetch answers not yet processed for KPIs
    cursor.execute("""
        SELECT q.id, q.answer, q.source_docs
        FROM query_log q
        WHERE q.id NOT IN (SELECT DISTINCT query_id FROM kpi_extractions)
    """)
    rows = cursor.fetchall()

    print(f"Processing {len(rows)} unextracted answers...")

    for row in rows:
        query_id, answer, source_docs = row
        kpis = extract_kpis_from_answer(answer, query_id, source_docs)

        for kpi in kpis:
            cursor.execute("""
                INSERT INTO kpi_extractions
                    (query_id, company, metric_name, metric_value, period, source_doc)
                VALUES (?, ?, ?, ?, ?, ?)
            """, kpi["query_id"], kpi["company"], kpi["metric_name"],
                kpi["metric_value"], kpi["period"], kpi["source_doc"])

        print(f"  Query {query_id}: {len(kpis)} KPIs extracted")

    conn.commit()
    cursor.close()
    conn.close()
    print("KPI extraction complete.")

if __name__ == "__main__":
    run_kpi_extraction()
