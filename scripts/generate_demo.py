"""Create the explicitly fictional, versioned example dataset. No external data."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pu_control.engine import schedule, workday_date


def generate():
    # id, description, stream, owner role, predecessors, baseline days, kEUR, resource
    definitions = [
        ("PM01", "Scope and acceptance criteria", "Programme", "Programme manager", "", 3, 12, ""),
        ("PM02", "Interface and responsibility agreement", "Programme", "Systems lead", "PM01", 4, 18, ""),
        ("G01", "Requirements review", "Programme", "Technical lead", "PM02", 0, 0, ""),
        ("ICE01", "Combustion assembly requirements", "ICE", "ICE lead", "G01", 5, 22, ""),
        ("ERS01", "Electrical system requirements", "ERS", "ERS lead", "G01", 5, 25, ""),
        ("CTL01", "Controls requirements", "Controls", "Controls lead", "G01", 4, 18, ""),
        ("INT01", "Test article and bench plan", "Integration", "Test lead", "G01", 5, 20, ""),
        ("ICE02", "Detail design and supplier release", "ICE", "ICE lead", "ICE01", 7, 38, ""),
        ("ERS02", "Electrical design and supplier release", "ERS", "ERS lead", "ERS01", 7, 42, ""),
        ("CTL02", "Software architecture", "Controls", "Controls lead", "CTL01;PM02", 6, 28, ""),
        ("INT02", "Bench instrumentation and fixtures", "Integration", "Test lead", "INT01", 8, 32, ""),
        ("ICE03", "Critical castings procurement", "ICE", "Supply chain lead", "ICE02", 12, 85, ""),
        ("ICE04", "Rotating assembly procurement", "ICE", "Supply chain lead", "ICE02", 10, 65, ""),
        ("ERS03", "Energy storage demonstrator delivery", "ERS", "Supply chain lead", "ERS02", 14, 95, ""),
        ("ERS04", "Motor generator demonstrator delivery", "ERS", "Supply chain lead", "ERS02", 12, 80, ""),
        ("CTL03", "Control software implementation", "Controls", "Controls lead", "CTL02", 10, 44, ""),
        ("CTL04", "Hardware in loop test preparation", "Controls", "Validation lead", "CTL02", 7, 25, ""),
        ("ICE05", "Incoming inspection", "ICE", "Quality lead", "ICE03;ICE04", 3, 12, ""),
        ("ERS05", "Electrical incoming inspection", "ERS", "Quality lead", "ERS03;ERS04", 3, 14, ""),
        ("CTL05", "Hardware in loop validation", "Controls", "Validation lead", "CTL03;CTL04", 6, 30, "HIL rig"),
        ("ICE06", "ICE test assembly", "ICE", "Build lead", "ICE05", 5, 35, ""),
        ("ERS06", "Electrical subsystem assembly", "ERS", "Build lead", "ERS05", 4, 28, ""),
        ("ICE07", "ICE subsystem test", "ICE", "Test lead", "ICE06;INT02", 7, 50, "Dyno A"),
        ("ERS07", "Electrical subsystem test", "ERS", "Test lead", "ERS06;INT02", 6, 42, "Dyno A"),
        ("CTL06", "Calibration package review", "Controls", "Controls lead", "CTL05", 3, 14, ""),
        ("G02", "Subsystem evidence review", "Programme", "Technical lead", "ICE07;ERS07;CTL06", 0, 0, ""),
        ("INT03", "Power unit demonstrator integration", "Integration", "Systems lead", "G02", 5, 38, ""),
        ("INT04", "First integrated bench run", "Integration", "Test lead", "INT03", 3, 25, "Dyno A"),
        ("INT05", "Integrated endurance validation", "Integration", "Validation lead", "INT04", 8, 65, "Dyno A"),
        ("INT06", "Thermal and energy validation", "Integration", "Validation lead", "INT04", 6, 48, "Dyno A"),
        ("CTL07", "Calibration refinement", "Controls", "Controls lead", "INT04", 5, 22, "HIL rig"),
        ("INT07", "Teardown and nonconformance review", "Integration", "Quality lead", "INT05;INT06", 3, 18, ""),
        ("INT08", "Corrective action closure", "Integration", "Systems lead", "INT07;CTL07", 4, 26, ""),
        ("INT09", "Regression validation", "Integration", "Validation lead", "INT08", 4, 35, "Dyno A"),
        ("PM03", "Cost to complete reconciliation", "Programme", "Finance lead", "G02", 3, 10, ""),
        ("PM04", "Configuration and evidence dossier", "Programme", "Configuration lead", "INT09;PM03", 3, 14, ""),
        ("PM05", "Cross site interface acceptance", "Programme", "Systems lead", "PM04", 2, 10, ""),
        ("G03", "Demonstrator release decision", "Programme", "Programme manager", "PM05", 0, 0, ""),
    ]
    tasks = []
    for order, (i, name, stream, owner, preds, days, keur, resource) in enumerate(definitions):
        tasks.append(dict(id=i, name=name, stream=stream, owner=owner, preds=preds.split(";") if preds else [],
                          baseline_days=days, budget=keur*1000, resource=resource, order=order,
                          progress=0., remaining_days=days, actual_start=None, actual_finish=None,
                          actual_cost=0, etc=keur*1000, ready_day=0))
    baseline = schedule(tasks, baseline=True)
    actual = [dict(t) for t in tasks]
    extra = {"ERS03": 12, "ERS04": 8, "ICE04": 3, "CTL03": 2, "INT05": 2}
    for t in actual:
        t["baseline_days"] += extra.get(t["id"], 0)
    observed = schedule(actual, baseline=True)
    status = 30
    for t in tasks:
        a = observed["tasks"][t["id"]]
        if a["finish"] <= status:
            t.update(progress=1., actual_start=a["start"], actual_finish=a["finish"], remaining_days=0,
                     actual_cost=round(t["budget"]*(1.03 if t["budget"] else 1)), etc=0)
        elif a["start"] < status:
            # Synthetic physical progress fixture; no real delivery performance is inferred.
            fraction = round((status-a["start"])/a["duration"], 3)
            t.update(progress=fraction, actual_start=a["start"], remaining_days=a["finish"]-status,
                     actual_cost=round(t["budget"]*fraction*1.08), etc=round(t["budget"]*(1-fraction)*1.06))
        else:
            t["etc"] = round(t["budget"]*1.02)
    by_id = {t["id"]: t for t in tasks}
    expedite_changes = {i: {"remaining_days": max(1, by_id[i]["remaining_days"]-reduction)}
                        for i, reduction in (("ERS03", 8), ("ERS04", 5))}
    recovery_changes = {**expedite_changes,
                        "INT03": {"remaining_days": 4},
                        "INT08": {"remaining_days": 3}, "PM04": {"remaining_days": 2}}
    config = dict(start_date="2027-01-11", status_day=status, target_day=baseline["finish"]+5,
                  holidays=[], calendar="Monday to Friday; no holiday exclusions in the fictional demo",
                  finish_convention="Start-of-day boundaries; intervals are [start, finish). A finish date is the next available workday boundary.",
                  seed=2314893, simulation_runs=5000, duration_low=.90, duration_high=1.20,
                  supplier_event_days=[3, 9], retest_days=[3, 7], delay_cost_per_day=1800,
                  cases=[
                      dict(id="current", name="Current forecast", description="Keep current supplier dates and test plan.",
                           task_changes={}, incremental_cost=0, supplier_event_probability=.25, retest_probability=.20, approval="Reference forecast"),
                      dict(id="expedite", name="Expedite supply", description="Reserve supplier finishing capacity and expedited delivery. Retain the same acceptance scope.",
                           task_changes=expedite_changes, incremental_cost=18000, supplier_event_probability=.10, retest_probability=.20, approval="Proposed, not approved"),
                      dict(id="recovery", name="Coordinated recovery", description="Expedite supply plus a dedicated integration engineer and parallel evidence preparation. Test durations and acceptance scope stay unchanged.",
                           task_changes=recovery_changes, incremental_cost=31000, supplier_event_probability=.10, retest_probability=.15, approval="Proposed, not approved")])
    evidence_defs = [
        ("EV01", "Requirements approval", "G01", "Accepted", "Systems lead", "DEMO-REQ-001", "Technical lead", 7),
        ("EV02", "ICE design release", "ICE02", "Accepted", "ICE lead", "DEMO-ICE-DR1", "Technical lead", 19),
        ("EV03", "Electrical design release", "ERS02", "Accepted", "ERS lead", "DEMO-ERS-DR1", "Technical lead", 19),
        ("EV04", "Controls validation report", "CTL05", "Missing", "Controls lead", "", "", None),
        ("EV05", "Incoming inspection records", "ERS05", "Missing", "Quality lead", "", "", None),
        ("EV06", "Subsystem test reports", "G02", "Missing", "Test lead", "", "", None),
        ("EV07", "Endurance validation report", "INT05", "Missing", "Validation lead", "", "", None),
        ("EV08", "Thermal and energy report", "INT06", "Missing", "Validation lead", "", "", None),
        ("EV09", "Nonconformance closure", "INT08", "Missing", "Quality lead", "", "", None),
        ("EV10", "Regression validation report", "INT09", "Missing", "Validation lead", "", "", None),
        ("EV11", "Configuration baseline", "PM04", "Missing", "Configuration lead", "", "", None),
        ("EV12", "Interface acceptance", "PM05", "Missing", "Systems lead", "", "", None),
    ]
    evidence = [dict(id=i, name=name, task_id=task, state=state, owner=owner, reference=ref,
                     approver=approver, accepted_day=day, mandatory=True)
                for i, name, task, state, owner, ref, approver, day in evidence_defs]
    risks = [
        dict(id="R01", name="Further electrical supplier disruption", category="Supply", probability=.25,
             affected_tasks=["ERS03", "ERS04"], impact_days="3 to 9 per affected task, one shared event", owner="Supply chain lead",
             trigger="No confirmed dispatch slot at next supplier review", mitigation="Reserve finishing slot, confirm dispatch evidence and maintain alternate logistics quote.", simulation="supplier"),
        dict(id="R02", name="Integrated test requires repeat work", category="Validation", probability=.20,
             affected_tasks=["INT05"], impact_days="3 to 7 additional working days", owner="Validation lead",
             trigger="Validation acceptance criterion missed", mitigation="Review entry criteria and diagnostic coverage before the test. Repeat testing remains mandatory after a failure.", simulation="retest"),
        dict(id="R03", name="Dyno booking conflict", category="Capacity", probability=None,
             affected_tasks=["ICE07", "ERS07", "INT05", "INT06"], impact_days="Calculated explicitly in the deterministic resource schedule", owner="Test lead",
             trigger="Two assignments request Dyno A on the same working day", mitigation="Protect one integrated slot and review the priority queue weekly.", simulation="resource constraint, not a stochastic event"),
        dict(id="R04", name="Incomplete release evidence", category="Readiness", probability=None,
             affected_tasks=["PM04", "PM05"], impact_days="Release remains blocked until evidence and approvals are complete", owner="Configuration lead",
             trigger="Mandatory record lacks accepted status, reference or approver", mitigation="Review evidence register weekly and assign an owner for each missing item.", simulation="evidence gate, not assigned an invented probability"),
    ]
    actions = [
        dict(id="A01", owner="Supply chain lead", due_day=32, state="Open", linked="R01", action="Obtain a written finishing and dispatch commitment for both electrical demonstrators.", decision="D01"),
        dict(id="A02", owner="Test lead", due_day=33, state="Open", linked="R03", action="Confirm protected Dyno A reservations and the escalation route for a clash.", decision="D02"),
        dict(id="A03", owner="Finance lead", due_day=33, state="Open", linked="D01", action="Validate the incremental recovery quote and avoid double-counting support costs.", decision="D01"),
        dict(id="A04", owner="Validation lead", due_day=34, state="Open", linked="R02", action="Agree test entry criteria and retain acceptance scope across recovery options.", decision="D02"),
        dict(id="A05", owner="Configuration lead", due_day=35, state="Open", linked="R04", action="Assign submission dates for each missing mandatory record.", decision="D03"),
    ]
    root = ROOT / "data"
    root.mkdir(parents=True, exist_ok=True)
    with (root / "tasks.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tasks[0]))
        w.writeheader()
        for t in tasks:
            w.writerow({**t, "preds": ";".join(t["preds"])})
    for name, obj in (("config", config), ("evidence", evidence), ("risks", risks), ("actions", actions)):
        (root / f"{name}.json").write_text(json.dumps(obj, indent=2)+"\n")
    print(f"Generated {len(tasks)} fictional activities; baseline {baseline['finish']} workdays; target {config['target_day']}; status {workday_date(config['start_date'], status)}")


if __name__ == "__main__":
    generate()
