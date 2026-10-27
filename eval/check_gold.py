"""Run every gold query and flag the ones that fail, return no rows or have a tie at the LIMIT cut-off.

Usage:
    uv run python eval/check_gold.py ~/lab/data/tpcds_sf0_1.duckdb
    uv run python eval/check_gold.py ~/lab/data/tpcds_sf7.duckdb
    uv run python eval/check_gold.py ~/lab/data/tpcds_sf0_1.duckdb --show   # also print each result
"""
import json
import os
import re
import sys
import time
from collections import Counter

import duckdb

DB = os.path.expanduser(sys.argv[1])
SHOW = "--show" in sys.argv
GOLD = "eval/gold.jsonl"
LIMIT_RE = re.compile(r"\bLIMIT\s+(\d+)\s*;?\s*$", re.IGNORECASE)

con = duckdb.connect(DB, read_only=True)
con.execute("SET memory_limit='6GB'")

ids, problems, mix = set(), 0, Counter()
for n, line in enumerate(open(GOLD), 1):
    q = json.loads(line)
    for key in ("id", "difficulty", "question", "gold_sql", "tags"):
        assert key in q, f"line {n}: missing {key}"
    assert q["id"] not in ids, f"duplicate id {q['id']}"
    assert q["difficulty"] in ("easy", "medium", "hard"), f"{q['id']}: bad difficulty"
    ids.add(q["id"])
    mix[q["difficulty"]] += 1

    start = time.time()
    try:
        rows = con.execute(q["gold_sql"]).fetchall()
    except duckdb.Error as e:
        print(f"{q['id']:6} {q['difficulty']:6} FAIL {e}")
        problems += 1
        continue

    flags = []
    if not rows:
        flags.append("EMPTY")
    elif all(v is None for v in rows[0]) and len(rows) == 1:
        flags.append("NULL")

    # Tie check: rerun with LIMIT n+1; if row n+1 has the same numbers as row n, two answers exist.
    m = LIMIT_RE.search(q["gold_sql"])
    if m and len(rows) == int(m.group(1)):
        k = int(m.group(1))
        extra = con.execute(LIMIT_RE.sub(f"LIMIT {k + 1}", q["gold_sql"])).fetchall()
        if len(extra) > k:
            nums = lambda r: [v for v in r if isinstance(v, (int, float)) or hasattr(v, "as_tuple")]
            if nums(extra[k - 1]) and nums(extra[k - 1]) == nums(extra[k]):
                flags.append("TIE")

    problems += bool(flags)
    print(f"{q['id']:6} {q['difficulty']:6} {len(rows):6} rows {time.time() - start:6.2f}s {' '.join(flags)}")
    if SHOW:
        print(f"       {q['question']}")
        for r in rows[:5]:
            print(f"         {r}")

print(f"\n{len(ids)} questions: {dict(mix)}  (target 150: easy 50, medium 60, hard 40)")
print("ALL GOOD" if problems == 0 else f"{problems} question(s) need attention")
sys.exit(1 if problems else 0)
