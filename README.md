# Power Unit Programme Control

An independent programme-management case study by **Carlos Daniel Marques Freire**.

A supplier delivery slips. This project traces the effect through a fictional power-unit demonstrator, shared test resources, cost forecasts and release evidence, then compares three recovery options. It is designed around the work described in the [Audi Formula Racing programme-management internship](https://audi-formula-racing-students.jobs.personio.de/job/2314893?language=en).

**All programme data is fictional.** This is a demonstrator work package, not a model of Audi's actual development programme, costs, staffing, suppliers or performance. No Audi affiliation or endorsement is claimed. There are no confidential datasets or actual supplier records.

## Start with the result

Open **[the live interactive management report](https://mynameiszorojuro15.github.io/power-unit-programme-control/)**, or download [the offline report](outputs/management_report.html) and open it in a browser. The downloaded report needs no server, accounts or external scripts. GitHub's file viewer displays HTML source rather than running it.

- [Three-page management brief](outputs/audi-2314893/Daniel_Freire_Power_Unit_Case_Study.pdf): recommendation, schedule, uncertainty, cost and decisions.
- [Editable Excel workbook](outputs/audi-2314893/Power_Unit_Programme_Control.xlsx): deterministic scenario selector, activity plan, cost control, evidence, actions and risks.
- [Calculated analysis](outputs/analysis.json): full results, simulation settings and input fingerprints.
- [Five-minute demonstration](docs/DEMO_WALKTHROUGH.md) and [calculation method](docs/METHOD.md).

### What the illustrative case says

The reference programme has **38 activities**, five workstreams, two shared test resources and 12 mandatory evidence records. At the fictional 22 February 2027 status cut-off, the committed finish boundary is 24 May 2027.

| Option | Deterministic finish | P80 finish | On-time trials | Extra recovery spending | Forecast cost |
| --- | --- | --- | ---: | ---: | ---: |
| Current forecast | 25 May 2027 | 4 June 2027 | 2.9% | EUR 0 | EUR 1,232,383 |
| Expedite supply | 18 May 2027 | 25 May 2027 | 78.5% | EUR 18,000 | EUR 1,248,583 |
| Coordinated recovery | 13 May 2027 | 19 May 2027 | 94.2% | EUR 31,000 | EUR 1,261,583 |

Coordinated recovery recovers eight working days in the deterministic model, with higher spending. The recommendation is to reserve that option subject to confirmed supplier commitments and cost approval. It does **not** accept the nine outstanding release records. The three options preserve validation durations and acceptance scope.

These percentages come from **5,000 trials per option with subjective illustrative assumptions**. They are not predictions of Audi's delivery probability. Sensitivity checks retain the original risk probabilities or widen the duration range. Their results are shown in the report and brief. Sampling precision is distinct from uncertainty about the model itself.

## Reproduce the analysis

The calculation engine and offline report builder require only **Python 3.10+ and the standard library**.

```bash
PYTHONPATH=src python3 -m pu_control --validate-only
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m pu_control --report
```

Or install the package with `python3 -m pip install -e .` and run `pu-control --report`.

The CLI supports `--data path`, `--out path`, `--runs N` and `--validate-only`. A short `--runs 200` development run is useful while editing. Use the configured 5,000 trials for the published results.

To rebuild the PDF brief, install the optional report dependency and run:

```bash
python3 -m pip install -e '.[reports]'
python3 scripts/build_brief.py
```

The supplied `.xlsx` is editable in Excel or LibreOffice. Rebuilding it with the optional authoring script requires an installed `@oai/artifact-tool` package. That package is **not required** to reproduce the Python calculations, CSVs, JSON or HTML report. The workbook's fixed resource sequence is documented below and in its opening view.

## Calculations and controls

- **Dependency planning:** finish-to-start relationships, frozen actual dates, source priority, explicit remaining durations and milestone nodes.
- **Resource feasibility:** one assignment at a time on Dyno A and the HIL rig. Resource-order arcs enter the backward pass for float and criticality. The serial algorithm can fill gaps but does not prove an optimal schedule.
- **Progress and cost:** baseline planned value, physical-progress earned value, actual cost, owner ETC, programme SPI/CPI and a reconciled bottom-up forecast.
- **Uncertainty:** triangular remaining durations, one correlated supplier event across two deliveries, repeat-validation exposure and common random draws across options. Quantiles use nearest rank.
- **Readiness:** completed work plus accepted state, reference, approver and valid date. A schedule improvement cannot manufacture accepted evidence.
- **Weekly coordination:** risk triggers, action owners, due dates, and three separate decisions for recovery spending, test sequence and release acceptance.

The Excel workbook uses one live deterministic build with one authoritative case selector. Its resource ordering is fixed to the reference sequence. Python rebuilds the feasible sequence when source logic changes. The workbook does not run Monte Carlo; use the rebuilt HTML/JSON for stochastic results.

## Verification

The repository contains **27 unit/integration tests**, including hand-calculated schedules and earned value, shared-resource conflicts, zero-duration milestones, preserved actuals, invalid records, scenario immutability, cost reconciliation, seed reproducibility and incomplete acceptance.

Additional authoring checks compare all three workbook scenarios with Python, alter a later duration to verify propagation, test a partial acceptance record, and exercise the offline report's scenario selection, search, filters, JSON download and mobile layout. Native workbook recalculation is verified with disposable copies using `scripts/verify_native_workbook.py --soffice /path/to/soffice`. See [verification notes](docs/VERIFICATION.md) for the observed results and limits.

## Public context

- [Audi Formula Racing company overview](https://www.audi.com/en/audi-formula-racing-gmbh-17953): context for power-unit development and the site interfaces.
- [Audi programme-management internship](https://audi-formula-racing-students.jobs.personio.de/job/2314893?language=en): planning, controlling, progress monitoring, risk and process digitalisation.
- [GAO Schedule Assessment Guide](https://www.gao.gov/products/gao-16-89g), December 2015: dependency logic, resources and schedule-risk analysis. This project does not claim formal conformance.

Sources checked 6 November 2026. Work-package definitions, numerical inputs, risk distributions and acceptance rules are independently invented. They are not taken from these sources.

## Repository layout

```text
data/                 Versioned task CSV and configuration, evidence, risks and actions JSON
src/pu_control/       Standard-library engine, CLI and offline report generation
templates/            Self-contained management report template
tests/                Hand-calculated examples and failure cases
scripts/              Demo generator, optional PDF/workbook builders and verification tools
docs/                 Method, demonstration and verification notes
outputs/              Reviewable report, workbook, brief, analysis and per-option schedule CSVs
```

MIT licensed. No tracking, authentication or external service is required to run the report.
