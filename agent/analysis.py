"""Merge per-worker events and summarize each source and game separately."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
from agent.course import FIELDS


def analyze(directory, output):
    files = sorted(directory.glob("*.csv"))
    if not files:
        raise SystemExit(f"No worker CSVs in {directory}")
    rows = []
    for path in files:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise ValueError(f"Unexpected log schema in {path}")
            rows.extend(reader)
    output.mkdir(parents=True, exist_ok=True)
    with (output/"events.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[row["source"], row["game"]].append(row)
    with (output/"summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["source","game","decisions","mean_latency_ms","fallbacks","completed_seats","wins","losses","draws","other_results"])
        for (source, game), batch in sorted(groups.items()):
            decisions = [r for r in batch if r["event"] == "decision"]
            outcomes = {}
            for r in batch:
                if r["event"] == "result":
                    key = (r["match"], r["seat"])
                    if key in outcomes and outcomes[key] != r["outcome"]:
                        raise ValueError("Conflicting outcomes for a seat")
                    outcomes[key] = r["outcome"]
            values = list(outcomes.values())
            writer.writerow([source,game,len(decisions),
                             round(mean(float(r["latency_ms"]) for r in decisions),3) if decisions else "",
                             sum(int(r["fallback"]) for r in decisions),len(values),values.count("won"),
                             values.count("lost"),values.count("drew"),
                             sum(v not in {"won","lost","drew"} for v in values)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("worker_directory", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    analyze(args.worker_directory,args.output_directory)
