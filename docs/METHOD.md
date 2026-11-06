# Calculation method and data dictionary

## Scope

This is a fictional programme-management work package. ICE, electrical systems, controls and integration are useful coordination workstreams, not a complete engineering decomposition. A real power-unit programme would require deeper product structures, configuration rules, supplier contracts, validation plans and specialist review.

The model supports a decision about recovery spending and scheduling. It does not calculate engine performance, lap time, FIA regulatory compliance or the monetary value of sporting results.

## Time conventions

Time is an integer count of working-day **boundaries** from Monday 11 January 2027. An activity occupies `[start, finish)`. A one-day activity starting on Friday finishes at the following Monday boundary; this represents work through Friday, not work on the weekend. A finish-to-start successor can start at its predecessor's finish boundary.

The example uses Monday to Friday with no holidays. `workday_date` also supports an explicit holiday exclusion list. A real plan must use the approved site and supplier calendars, shutdowns and shift arrangements. The workbook's `WORKDAY` formulas use the unmodified demonstration calendar.

Baseline scheduling starts at day zero. The current status is day 30. Completed activities retain actual start and finish. Unstarted remaining work cannot start before status, release boundary or predecessor completion. Active resource work reserves its remaining slot first.

## Dependency and resource scheduling

`topological` validates unique IDs, predecessor existence and an acyclic graph. Source `order` is a deterministic scheduling priority among eligible nodes; task ID breaks ties.

The scheduler assigns each activity its earliest feasible slot given its predecessors and the already-reserved intervals on its single-capacity resource. It can fill a gap if the entire duration fits. It then adds resource-order arcs to the dependency graph and performs a backward pass:

```text
latest finish = minimum latest start of successors
latest start  = latest finish - scheduled duration
total float   = latest start - scheduled start
```

Remaining activities with zero total float are labelled critical **in that chosen resource sequence**. These labels do not prove that another resource priority would not improve the finish. The model is a feasible serial schedule, not a resource-constrained optimisation solver.

The final activity is a zero-duration demonstrator release-decision milestone. A zero-duration milestone does not occupy a bench. The final graph includes three reviews, and the programme finish is the maximum completion boundary across the full network.

## Task source fields

| Field | Meaning | Unit / rule |
| --- | --- | --- |
| `id` | Stable activity identifier | Unique text key |
| `name`, `stream`, `owner` | Description, workstream, accountable fictional role | Text |
| `preds` | Direct finish-to-start dependencies | Semicolon-separated IDs in CSV |
| `baseline_days` | Original activity duration | Nonnegative integer working days |
| `budget` | Frozen work-package budget | Whole EUR |
| `resource` | One named unit-capacity asset, if applicable | Empty, Dyno A or HIL rig |
| `order` | Deterministic source scheduling priority | Integer |
| `progress` | Supplied physical progress | Number from zero to one |
| `remaining_days` | Owner estimate of remaining elapsed work | Integer working days, independent of progress |
| `actual_start`, `actual_finish` | Historical boundaries at the status cut-off | Integer or blank |
| `actual_cost` | Cost recorded through status | Whole EUR |
| `etc` | Owner estimate of remaining direct cost | Whole EUR |
| `ready_day` | Earliest available workday boundary | Nonnegative integer |

The example generator derives synthetic progress from elapsed fixture durations to make a consistent dataset. That is a fixture-generation shortcut, **not a recommended way to measure engineering accomplishment**. A live implementation should use accepted deliverables, quantities or weighted milestones and independently assessed remaining effort.

## Earned value and bottom-up cost

Planned value is budget multiplied by the fraction of baseline working days elapsed, capped from zero to one. Milestone budget is zero in this dataset. Earned value is budget multiplied by the supplied physical progress. SPI is summed EV divided by summed PV; CPI is summed EV divided by summed actual cost. No task-level ratios are averaged. A zero denominator is unavailable, not a healthy zero.

The decision forecast is:

```text
EAC = actual cost + owner ETC + incremental recovery spending
      + max(0, forecast finish - committed finish) × late support per workday
```

Actual cost is frozen across scenarios. The recovery quotes are programme-level additions. Owner ETC excludes those quotes and the incremental late support, preventing double counting. Cost is stated for this demonstrator scope only. No cost-cap accounting is modelled.

The engine also calculates a CPI-based EAC as a diagnostic in JSON. It is not used as the decision forecast, because a bottom-up owner estimate and scenario-specific spending are available.

## Scenarios and change control

The current forecast retains source remaining estimates. Expediting supply reduces the remaining duration of ERS03 by eight days and ERS04 by five days. Coordinated recovery adds assumed support that reduces INT03, INT08 and PM04 by one day each. Bench test durations, validation requirements and acceptance rules stay unchanged. These are illustrative assumptions requiring owner confirmation, not guaranteed productivity improvements.

The application permits scenarios to change only `remaining_days`, `ready_day` and `etc` on unfinished activities. A scenario cannot rewrite a completed activity or its actual cost. Proposals carry a visible approval state rather than being presented as authorised decisions.

Use `data/tasks.csv` and `data/config.json` as the authoritative analysis inputs. Keep a dated copy before a real status update. The output includes input SHA-256 fingerprints; those prove which exact file version was analysed, not the truth of its contents.

## Monte Carlo assumptions

Each scenario uses 5,000 trials with seed 2314893. Remaining durations use an independent triangular multiplier `(0.90, 1.00, 1.20)`, rounded to the nearest integer day, with a one-day minimum for nonzero work. Zero-duration milestones remain zero.

The model samples one additional future supplier event, affecting both ERS03 and ERS04 with the same 3-to-9-day impact. A separate 3-to-7-day repeat-validation event affects INT05. The events are independent of each other and of the duration multipliers. The shared supplier event creates positive dependence between the two deliveries. The known current delay is already in remaining estimates, so the simulated event represents further disruption.

| Assumption | Current | Expedite | Coordinated recovery |
| --- | ---: | ---: | ---: |
| Further supplier event probability | 25% | 10% | 10% |
| Repeat-validation event probability | 20% | 20% | 15% |

The lower probabilities are uncalibrated illustrative assumptions about supplier commitments and validation preparation. Sensitivity analysis retains 25% and 20% for coordinated recovery and widens the duration range to `(0.80, 1.00, 1.30)` separately.

Common random numbers are used across options and ablations, reducing comparison noise. Nearest-rank quantiles define P50, P80 and P95. The reported 95% sampling margin is `1.96 × sqrt(p × (1-p) / n)`; it describes sampling error only. It is not a confidence interval on real-world programme delivery.

Risk ablation removes one future event, leaving the same draws and all existing delays. The effects are conditional and cannot be added. Criticality is the fraction of trials in which an activity is critical in the chosen resource sequence.

Simulated cost varies only through late support. Material prices, repeated-test direct costs and other commercial exposures are not randomised. A real financial forecast must add those uncertainties separately.

## Evidence acceptance

A mandatory record is accepted only if its task is physically complete, state is Accepted, reference and approver contain non-whitespace text, and acceptance day is present and no later than status. Unknown evidence states and duplicate IDs are rejected. An empty register does not mean release is ready.

All evidence references beginning `DEMO-` are fictional. Actual qualification of approvers, independence, electronic signatures, configuration/version matching and controlled-document access would need real systems and technical authority. This demonstrator does not implement a production document-management or safety approval process.

## Refresh boundaries

The offline HTML embeds saved results and explicitly asks for a rebuild after source changes. Its selectors change the saved scenario being inspected. Search and filters change the visible activity set. A temporary evidence-record demonstration never writes source files or accepts the full release.

The Excel workbook has one live deterministic plan and one case selector. It keeps reference resource-order arcs fixed, so its calculations match the three included options. A different priority, topology, resource assignment or substantial duration change can require a different sequence; rebuild and review Python's result rather than treating the workbook as a general scheduling solver. Monte Carlo does not recalculate in Excel.
