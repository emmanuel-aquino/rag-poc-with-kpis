import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

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

# table 1 — logs every RAG query end to end
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='query_log' AND xtype='U')
CREATE TABLE query_log (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    question        NVARCHAR(500)   NOT NULL,
    answer          NVARCHAR(MAX)   NOT NULL,
    source_docs     NVARCHAR(500),
    retrieved_chunks INT,
    latency_ms      INT,
    timestamp       DATETIME        DEFAULT GETDATE()
)
""")

# table 2 — structured KPIs extracted from answers
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='kpi_extractions' AND xtype='U')
CREATE TABLE kpi_extractions (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    query_id        INT             REFERENCES query_log(id),
    company         NVARCHAR(100),
    metric_name     NVARCHAR(100),
    metric_value    NVARCHAR(100),
    period          NVARCHAR(50),
    source_doc      NVARCHAR(200),
    timestamp       DATETIME        DEFAULT GETDATE()
)
""")

# table 3 — chunk-level retrieval detail
cursor.execute("""
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='retrieval_log' AND xtype='U')
CREATE TABLE retrieval_log (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    query_id        INT             REFERENCES query_log(id),
    chunk_id        NVARCHAR(200),
    source_doc      NVARCHAR(200),
    section         NVARCHAR(200),
    relevance_score FLOAT,
    timestamp       DATETIME        DEFAULT GETDATE()
)
""")

conn.commit()
cursor.close()
conn.close()
print("Tables created successfully.")
