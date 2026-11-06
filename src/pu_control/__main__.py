from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .engine import build_analysis, load_data, workday_date


def main():
    parser = argparse.ArgumentParser(description="Rebuild the fictional power-unit programme management case study")
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parents[2]/"data")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[2]/"outputs")
    parser.add_argument("--runs", type=int, help="Override the Monte Carlo runs for a development check")
    parser.add_argument("--report", action="store_true", help="Also generate the offline HTML management report")
    parser.add_argument("--validate-only", action="store_true", help="Validate source data without running simulation")
    args = parser.parse_args()
    tasks, config, evidence, risks, actions = load_data(args.data)
    if args.validate_only:
        print(json.dumps({"status": "valid", "activities": len(tasks), "evidence_records": len(evidence)}))
        return
    if args.runs is not None:
        config["simulation_runs"] = args.runs
    analysis = build_analysis(tasks, config, evidence, risks, actions, args.data)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/"analysis.json").write_text(json.dumps(analysis, indent=2, allow_nan=False)+"\n")
    for case in analysis["cases"]:
        records = []
        for t in tasks:
            b, f = analysis["baseline"]["tasks"][t["id"]], case["forecast"]["tasks"][t["id"]]
            records.append(dict(id=t["id"], name=t["name"], stream=t["stream"], owner=t["owner"],
                                baseline_start=b["start"], baseline_finish=b["finish"],
                                forecast_start=f["start"], forecast_finish=f["finish"],
                                forecast_finish_date=workday_date(config["start_date"], f["finish"], config["holidays"]),
                                variance_days=f["finish"]-b["finish"], float_days=f["float"],
                                critical=f["critical"], resource=t["resource"], resource_wait=f["resource_wait"],
                                progress=t["progress"], actual_cost=t["actual_cost"], etc=t["etc"]))
        with (args.out/f"schedule_{case['id']}.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    if args.report:
        from .report import html_report
        html_report(analysis, args.out/"management_report.html")
    print(json.dumps({"activities": len(tasks), "baseline_finish": analysis["baseline"]["finish"],
                      "target_day": config["target_day"], "cases": [
                          {"case": c["id"], "finish": c["forecast"]["finish"], "eac": c["eac"],
                           "p80": c["simulation"]["p80"], "on_time": round(c["simulation"]["on_time_probability"], 3)}
                          for c in analysis["cases"]]}, indent=2))


if __name__ == "__main__":
    main()
