"""Render a concise, three-page management case study from calculated results."""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Line, PolyLine, Rect, String
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from pu_control.engine import workday_date

D = json.loads((ROOT/"outputs/analysis.json").read_text())
C = D["config"]
OUT = ROOT/"outputs/audi-2314893"
QA = ROOT/"tmp/brief"
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)
ink, muted, red, line = "#18232B", "#5B676B", "#AC2D3A", "#D9DEDA"

def date_for(day):
    from datetime import date
    return date.fromisoformat(workday_date(C["start_date"], day)).strftime("%d %b %Y")

def money(x):
    return f"EUR {x:,.0f}"

def percent(x):
    return f"{100*x:.1f}%"


def charts():
    cdf = Drawing(487, 164)
    left, bottom, width, height = 35, 26, 435, 112
    low, high = 82, 120
    for v in (0, 25, 50, 75, 100):
        y = bottom+height*v/100
        cdf.add(Line(left,y,left+width,y,strokeColor=colors.HexColor(line),strokeWidth=.4))
        cdf.add(String(left-8,y-2,str(v),textAnchor="end",fontName="Helvetica",fontSize=7,fillColor=colors.HexColor(muted)))
    for day in range(low,high+1,5):
        x=left+(day-low)/(high-low)*width
        cdf.add(String(x,12,str(day),textAnchor="middle",fontName="Helvetica",fontSize=7,fillColor=colors.HexColor(muted)))
    for index,(case, col) in enumerate(zip(D["cases"], [red, "#8D9693", "#315B48"])):
        h = case["simulation"]["histogram"]
        cumulative, points = 0, []
        for item in h:
            if not low <= item["finish_day"] <= high:
                continue
            x=left+(item["finish_day"]-low)/(high-low)*width
            points.extend([x,bottom+height*cumulative/case["simulation"]["runs"]])
            cumulative+=item["count"]
            points.extend([x,bottom+height*cumulative/case["simulation"]["runs"]])
        cdf.add(PolyLine(points,strokeColor=colors.HexColor(col),strokeWidth=1.6))
        lx=40+index*145
        cdf.add(Line(lx,155,lx+12,155,strokeColor=colors.HexColor(col),strokeWidth=2))
        cdf.add(String(lx+16,152,case["name"],fontName="Helvetica",fontSize=7.3,fillColor=colors.HexColor(ink)))
    tx=left+(C["target_day"]-low)/(high-low)*width
    cdf.add(Line(tx,bottom,tx,bottom+height,strokeColor=colors.HexColor(red),strokeWidth=.7,strokeDashArray=[3,2]))
    cdf.add(String(250,0,"Finish boundary in working days from programme start",textAnchor="middle",fontName="Helvetica",fontSize=7,fillColor=colors.HexColor(muted)))
    ids = ["ERS03", "ERS04", "ICE07", "ERS07", "INT03", "INT05", "INT06", "INT08", "INT09", "PM04", "PM05"]
    by_id = {t["id"]: t for t in D["tasks"]}
    gantt=Drawing(487,196)
    left,width=222,260
    scale=width/72
    for day in range(30,101,10):
        x=left+(day-28)*scale
        gantt.add(Line(x,23,x,188,strokeColor=colors.HexColor(line),strokeWidth=.4))
        gantt.add(String(x,12,str(day),textAnchor="middle",fontName="Helvetica",fontSize=7,fillColor=colors.HexColor(muted)))
    for n, task_id in enumerate(ids):
        y=180-n*14
        gantt.add(String(0,y-2,f"{task_id}  {by_id[task_id]['name']}",fontName="Helvetica",fontSize=7.2,fillColor=colors.HexColor(ink)))
        for offset, case, col in [(1, D["cases"][0], red), (-4, D["cases"][2], "#354B60")]:
            t = case["forecast"]["tasks"][task_id]
            gantt.add(Rect(left+(t["start"]-28)*scale,y+offset,t["duration"]*scale,4,fillColor=colors.HexColor(col),strokeWidth=0))
    tx=left+(C["target_day"]-28)*scale
    gantt.add(Line(tx,23,tx,188,strokeColor=colors.HexColor(red),strokeWidth=.8,strokeDashArray=[3,2]))
    return gantt,cdf


styles = {
    "title": ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=27, leading=30, textColor=colors.HexColor(ink), spaceAfter=13),
    "kicker": ParagraphStyle("Kicker", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=colors.HexColor(red), spaceAfter=10),
    "h": ParagraphStyle("Heading", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.black, spaceBefore=12, spaceAfter=7),
    "body": ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=14.3, textColor=colors.HexColor(ink), spaceAfter=8),
    "small": ParagraphStyle("Small", fontName="Helvetica", fontSize=8.4, leading=11, textColor=colors.HexColor(muted), spaceAfter=7),
    "cell": ParagraphStyle("Cell", fontName="Helvetica", fontSize=8.8, leading=11.7, textColor=colors.HexColor(ink)),
    "th": ParagraphStyle("TableHeader", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white),
}

def p(text, style="body"):
    return Paragraph(text, styles[style])

def table(headers, rows, widths):
    values = [[p(escape(str(x)), "th") for x in headers]]+[[p(escape(str(x)), "cell") for x in row] for row in rows]
    t = Table(values, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(ink)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                           ("LINEBELOW", (0, 1), (-1, -1), .4, colors.HexColor(line))]))
    return t

def footer(canvas, doc):
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor(muted))
    canvas.drawString(19*mm, 13*mm, "Daniel Freire | Independent case study | Fictional programme data")
    canvas.drawRightString(A4[0]-19*mm, 13*mm, str(doc.page))

def main():
    gantt,cdf=charts()
    cur, exp, rec = D["cases"]
    story = [p("PROGRAMME MANAGEMENT CASE STUDY", "kicker"), p("Power unit development<br/>programme control", "title"),
             p("A supplier delivery slips. Which recovery option protects the next demonstrator release, and what must management approve?"),
             p("Carlos Daniel Marques Freire | Prepared for the Audi Formula Racing programme-management internship | 6 November 2026", "small"),
             p("Recommendation", "h"),
             p(f"Reserve the coordinated recovery option, subject to a confirmed supplier commitment and an approved {money(rec['incremental_cost'])} quote. In this fictional case, it brings the deterministic finish forward by {cur['forecast']['finish']-rec['forecast']['finish']} working days and raises the illustrative on-time probability from {percent(cur['simulation']['on_time_probability'])} to {percent(rec['simulation']['on_time_probability'])}."),
             p(f"The committed finish boundary is {date_for(C['target_day'])}. The current forecast is {date_for(cur['forecast']['finish'])}; its P80 boundary is {date_for(cur['simulation']['p80'])}. Expediting supply alone meets the deterministic date but its P80 result remains beyond the commitment."),
             table(["Option", "Finish", "P80", "On time", "Recovery cost"],
                   [[c["name"], date_for(c["forecast"]["finish"]), date_for(c["simulation"]["p80"]), percent(c["simulation"]["on_time_probability"]), money(c["incremental_cost"])] for c in D["cases"]], [117, 82, 82, 63, 143]),
             Spacer(1, 6),
             p("Decision requested", "h"),
             p("D01: Supply chain confirms the finishing and dispatch slots. Finance validates recovery spending. The programme manager decides whether to reserve the option.<br/>D02: The test lead protects the agreed bench sequence. Validation keeps the same test scope and acceptance criteria.<br/>D03: The technical authority accepts release evidence separately from the forecast."),
             p("Scope", "h"),
             p("The model covers 38 activities across programme coordination, ICE, electrical systems, controls and integration. It represents a small demonstrator work package. Durations, costs, risks, resource capacity and evidence records are invented. No Audi internal data, regulatory interpretation or engineering-performance prediction is used.", "small"),
             PageBreak(),
             p("SCHEDULE AND RISK", "kicker"), p("Make the consequences visible", "title"),
             p("Electrical procurement moves subsystem assembly and the shared dyno sequence. Shortening one delivery does not recover the full programme delay because a second delivery and resource reservations can become controlling constraints."),
             gantt,
             p("Red: current forecast. Blue: coordinated recovery. Selected activities shown; the interactive report and CSV exports include the full network.", "small"),
             p("A forecast date needs an uncertainty range", "h"),
             cdf,
             p(f"Each option uses {C['simulation_runs']:,} trials and common random numbers. Remaining durations vary with a triangular multiplier ({C['duration_low']}, 1.00, {C['duration_high']}). One future supplier event affects both electrical deliveries; a separate event adds repeat validation. These are additional exposures, beyond the already-known delay.", "small"),
             table(["Recovery assumption check", "P80 finish", "On-time trials"],
                   [[s["assumption"], date_for(s["result"]["p80"]), percent(s["result"]["on_time_probability"])] for s in D["sensitivities"]], [315, 90, 82]),
             Spacer(1, 5),
             p("The probabilities are illustrative planning outputs. They are sensitive to subjective durations and event assumptions. A real programme would validate these inputs with package owners, suppliers and test engineers before making a commitment.", "small"),
             PageBreak(),
             p("COST AND OPERATING WORKFLOW", "kicker"), p("Keep decisions traceable", "title"),
             p("Cost at completion", "h"),
             table(["EUR, fictional demonstrator scope", "Current", "Coordinated recovery"],
                   [["Actual cost at status", money(cur["ac"]), money(rec["ac"])],
                    ["Owner estimate to complete", money(cur["etc"]), money(rec["etc"])],
                    ["Incremental recovery", money(cur["incremental_cost"]), money(rec["incremental_cost"])],
                    ["Late support after commitment", money(cur["delay_cost"]), money(rec["delay_cost"])],
                    ["Forecast cost at completion", money(cur["eac"]), money(rec["eac"])],
                    ["Baseline budget", money(D["evm"]["budget"]), money(D["evm"]["budget"])]], [247, 120, 120]),
             p("Forecast cost reconciles to actuals plus remaining estimates, recovery spending and incremental support after the target. The model does not value an F1 championship point or infer the financial value of an earlier release. Simulated cost uncertainty includes late support only.", "small"),
             p("Weekly review workflow", "h"),
             p("1. Package owners update physical progress, actual dates, remaining duration and cost estimates.<br/>2. The planning engine checks IDs, dependency logic, actuals and resource conflicts, then rebuilds the forecast.<br/>3. Programme management reviews changed milestones, cost, risk and the test sequence with supply chain and finance.<br/>4. Decisions receive an owner and due date. Evidence owners submit traceable records for technical acceptance."),
             p("Release readiness", "h"),
             p(f"Only {cur['readiness']['accepted']} of {cur['readiness']['mandatory']} mandatory records are accepted at the status date. Recovery spending does not clear the other {len(cur['readiness']['blockers'])} records. Acceptance requires completed work, an accepted state, a reference, an approver and a date no later than the status cut-off."),
             p("Verification and practical limits", "h"),
             p("The source includes hand-calculated scheduling and earned-value tests, resource-collision tests, frozen-actual checks and evidence failure cases. Excel recalculation is checked against the Python result for all three options. The workbook keeps a fixed resource order; Python can fill new gaps when the network is rebuilt. Neither engine proves an optimal schedule. Full staffing, holiday calendars, FIA rules and other programmes' test demand need separate treatment.", "small"),
             p("Public context and references", "h"),
             p('Audi internship: <link href="https://audi-formula-racing-students.jobs.personio.de/job/2314893?language=en" color="#274B64">Personio job 2314893</link>. Audi power-unit context: <link href="https://www.audi.com/en/audi-formula-racing-gmbh-17953" color="#274B64">Audi Formula Racing company overview</link>. Scheduling reference: <link href="https://www.gao.gov/products/gao-16-89g" color="#274B64">GAO Schedule Assessment Guide</link>, December 2015. Accessed 6 November 2026. No formal compliance claim.', "small")]
    doc = SimpleDocTemplate(str(OUT/"Daniel_Freire_Power_Unit_Case_Study.pdf"), pagesize=A4,
                            rightMargin=19*mm, leftMargin=19*mm, topMargin=17*mm, bottomMargin=22*mm,
                            title="Power Unit Programme Control - Independent Case Study", author="Carlos Daniel Marques Freire")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT/"Daniel_Freire_Power_Unit_Case_Study.pdf")


if __name__ == "__main__":
    main()
