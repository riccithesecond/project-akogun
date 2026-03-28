from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import duckdb
import os
import re

app = FastAPI(title="Akogun SIEM API", version="1.0.0")


# Allow requests from the React UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PARQUET_PATH = os.environ.get("PARQUET_PATH", "/home/xango/akogun/data/parquet")

class QueryRequest(BaseModel):
    query: str
    language: str  # "kql", "spl", or "sql"

class QueryResponse(BaseModel):
    columns: list
    rows: list
    row_count: int
    language: str
    translated_sql: str

def kql_to_sql(kql: str) -> str:
    """
    Basic KQL -> DuckDB SQL translator.
    Handles the most common KQL patterns.
    """
    sql = kql.strip()

    # KQL: TableName | where Field == "value"
    # Handle pipe-based KQL
    parts = [p.strip() for p in sql.split("|")]
    table = parts[0].strip()

    # Build SQL from table name
    parquet_file = f"'{PARQUET_PATH}/{table}.parquet'"
    sql_query = f"SELECT * FROM read_parquet({parquet_file})"

    conditions = []
    select_cols = "*"
    limit_val = None
    order_col = None
    order_dir = "DESC"

    for part in parts[1:]:
        part = part.strip()

        # where clause
        if part.lower().startswith("where "):
            condition = part[6:].strip()
            # == to =
            condition = re.sub(r'\s*==\s*', ' = ', condition)
            # != stays
            # contains to LIKE
            condition = re.sub(
                r'(\w+)\s+contains\s+"([^"]+)"',
                r"\1 LIKE '%\2%'",
                condition,
                flags=re.IGNORECASE
            )
            # startswith
            condition = re.sub(
                r'(\w+)\s+startswith\s+"([^"]+)"',
                r"\1 LIKE '\2%'",
                condition,
               flags=re.IGNORECASE
            )
            conditions.append(condition)

        # project (SELECT specific columns)
        elif part.lower().startswith("project "):
            select_cols = part[8:].strip()

        # limit
        elif part.lower().startswith("limit ") or part.lower().startswith("take "):
            limit_val = part.split()[-1]

        # order by / sort by
        elif part.lower().startswith("sort by ") or part.lower().startswith("order by "):
            tokens = part.split()
            order_col = tokens[2]
            if len(tokens) > 3:
                order_dir = tokens[3].upper()

        # count
        elif part.lower() == "count":
            select_cols = "COUNT(*) as count"

        # summarize count() by Field
        elif part.lower().startswith("summarize "):
            summary = part[10:].strip()
            if " by " in summary.lower():
                agg, group = re.split(r'\s+by\s+', summary, flags=re.IGNORECASE)
                agg = agg.strip().replace("count()", "COUNT(*) as count")
                select_cols = f"{agg}, {group.strip()}"
                sql_query = f"SELECT {select_cols} FROM read_parquet({parquet_file})"
                if conditions:
                    sql_query += " WHERE " + " AND ".join(conditions)
                sql_query += f" GROUP BY {group.strip()}"
                if limit_val:
                    sql_query += f" LIMIT {limit_val}"
                return sql_query

    # Assemble final SQL
    sql_query = f"SELECT {select_cols} FROM read_parquet({parquet_file})"
    if conditions:
        sql_query += " WHERE " + " AND ".join(conditions)
    if order_col:
        sql_query += f" ORDER BY {order_col} {order_dir}"
    if limit_val:
        sql_query += f" LIMIT {limit_val}"

    return sql_query


def spl_to_sql(spl: str) -> str:
    """
    Basic SPL -> DuckDB SQL translator.
    Handles common SPL search patterns.
    """
    spl = spl.strip()
    parts = [p.strip() for p in spl.split("|")]

    # First part is usually: search index=X sourcetype=Y field=value
    base = parts[0].strip()

    # Extract index/sourcetype for table routing
    index_match = re.search(r'index=(\S+)', base, re.IGNORECASE)
    sourcetype_match = re.search(r'sourcetype=(\S+)', base, re.IGNORECASE)

    table = index_match.group(1) if index_match else "events"
    parquet_file = f"'{PARQUET_PATH}/{table}.parquet'"

    conditions = []
    select_cols = "*"
    limit_val = 100
    group_by = None
    agg = None

    # Extract field=value pairs from base search
    field_vals = re.findall(r'(\w+)="([^"]+)"', base)
    for field, val in field_vals:
        if field.lower() not in ("index", "sourcetype"):
            conditions.append(f"{field} = '{val}'")

    # Process pipe commands
    for part in parts[1:]:
        part = part.strip()

        # where
        if part.lower().startswith("where "):
            condition = part[6:].strip()
            condition = re.sub(r'\s*==\s*', ' = ', condition)
            conditions.append(condition)

        # fields (SELECT)
        elif part.lower().startswith("fields "):
            select_cols = part[7:].strip()

        # head (LIMIT)
        elif part.lower().startswith("head "):
            limit_val = part.split()[-1]

        # stats count by field
        elif part.lower().startswith("stats "):
            stats_body = part[6:].strip()
            if " by " in stats_body.lower():
                agg_part, group_part = re.split(r'\s+by\s+', stats_body, flags=re.IGNORECASE)
                agg_part = agg_part.strip()
                group_by = group_part.strip()
                agg_part = re.sub(r'count\(\)', 'COUNT(*) as count', agg_part, flags=re.IGNORECASE)
                agg_part = re.sub(r'count\s+as\s+(\w+)', r'COUNT(*) as \1', agg_part, flags=re.IGNORECASE)
                select_cols = f"{agg_part}, {group_by}"
            else:
                select_cols = e.sub(r'count\(\)', 'COUNT(*) as count', stats_body, flags=re.IGNORECASE)

        # sort
        elif part.lower().startswith("sort "):
            tokens = part.split()
            direction = "ASC"
            col = tokens[-1]
            if col.startswith("-"):
                direction = "DESC"
                col = col[1:]
            elif col.startswith("+"):
                col = col[1:]

    # Assemble SQL
    sql_query = f"SELECT {select_cols} FROM read_parquet({parquet_file})"
    if conditions:
        sql_query += " WHERE " + " AND ".join(conditions)
    if group_by:
        sql_query += f" GROUP BY {group_by}"
    sql_query += f" LIMIT {limit_val}"

    return sql_query


def execute_query(sql: str) -> tuple:
    """Execute SQL against DuckDB and return columns + rows."""
    con = duckdb.connect()
    try:
        result = con.execute(sql).fetchdf()
        columns = list(result.columns)
        rows = result.values.tolist()
        # Convert any non-serializable types
        rows = [[str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for v in row] for row in rows]
        return columns, rows
    finally:
        con.close()


@app.get("/")
def root():
    return {"status": "Akogun SIEM API", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy", "parquet_path": PARQUET_PATH}

@app.post("/query", response_model=QueryResponse)
def run_query(req: QueryRequest):
    lang = req.language.lower().strip()

    if lang == "sql":
        translated = req.query
    elif lang == "kql":
        translated = kql_to_sql(req.query)
    elif lang == "spl":
        translated = spl_to_sql(req.query)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown language: {lang}. Use kql, spl, or sql.")

    try:
        columns, rows = execute_query(translated)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}\nTranslated SQL: {translated}")

    return QueryResponse(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        language=lang,
        translated_sql=translated
    )

@app.get("/tables")
def list_tables():
    """List available Parquet files in the data directory."""
    try:
        files = [f.replace(".parquet", "") for f in os.listdir(PARQUET_PATH) if f.endswith(".parquet")]
        return {"tables": files}
    except Exception as e:
        return {"tables": [], "error": str(e)}
