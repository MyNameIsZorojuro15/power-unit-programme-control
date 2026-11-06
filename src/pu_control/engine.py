"""Transparent workday scheduling, cost control and evidence-based readiness.

Time is represented as integer working-day boundaries. [s, f) occupies f-s
working days, and finish-to-start successors can start at f. Resource scheduling
uses deterministic serial priority, not an optimisation solver. Percent complete
is a physical-progress estimate; it does not set remaining duration.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path


def workday_date(start: str, offset: int, holidays=()) -> str:
    """Convert a working-day boundary to a date; start must be a workday."""
    d = date.fromisoformat(start)
    excluded = set(holidays)
    if d.weekday() >= 5 or d.isoformat() in excluded or offset < 0:
        raise ValueError("start must be a workday and offset must be nonnegative")
    for _ in range(offset):
        d += timedelta(days=1)
        while d.weekday() >= 5 or d.isoformat() in excluded:
            d += timedelta(days=1)
    return d.isoformat()


def load_data(root: Path):
    config = json.loads((root / "config.json").read_text())
    with (root / "tasks.csv").open(newline="") as f:
        tasks = list(csv.DictReader(f))
    ints = ("baseline_days", "remaining_days", "actual_cost", "budget", "etc", "ready_day", "order")
    for t in tasks:
        for k in ints:
            t[k] = int(t[k])
        t["progress"] = float(t["progress"])
        for k in ("actual_start", "actual_finish"):
            t[k] = int(t[k]) if t[k] != "" else None
        t["preds"] = t["preds"].split(";") if t["preds"] else []
    evidence = json.loads((root / "evidence.json").read_text())
    risks = json.loads((root / "risks.json").read_text())
    actions = json.loads((root / "actions.json").read_text())
    validate(tasks, config)
    return tasks, config, evidence, risks, actions


def topological(tasks):
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task ID")
    by_id = {t["id"]: t for t in tasks}
    for t in tasks:
        if len(t["preds"]) != len(set(t["preds"])):
            raise ValueError(f"duplicate predecessor: {t['id']}")
        if any(p not in by_id for p in t["preds"]):
            raise ValueError(f"missing predecessor: {t['id']}")
    result, done = [], set()
    while len(result) < len(tasks):
        ready = [t for t in tasks if t["id"] not in done and set(t["preds"]) <= done]
        if not ready:
            raise ValueError("dependency cycle")
        chosen = min(ready, key=lambda t: (t["order"], t["id"]))
        result.append(chosen)
        done.add(chosen["id"])
    return result


def validate(tasks, config):
    if not tasks:
        raise ValueError("empty programme")
    if config["status_day"] < 0 or config["target_day"] < config["status_day"]:
        raise ValueError("invalid status/target day")
    if config["delay_cost_per_day"] < 0:
        raise ValueError("negative delay cost")
    ordered = topological(tasks)
    by_id = {t["id"]: t for t in tasks}
    for t in ordered:
        for k in ("baseline_days", "remaining_days", "actual_cost", "budget", "etc", "ready_day"):
            if not isinstance(t[k], int) or t[k] < 0:
                raise ValueError(f"{t['id']}: {k} must be a nonnegative integer")
        if not math.isfinite(t["progress"]) or not 0 <= t["progress"] <= 1:
            raise ValueError(f"{t['id']}: invalid physical progress")
        s, f, pct = t["actual_start"], t["actual_finish"], t["progress"]
        if s is not None and (s < 0 or s > config["status_day"]):
            raise ValueError(f"{t['id']}: actual start outside status window")
        if pct == 1:
            if s is None or f is None or not s <= f <= config["status_day"]:
                raise ValueError(f"{t['id']}: completed task needs valid actual dates")
            if t["remaining_days"] or t["etc"]:
                raise ValueError(f"{t['id']}: completed work has remaining duration/cost")
        elif f is not None:
            raise ValueError(f"{t['id']}: unfinished task has actual finish")
        if 0 < pct < 1 and (s is None or t["remaining_days"] == 0):
            raise ValueError(f"{t['id']}: in-progress work needs start and remaining estimate")
        if pct == 0 and s is not None:
            raise ValueError(f"{t['id']}: zero-progress task has actual start")
        if s is not None:
            for p in t["preds"]:
                pf = by_id[p]["actual_finish"]
                if pf is None or pf > s:
                    raise ValueError(f"{t['id']}: actual predecessor violation")
    # A single-capacity resource cannot have overlapping historical/active work.
    for resource in {t["resource"] for t in tasks if t["resource"]}:
        intervals = sorted((t["actual_start"], t["actual_finish"] if t["actual_finish"] is not None else config["status_day"], t["id"])
                           for t in tasks if t["resource"] == resource and t["actual_start"] is not None)
        if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
            raise ValueError(f"historical resource collision: {resource}")


def slot(start, duration, intervals):
    """Earliest nonoverlapping half-open slot on a unit-capacity resource."""
    if duration == 0:
        return start
    for a, b, _ in sorted(intervals):
        if start + duration <= a:
            break
        if start < b and start + duration > a:
            start = b
    return start


def schedule(tasks, status=0, baseline=False, level_resources=True, durations=None, ready_overrides=None):
    """Serial scheduling with frozen historical facts and forward-only estimates."""
    ordered = topological(tasks)
    rows, bookings = {}, {}
    durations, ready_overrides = durations or {}, ready_overrides or {}
    # Reserve all active resource assignments before not-yet-started work.
    if not baseline and level_resources:
        for t in ordered:
            if t["resource"] and 0 < t["progress"] < 1:
                d = durations.get(t["id"], t["remaining_days"])
                bookings.setdefault(t["resource"], []).append((status, status + d, t["id"]))
    for t in ordered:
        done = not baseline and t["progress"] == 1
        dur = t["baseline_days"] if baseline else durations.get(t["id"], t["remaining_days"])
        if done:
            s, f = t["actual_start"], t["actual_finish"]
        else:
            release = 0 if baseline else ready_overrides.get(t["id"], t["ready_day"])
            earliest = max([0 if baseline else status, release] + [rows[p]["finish"] for p in t["preds"]])
            resource = t["resource"] if level_resources else ""
            active = not baseline and 0 < t["progress"] < 1
            if active:
                if earliest > status:
                    raise ValueError(f"active task has unmet dependency/release: {t['id']}")
                s = status
            else:
                s = slot(earliest, dur, bookings.get(resource, [])) if resource else earliest
                if resource and dur:
                    bookings.setdefault(resource, []).append((s, s + dur, t["id"]))
            f = s + dur
        rows[t["id"]] = {"start": s, "finish": f, "duration": f-s,
                          "resource_wait": 0 if done else s-earliest, "resource": t["resource"],
                          "preds": list(t["preds"]), "done": done}
    # Resource-order arcs make the backwards pass reflect the chosen feasible plan.
    if level_resources:
        for resource in {t["resource"] for t in tasks if t["resource"]}:
            intervals = sorted((r["start"], r["finish"], i) for i, r in rows.items()
                               if r["resource"] == resource and r["duration"] > 0 and not r["done"])
            for a, b in zip(intervals, intervals[1:]):
                if a[1] > b[0]:
                    raise ValueError(f"resource collision: {resource}")
                if a[2] not in rows[b[2]]["preds"]:
                    rows[b[2]]["preds"].append(a[2])
    # Use augmented-graph order rather than source order after resource insertion.
    proxy = [dict(t, preds=rows[t["id"]]["preds"]) for t in tasks]
    finish = max(r["finish"] for r in rows.values())
    successors = {i: [] for i in rows}
    for i, r in rows.items():
        for p in r["preds"]:
            successors[p].append(i)
    for t in reversed(topological(proxy)):
        i = t["id"]
        r = rows[i]
        lf = min((rows[c]["late_start"] for c in successors[i]), default=finish)
        r["late_start"] = lf-r["duration"]
        r["float"] = r["late_start"]-r["start"]
        r["critical"] = not r["done"] and r["float"] == 0
    return {"tasks": rows, "finish": finish,
            "critical_ids": [t["id"] for t in topological(proxy) if rows[t["id"]]["critical"]]}


def earned_value(tasks, baseline, status):
    result = []
    for t in tasks:
        b = baseline["tasks"][t["id"]]
        planned = (min(1, max(0, (status-b["start"])/t["baseline_days"]))
                   if t["baseline_days"] else float(b["finish"] <= status))
        result.append({"id": t["id"], "stream": t["stream"], "budget": t["budget"],
                       "pv": t["budget"]*planned, "ev": t["budget"]*t["progress"],
                       "ac": t["actual_cost"], "etc": t["etc"]})
    totals = {k: round(sum(r[k] for r in result), 2) for k in ("budget", "pv", "ev", "ac", "etc")}
    totals.update(spi=totals["ev"]/totals["pv"] if totals["pv"] else None,
                  cpi=totals["ev"]/totals["ac"] if totals["ac"] else None)
    totals["bottom_up_eac"] = totals["ac"]+totals["etc"]
    totals["cpi_eac"] = totals["budget"]/totals["cpi"] if totals["cpi"] else None
    return {"rows": result, **totals}


def readiness(evidence, tasks, forecast, status):
    by_id = {t["id"]: t for t in tasks}
    seen, rows = set(), []
    for e in evidence:
        if e["id"] in seen or e["task_id"] not in by_id:
            raise ValueError("duplicate evidence ID or unknown task")
        seen.add(e["id"])
        if e["state"] not in {"Accepted", "In review", "Missing", "Rejected"}:
            raise ValueError("unknown evidence state")
        accepted = (e["state"] == "Accepted" and bool(str(e.get("reference") or "").strip())
                    and bool(str(e.get("approver") or "").strip()) and e.get("accepted_day") is not None
                    and 0 <= e["accepted_day"] <= status and by_id[e["task_id"]]["progress"] == 1)
        reason = "Accepted" if accepted else ("Task incomplete" if by_id[e["task_id"]]["progress"] < 1 else
                   "Missing reference or approval" if e["state"] == "Accepted" else e["state"])
        rows.append({**e, "accepted": accepted, "reason": reason,
                     "planned_available_day": forecast["tasks"][e["task_id"]]["finish"]})
    blockers = [r["id"] for r in rows if r["mandatory"] and not r["accepted"]]
    return {"rows": rows, "mandatory": sum(bool(r["mandatory"]) for r in rows),
            "accepted": sum(r["mandatory"] and r["accepted"] for r in rows),
            "blockers": blockers, "ready": not blockers and any(r["mandatory"] for r in rows)}


def apply_case(tasks, config, case):
    changed = copy.deepcopy(tasks)
    by_id = {t["id"]: t for t in changed}
    for task_id, delta in case.get("task_changes", {}).items():
        if task_id not in by_id:
            raise ValueError("scenario references unknown task")
        if by_id[task_id]["progress"] == 1:
            raise ValueError("scenario cannot rewrite completed work")
        if set(delta)-{"remaining_days", "ready_day", "etc"}:
            raise ValueError("scenario can change only remaining estimates")
        by_id[task_id].update(delta)
    validate(changed, config)
    return changed


def evaluate_case(tasks, config, case, evidence):
    if case["incremental_cost"] < 0:
        raise ValueError("negative incremental scenario cost")
    changed = apply_case(tasks, config, case)
    forecast = schedule(changed, config["status_day"])
    unlevelled = schedule(changed, config["status_day"], level_resources=False)
    ac = sum(t["actual_cost"] for t in changed)
    etc = sum(t["etc"] for t in changed)
    slip = max(0, forecast["finish"]-config["target_day"])
    # Delay cost is incremental programme support after the committed target.
    delay_cost = slip*config["delay_cost_per_day"]
    eac = ac+etc+case["incremental_cost"]+delay_cost
    return {"id": case["id"], "name": case["name"], "description": case["description"],
            "approval": case["approval"], "forecast": forecast, "ac": ac, "etc": etc,
            "incremental_cost": case["incremental_cost"], "delay_cost": delay_cost,
            "eac": eac, "budget_variance": eac-sum(t["budget"] for t in tasks),
            "slip": slip, "resource_extension": forecast["finish"]-unlevelled["finish"],
            "readiness": readiness(evidence, changed, forecast, config["status_day"])}


def quantile(values, fraction):
    """Nearest-rank quantile, suitable for discrete working-day outcomes."""
    return sorted(values)[max(0, math.ceil(len(values)*fraction)-1)]


def monte_carlo(tasks, config, case, runs=None, seed=None, risk_off=None):
    """Common random numbers across cases; scenario changes remain explicit.

    Continuous uncertainty is rounded to the nearest whole working day, with
    a one-day minimum for nonzero remaining work. One Bernoulli
    event jointly affects both electrical procurements (correlated supplier
    exposure), and a separate retest event affects integration validation.
    These events are additional future exposure, not the known current delay.
    """
    tasks = apply_case(tasks, config, case)
    n = runs if runs is not None else config["simulation_runs"]
    if n < 1:
        raise ValueError("simulation runs must be positive")
    rng = random.Random(config["seed"] if seed is None else seed)
    finishes, costs, critical_counts = [], [], {t["id"]: 0 for t in tasks}
    supplier_p = case["supplier_event_probability"]
    retest_p = case["retest_probability"]
    if not 0 <= supplier_p <= 1 or not 0 <= retest_p <= 1:
        raise ValueError("risk probabilities outside 0..1")
    for _ in range(n):
        durations = {}
        for t in tasks:
            draw = rng.triangular(config["duration_low"], config["duration_high"], 1.0)
            remaining = t["remaining_days"]
            durations[t["id"]] = max(1, math.floor(remaining*draw+.5)) if remaining else 0
        supplier_draw, retest_draw = rng.random(), rng.random()
        supplier_impact = rng.randint(*config["supplier_event_days"])
        retest_impact = rng.randint(*config["retest_days"])
        if supplier_draw < supplier_p and risk_off != "supplier":
            for i in ("ERS03", "ERS04"):
                if next(t for t in tasks if t["id"] == i)["progress"] < 1:
                    durations[i] += supplier_impact
        if retest_draw < retest_p and risk_off != "retest":
            durations["INT05"] += retest_impact
        plan = schedule(tasks, config["status_day"], durations=durations)
        finishes.append(plan["finish"])
        slip = max(0, plan["finish"]-config["target_day"])
        costs.append(sum(t["actual_cost"]+t["etc"] for t in tasks)+case["incremental_cost"]+slip*config["delay_cost_per_day"])
        for i in plan["critical_ids"]:
            critical_counts[i] += 1
    probability = sum(x <= config["target_day"] for x in finishes)/n
    se = math.sqrt(probability*(1-probability)/n)
    histogram = [{"finish_day": x, "count": finishes.count(x)} for x in sorted(set(finishes))]
    return {"runs": n, "seed": config["seed"] if seed is None else seed,
            "p50": quantile(finishes, .5), "p80": quantile(finishes, .8), "p95": quantile(finishes, .95),
            "on_time_probability": probability, "sampling_margin_95": 1.96*se,
            "p80_cost": quantile(costs, .8), "mean_finish": sum(finishes)/n,
            "histogram": histogram,
            "criticality": {i: c/n for i, c in critical_counts.items()}}


def build_analysis(tasks, config, evidence, risks, actions, data_root):
    baseline = schedule(tasks, baseline=True)
    evm = earned_value(tasks, baseline, config["status_day"])
    results = []
    for case in config["cases"]:
        result = evaluate_case(tasks, config, case, evidence)
        result["simulation"] = monte_carlo(tasks, config, case)
        results.append(result)
    current = results[0]
    ablations = []
    for event in ("supplier", "retest"):
        alternate = monte_carlo(tasks, config, config["cases"][0], risk_off=event)
        ablations.append({"risk": event, "mean_days_reduced": current["simulation"]["mean_finish"]-alternate["mean_finish"],
                          "p80_days_reduced": current["simulation"]["p80"]-alternate["p80"]})
    recovery = config["cases"][2]
    conservative = dict(recovery, supplier_event_probability=.25, retest_probability=.20)
    wider = dict(config, duration_low=.80, duration_high=1.30)
    sensitivities = [
        {"assumption": "Recovery dates, but reference risk probabilities retained",
         "result": monte_carlo(tasks, config, conservative)},
        {"assumption": "Recovery with wider remaining-duration range (0.80, 1.00, 1.30)",
         "result": monte_carlo(tasks, wider, recovery)},
    ]
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(data_root.glob("*")) if p.is_file()}
    return {"project": "Power Unit Programme Control", "data_classification": "Fictional independent case study",
            "config": config, "tasks": tasks, "baseline": baseline, "evm": evm,
            "cases": results, "risk_ablations": ablations, "sensitivities": sensitivities,
            "risks": risks, "actions": actions,
            "provenance": {"input_sha256": hashes, "model_version": "1.0.0"}}
