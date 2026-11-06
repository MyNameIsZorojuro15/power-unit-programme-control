"""Recalculate disposable copies in LibreOffice and compare to Python results.

Original deliverable is never replaced. Use --soffice to select the executable.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

NS={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
ROOT=Path(__file__).resolve().parents[1]

def value(archive, sheet, cell):
    tree=ET.fromstring(archive.read(f"xl/worksheets/sheet{sheet}.xml"))
    node=tree.find(f".//m:c[@r='{cell}']",NS)
    if node is None:
        return None
    raw=node.find("m:v",NS)
    if node.attrib.get("t")=="inlineStr":
        return "".join(node.itertext())
    if raw is None:
        return None
    if node.attrib.get("t")=="s":
        strings=ET.fromstring(archive.read("xl/sharedStrings.xml"))
        return "".join(strings[int(raw.text)].itertext())
    if node.attrib.get("t") in {"str","e"}:
        return raw.text
    return float(raw.text)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--soffice",required=True)
    args=p.parse_args()
    data=json.loads((ROOT/"outputs/analysis.json").read_text())
    source=ROOT/"outputs/audi-2314893/Power_Unit_Programme_Control.xlsx"
    tmp=ROOT/"tmp/native"
    tmp.mkdir(parents=True,exist_ok=True)
    results=[]
    for case_no,case in enumerate(data["cases"],1):
        inp=tmp/f"case{case_no}.xlsx"
        with ZipFile(source) as z,ZipFile(inp,"w",ZIP_DEFLATED) as out:
            for name in z.namelist():
                content=z.read(name)
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                    tree=ET.fromstring(content)
                    for node in tree.findall(".//m:c",NS):
                        if node.find("m:f",NS) is not None:
                            cached=node.find("m:v",NS)
                            if cached is not None:
                                node.remove(cached)
                    if name=="xl/worksheets/sheet2.xml":
                        node=tree.find(".//m:c[@r='B4']",NS)
                        node.attrib.pop("t",None)
                        for child in list(node):
                            node.remove(child)
                        ET.SubElement(node,"{"+NS["m"]+"}v").text=str(case_no)
                    content=ET.tostring(tree,encoding="utf-8",xml_declaration=True)
                elif name=="xl/workbook.xml":
                    tree=ET.fromstring(content)
                    calc=tree.find("m:calcPr",NS)
                    if calc is None:
                        calc=ET.SubElement(tree,"{"+NS["m"]+"}calcPr")
                    calc.attrib.update(calcMode="auto",fullCalcOnLoad="1",forceFullCalc="1")
                    content=ET.tostring(tree,encoding="utf-8",xml_declaration=True)
                out.writestr(name,content)
        destination=tmp/f"out{case_no}"
        destination.mkdir(exist_ok=True)
        profile=(tmp/f"profile{case_no}").as_uri()
        proc=subprocess.run([args.soffice,f"-env:UserInstallation={profile}","--headless","--convert-to","xlsx","--outdir",str(destination),str(inp)],capture_output=True,text=True,timeout=55)
        native=destination/inp.name
        if proc.returncode or not native.exists():
            raise RuntimeError(f"Native recalculation failed: {proc.stdout} {proc.stderr}")
        with ZipFile(native) as z:
            finish,eac,accepted=value(z,1,"B7"),value(z,1,"E12"),value(z,1,"B13")
            errors=[]
            for name in z.namelist():
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                    tree=ET.fromstring(z.read(name))
                    errors.extend((name,n.attrib["r"],"".join(n.itertext())) for n in tree.findall(".//m:c[@t='e']",NS))
            assert not errors,errors
            assert finish==case["forecast"]["finish"],(finish,case["forecast"]["finish"])
            assert abs(eac-case["eac"])<.01,(eac,case["eac"])
            assert accepted==3,accepted
            results.append(dict(case=case["id"],finish=finish,eac=eac,accepted=accepted,formula_errors=0))
    (tmp/"checks.json").write_text(json.dumps(results,indent=2)+"\n")
    print(json.dumps(results,indent=2))

if __name__=="__main__":
    main()
