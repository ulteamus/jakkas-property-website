"""Split schema SQL and print chunk boundaries for MCP apply_migration."""
from pathlib import Path

sql = Path("scripts/_tmp_cloud_migration.sql").read_text(encoding="utf-8")
# Drop trailing incomplete comment section
if sql.rstrip().endswith("--"):
    sql = sql.rstrip()[:-2].rstrip()

marker = "-- Row Level Security"
if marker in sql:
    tables, rls = sql.split(marker, 1)
    rls = marker + rls
else:
    tables, rls = sql, ""

Path("scripts/_mig_tables.sql").write_text(tables.strip() + "\n", encoding="utf-8")
Path("scripts/_mig_rls.sql").write_text(rls.strip() + "\n", encoding="utf-8")
print("tables_chars", len(tables))
print("rls_chars", len(rls))
