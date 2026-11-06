# Verification record

Checked 6 November 2026 against model version 1.0.0 and the versioned demonstration inputs.

| Area | Check | Observed result |
| --- | --- | --- |
| Scheduling | Hand-calculated diamond network, zero-duration milestones, workday boundaries, release dates | Passed |
| Capacity | Shared-resource clash, gap use, active reservation, all scenario intervals | Passed |
| Source validation | Duplicate/missing IDs, cycles, invalid progress and costs, actual precedence | Passed |
| History | Completed actuals and source inputs remain unchanged across options | Passed |
| Financial logic | Hand-computed PV/EV and aggregate SPI/CPI, zero denominator, scenario bridge | Passed |
| Readiness | Missing approval/date/reference, unfinished task, partial acceptance, empty register, invalid state | Passed |
| Simulation | Fixed-seed reproducibility, quantile ordering, histogram totals, event ablation | Passed |
| Workbook calculations | All three cases compared with the independent Python result | Passed |
| Workbook input changes | Later remaining duration propagates; active blank exposed; inactive blank ignored; legitimate zero spending retained | Passed |
| Workbook native calculation | Disposable copies recalculated in bundled LibreOffice with formula caches cleared | All three finish/cost results matched; zero formula errors |
| Browser interaction | Scenario switch, activity search, stream/critical filters, empty state, JSON export | Passed in headless Chrome |
| Browser acceptance example | Missing date remains visible; accepting one temporary record does not accept the programme | Passed |
| Mobile layout | 390-pixel viewport, no document-level horizontal overflow | Passed |
| Visual review | Workbook sheet previews, three-page brief, desktop and mobile report | Reviewed |

The unit/integration suite contains **27 tests**. The core analytical run uses Python's standard library. Generated analysis includes SHA-256 input fingerprints and a fixed seed. A second complete run is compared with the saved analysis and per-option CSVs to check reproducibility.

## Native verification procedure

The authoring engine verifies the model through input changes before export. The separate native check then changes the case selector in disposable XLSX copies, removes old formula-cache values, asks LibreOffice to recalculate, and reads the saved results. The original workbook is not replaced by those copies. This tests formula evaluation in a second engine; it is not a test of a user's installed desktop Excel build.

## Limits

Passing tests establishes the exercised implementation behaviours. It does not validate invented supplier risk, engineering durations, cost estimates, productivity gains or actual release authority. No real Audi data was used, no actual technical evidence was accepted, and no production integrations were tested.

Workbook resource order is fixed. A new priority or topology needs a Python rebuild and review. Browser scenario results are saved calculations, not a live connection to source files. Monte Carlo outputs do not recalculate in Excel.
