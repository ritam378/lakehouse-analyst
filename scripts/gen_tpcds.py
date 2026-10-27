"""Generate TPC-DS data into a DuckDB file.

Usage:
    uv run python scripts/gen_tpcds.py 0.1 ~/lab/data/tpcds_sf0_1.duckdb   # seconds
    uv run python scripts/gen_tpcds.py 7   ~/lab/data/tpcds_sf7.duckdb     # working copy
"""
import os, sys, duckdb

sf, path = float(sys.argv[1]), os.path.expanduser(sys.argv[2])
tmp = os.path.expanduser("~/lab/data/tmp")
os.makedirs(tmp, exist_ok=True)

con = duckdb.connect(path)
con.execute("SET memory_limit='6GB'")
con.execute(f"SET temp_directory='{tmp}'")
con.execute("INSTALL tpcds; LOAD tpcds;")
con.execute(f"CALL dsdgen(sf={sf})")
print(con.execute("SELECT count(*) FROM store_sales").fetchone())
