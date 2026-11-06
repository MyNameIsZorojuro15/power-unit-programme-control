from pathlib import Path
import json


def html_report(analysis, output):
    template = (Path(__file__).resolve().parents[2]/"templates"/"management_report.html").read_text()
    payload = json.dumps(analysis, allow_nan=False).replace("<", "\\u003c")
    output.write_text(template.replace("__ANALYSIS__", payload))
