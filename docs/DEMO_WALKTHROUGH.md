# Five minute demonstration

## Minute one

Open `outputs/management_report.html`. Explain the management question: two electrical deliveries are late, the demonstrator shares a dyno, and the next release needs both completed work and accepted evidence.

Start with the current forecast. Read the deterministic finish, P80, illustrative on-time probability and cost forecast. Point out that the programme dates and numerical inputs are fictional.

## Minute two

Open Schedule and capacity. Search for `ERS03`. Compare baseline and remaining forecast. Clear the search, choose ERS, then select Remaining critical activities. Explain how procurement, inspection, assembly and the test sequence are connected.

Show the resource table. Thermal validation and endurance validation request the same dyno. Their dependency dates alone would allow an infeasible overlap; the resource schedule prevents it. Explain why the critical labels apply to this chosen priority sequence.

## Minute three

Switch to Expedite supply, then Coordinated recovery. Return to Decision overview and compare all options. Expediting supply meets the deterministic commitment but still misses it at P80. Coordinated recovery provides more margin and costs more.

Open Risk and uncertainty. Show the sensitivity cases. Explain that the result depends on owner and supplier estimates, and lower event probabilities need evidence. Do not describe the illustrative percentages as calibrated company forecasts.

## Minute four

Open Cost control. Trace forecast cost from actuals to owner ETC, recovery spending and late support. Actual cost stays unchanged across options. Explain why SPI and CPI are based on totals and why a bottom-up estimate is used for the recovery decision.

Open Release evidence. Three records are accepted and nine are outstanding. In the temporary demonstration, choose Accepted, enter a reference and approver, and mark task complete, but leave the date unchecked. Check the record and show the missing prerequisite. Then mark the date valid. The individual record can pass while other records still block release.

## Minute five

Open the Excel workbook and change Controls B4 from 1 to 3. Review the new finish and cost. Increase the coordinated-recovery PM04 remaining duration by two days and observe the forecast move. Restore the original value. Describe the fixed resource-order limitation.

Close with the decisions: confirm the supplier commitment and quote, protect the test sequence, and keep technical acceptance separate. Offer to walk through the tests and source calculations.

## Questions to be ready for

**Why not predict lap time?** The work being demonstrated is programme coordination. This dataset supports schedule, cost and readiness decisions; it does not contain an engineering model for performance.

**Why not use only a Gantt chart?** A useful programme review also needs constraints, financial consequences, uncertainty and acceptance evidence.

**What would change with real data?** Use controlled task/configuration IDs, specialist-approved test plans, actual calendars and capacity, supplier commitments, finance-approved cost definitions and validated risk distributions. Keep the same separation of source data, calculations and decisions.

**Is this production ready?** No. It is a tested portfolio demonstrator. Access control, audit history, approvals, integrations and change-management policy would be needed for operational use.

**What part needs the most judgement?** Remaining-duration estimates, the recoverability of activities, resource priorities and whether the evidence actually supports acceptance. The calculation does not replace that judgement.
