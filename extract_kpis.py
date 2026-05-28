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
  make sure to convert values to the same units across answers, some values might be in millions, others in billions, etc. 
  If the answer includes a range, return it as is e.g. "between 90B and 100B", "94B-96B", etc.
  if the answer mentions "billions" or "millions", conver them using the appropriate suffix, e.g. "94.9B" for 94.9 billions, "500M" for 500 millions, etc.
- period: time period, use always the same format "FY2024Q1", "FY2025Q1", etc.
- sources might include the period in the name so if you are unable to get it from the answer, try to infer it from the sources name.
  For Amazon AMZN, the source document runs as the calendar year, so Q1 is Jan-Mar, Q2 is Apr-Jun, etc. 
  For Microsoft MSFT, the source document runs as the fiscal year, so Q1 is Jul-Sep, Q2 is Oct-Dec, etc.
  Make sure you make the distinction between calendar and fiscal year when inferring the period from the source document name, and be consistent in the format you return it in.


- Infer the company name from the context and sources. Sources usually include the company name
    or the company stock name (Amazon, AMZN, Microsoft, MSFT, etc). If you cannot determine the company name, return "unknown".
- If the answer includes sources from multiple or unknown companies, ignore it and return an empty array, since we cannot attribute the KPIs to a specific company.

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
