import copy
import unittest
from pathlib import Path

from pu_control.engine import (apply_case, earned_value, evaluate_case, load_data, monte_carlo,
                               quantile, readiness, schedule, slot, topological, validate, workday_date)

ROOT = Path(__file__).resolve().parents[1]


def task(i, days=2, preds=(), resource="", order=0):
    return dict(id=i, name=i, stream="Test", owner="Owner", preds=list(preds), baseline_days=days,
                remaining_days=days, actual_start=None, actual_finish=None, progress=0.,
                budget=100, actual_cost=0, etc=100, ready_day=0, resource=resource, order=order)


class SchedulingTests(unittest.TestCase):
    def test_hand_calculated_diamond(self):
        rows = [task("A", 2), task("B", 5, ["A"], order=1), task("C", 3, ["A"], order=2), task("D", 2, ["B", "C"], order=3)]
        p = schedule(rows, baseline=True)
        self.assertEqual(p["finish"], 9)
        self.assertEqual(p["tasks"]["C"]["float"], 2)
        self.assertEqual(p["critical_ids"], ["A", "B", "D"])

    def test_resource_collision_delays_and_augments_path(self):
        rows = [task("A", 5, resource="Rig"), task("B", 3, resource="Rig", order=1), task("C", 1, ["B"], order=2)]
        p = schedule(rows, baseline=True)
        self.assertEqual(p["finish"], 9)
        self.assertEqual(p["tasks"]["B"]["resource_wait"], 5)
        self.assertIn("A", p["tasks"]["B"]["preds"])
        self.assertEqual(schedule(rows, baseline=True, level_resources=False)["finish"], 5)

    def test_resource_uses_a_gap(self):
        self.assertEqual(slot(0, 3, [(5, 8, "X")]), 0)
        self.assertEqual(slot(4, 3, [(5, 8, "X")]), 8)
        self.assertEqual(slot(8, 2, [(5, 8, "X")]), 8)

    def test_active_resource_is_reserved_first(self):
        waiting = task("A", 2, resource="Rig")
        active = dict(task("B", 4, resource="Rig", order=1), actual_start=1, progress=.5, remaining_days=2)
        p = schedule([waiting, active], status=3)
        self.assertEqual(p["tasks"]["B"]["start"], 3)
        self.assertEqual(p["tasks"]["A"]["start"], 5)

    def test_actuals_frozen(self):
        a = dict(task("A", 3), actual_start=0, actual_finish=5, progress=1., remaining_days=0, etc=0)
        p = schedule([a, task("B", 2, ["A"], order=1)], status=8)
        self.assertEqual(p["tasks"]["A"]["finish"], 5)
        self.assertEqual(p["tasks"]["B"]["start"], 8)

    def test_release_and_zero_duration_milestone(self):
        a = dict(task("A", 3), ready_day=10)
        p = schedule([a, task("M", 0, ["A"], order=1)], status=5)
        self.assertEqual(p["finish"], 13)
        self.assertEqual(p["tasks"]["M"]["duration"], 0)

    def test_input_order_does_not_change_priority(self):
        rows = [task("A", 3, resource="Rig"), task("B", 2, resource="Rig", order=1)]
        self.assertEqual(schedule(rows), schedule(list(reversed(rows))))

    def test_cycle_missing_duplicate(self):
        for rows in ([task("A", preds=["B"]), task("B", preds=["A"])], [task("A", preds=["X"])], [task("A"), task("A")]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                topological(rows)

    def test_workday_calendar(self):
        self.assertEqual(workday_date("2027-01-08", 1), "2027-01-11")
        self.assertEqual(workday_date("2027-01-08", 1, ["2027-01-11"]), "2027-01-12")
        self.assertEqual(workday_date("2027-01-08", 0), "2027-01-08")
        with self.assertRaises(ValueError):
            workday_date("2027-01-09", 0)


class CostAndEvidenceTests(unittest.TestCase):
    def test_hand_calculated_evm_rollup(self):
        a = dict(task("A", 10), progress=.5, budget=100, actual_cost=80, etc=70)
        b = dict(task("B", 10, order=1), progress=.25, budget=300, actual_cost=50, etc=250)
        value = earned_value([a, b], schedule([a, b], baseline=True), 5)
        self.assertEqual(value["pv"], 200)
        self.assertEqual(value["ev"], 125)
        self.assertAlmostEqual(value["cpi"], 125/130)
        self.assertEqual(value["spi"], .625)
        self.assertEqual(value["bottom_up_eac"], 450)

    def test_no_progress_ratios_are_unavailable(self):
        a = task("A")
        value = earned_value([a], schedule([a], baseline=True), 0)
        self.assertIsNone(value["cpi"])
        self.assertIsNone(value["spi"])

    def test_evidence_requires_completed_task_and_approval(self):
        a = task("A")
        e = dict(id="E", task_id="A", mandatory=True, state="Accepted", reference="DEMO-X", approver="Lead", accepted_day=1)
        p = schedule([a], 3)
        self.assertFalse(readiness([e], [a], p, 3)["ready"])
        a.update(progress=1., actual_start=0, actual_finish=2, remaining_days=0, etc=0)
        p = schedule([a], 3)
        self.assertTrue(readiness([e], [a], p, 3)["ready"])
        for key, value in (("reference", ""), ("approver", ""), ("accepted_day", None), ("accepted_day", 4), ("state", "Rejected")):
            with self.subTest(key=key, value=value):
                self.assertFalse(readiness([{**e, key: value}], [a], p, 3)["ready"])

    def test_one_accepted_record_does_not_clear_other_blocker(self):
        a = dict(task("A"), progress=1., actual_start=0, actual_finish=2, remaining_days=0, etc=0)
        e = dict(id="E1", task_id="A", mandatory=True, state="Accepted", reference="DEMO-X", approver="Lead", accepted_day=2)
        other = dict(e, id="E2", state="Missing", reference="", approver="", accepted_day=None)
        r = readiness([e, other], [a], schedule([a], 3), 3)
        self.assertEqual(r["accepted"], 1)
        self.assertEqual(r["blockers"], ["E2"])
        self.assertFalse(r["ready"])

    def test_empty_evidence_never_means_ready(self):
        self.assertFalse(readiness([], [task("A")], schedule([task("A")]), 0)["ready"])


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks, cls.config, cls.evidence, cls.risks, cls.actions = load_data(ROOT/"data")

    def test_fixture_validation_and_all_precedence(self):
        validate(self.tasks, self.config)
        for case in self.config["cases"]:
            p = evaluate_case(self.tasks, self.config, case, self.evidence)["forecast"]
            for i, row in p["tasks"].items():
                for pred in row["preds"]:
                    self.assertLessEqual(p["tasks"][pred]["finish"], row["start"], (i, pred))

    def test_cost_bridge_reconciles_and_actuals_do_not_change(self):
        ac = sum(t["actual_cost"] for t in self.tasks)
        for case in self.config["cases"]:
            r = evaluate_case(self.tasks, self.config, case, self.evidence)
            self.assertEqual(r["ac"], ac)
            self.assertEqual(r["eac"], r["ac"]+r["etc"]+r["incremental_cost"]+r["delay_cost"])

    def test_cases_do_not_mutate_inputs_or_accept_evidence(self):
        original = copy.deepcopy(self.tasks)
        result = evaluate_case(self.tasks, self.config, self.config["cases"][2], self.evidence)
        self.assertEqual(self.tasks, original)
        self.assertFalse(result["readiness"]["ready"])
        self.assertEqual(result["readiness"]["accepted"], 3)

    def test_recovery_preserves_test_durations(self):
        base = {t["id"]: t for t in self.tasks}
        for case in self.config["cases"]:
            for t in apply_case(self.tasks, self.config, case):
                if "validation" in t["name"].lower() or t["resource"]:
                    self.assertEqual(t["remaining_days"], base[t["id"]]["remaining_days"])

    def test_cannot_rewrite_actuals(self):
        with self.assertRaises(ValueError):
            apply_case(self.tasks, self.config, dict(task_changes={"PM01": {"remaining_days": 1}}))
        with self.assertRaises(ValueError):
            apply_case(self.tasks, self.config, dict(task_changes={"ERS03": {"progress": 1}}))

    def test_simulation_reproducibility_and_bounds(self):
        c = self.config["cases"][0]
        a = monte_carlo(self.tasks, self.config, c, runs=40)
        self.assertEqual(a, monte_carlo(self.tasks, self.config, c, runs=40))
        self.assertLessEqual(a["p50"], a["p80"])
        self.assertLessEqual(a["p80"], a["p95"])
        self.assertEqual(sum(b["count"] for b in a["histogram"]), 40)
        self.assertTrue(0 <= a["on_time_probability"] <= 1)

    def test_risk_removal_does_not_increase_outcome(self):
        a = monte_carlo(self.tasks, self.config, self.config["cases"][0], runs=50)
        b = monte_carlo(self.tasks, self.config, self.config["cases"][0], runs=50, risk_off="supplier")
        self.assertLessEqual(b["mean_finish"], a["mean_finish"])

    def test_validation_rejects_bad_values(self):
        for key, value in (("remaining_days", -1), ("progress", 1.1), ("progress", float("nan")), ("etc", -1)):
            rows = copy.deepcopy(self.tasks)
            rows[14][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(rows, self.config)

    def test_nearest_rank_quantile(self):
        self.assertEqual(quantile([1, 2, 3, 4, 5], .8), 4)

    def test_invalid_cost_and_risk_rejected(self):
        case = dict(self.config["cases"][0], incremental_cost=-1)
        with self.assertRaises(ValueError):
            evaluate_case(self.tasks, self.config, case, self.evidence)
        with self.assertRaises(ValueError):
            monte_carlo(self.tasks, self.config, dict(case, supplier_event_probability=1.1), runs=1)

    def test_actual_precedence_rejected(self):
        rows = copy.deepcopy(self.tasks)
        rows[3]["actual_start"] = 0
        with self.assertRaises(ValueError):
            validate(rows, self.config)

    def test_duplicate_evidence_and_unknown_state_rejected(self):
        plan = schedule(self.tasks, self.config["status_day"])
        with self.assertRaises(ValueError):
            readiness([self.evidence[0], self.evidence[0]], self.tasks, plan, self.config["status_day"])
        with self.assertRaises(ValueError):
            readiness([dict(self.evidence[0], state="Assumed accepted")], self.tasks, plan, self.config["status_day"])

    def test_no_resource_overlap_in_all_cases(self):
        for case in self.config["cases"]:
            plan = evaluate_case(self.tasks, self.config, case, self.evidence)["forecast"]
            for resource in ("Dyno A", "HIL rig"):
                intervals = sorted((r["start"], r["finish"]) for r in plan["tasks"].values()
                                   if r["resource"] == resource and r["duration"])
                for a, b in zip(intervals, intervals[1:]):
                    self.assertLessEqual(a[1], b[0])


if __name__ == "__main__":
    unittest.main()
