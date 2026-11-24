"""Independent SQLite check of the exported CSV totals. Uses the standard library."""
import argparse
import csv
import math
import sqlite3
from pathlib import Path

QUERY = """
WITH decisions AS (
 SELECT source, game, COUNT(*) AS decisions, AVG(latency_ms) AS latency,
        SUM(fallback) AS fallbacks FROM events WHERE event='decision' GROUP BY source,game
), seats AS (
 SELECT DISTINCT source,game,match,seat,outcome FROM events WHERE event='result'
), results AS (
 SELECT source,game,COUNT(*) AS completed, SUM(outcome='won') AS wins,
        SUM(outcome='lost') AS losses, SUM(outcome='drew') AS draws,
        SUM(outcome NOT IN ('won','lost','drew')) AS other
 FROM seats GROUP BY source,game
), groups AS (SELECT DISTINCT source, game FROM events)
SELECT g.source,g.game,COALESCE(d.decisions,0),d.latency,COALESCE(d.fallbacks,0),
       COALESCE(r.completed,0),COALESCE(r.wins,0),COALESCE(r.losses,0),
       COALESCE(r.draws,0),COALESCE(r.other,0)
FROM groups g LEFT JOIN decisions d USING(source,game) LEFT JOIN results r USING(source,game)
ORDER BY g.source,g.game
"""


METRICS = ("decisions", "mean_latency_ms", "fallbacks", "completed_seats", "wins", "losses", "draws", "other_results")


def verify(folder, summary=None):
    with sqlite3.connect(":memory:") as db, (folder/"events.csv").open(newline="", encoding="utf-8-sig") as f:
        db.execute("CREATE TABLE events(source,match,seat,game,event,state_version,kind,latency_ms REAL,attempts,fallback INTEGER,outcome)")
        reader = csv.DictReader(f)
        db.executemany("INSERT INTO events VALUES(:source,:match,:seat,:game,:event,:state_version,:kind,:latency_ms,:attempts,:fallback,:outcome)", reader)
        computed = db.execute(QUERY).fetchall()
    with (summary or folder/"summary.csv").open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        required = {"source", "game", *METRICS}
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")
        saved = {}
        for row in reader:
            key = row["source"], row["game"]
            if key in saved:
                raise ValueError(f"Duplicate group: {key}")
            saved[key] = row
    if set(saved) != {tuple(row[:2]) for row in computed}:
        raise ValueError("Source/game groups differ")
    for source, game, *values in computed:
        for metric, expected in zip(METRICS, values):
            raw = saved[source, game][metric]
            if expected is None and raw in ("", None):
                continue
            tolerance = 0.000501 if metric == "mean_latency_ms" else 0
            if expected is None or not math.isclose(float(raw), expected, rel_tol=0, abs_tol=tolerance):
                raise ValueError(f"{source} / {game} / {metric}: expected {expected}, found {raw}")
        print(source, game, *values)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--external-summary", type=Path, help="CSV exported from Realy")
    args = parser.parse_args()
    verify(args.folder, args.external_summary)
