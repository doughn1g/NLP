"""Build an Excel comparison of the same idioms translated by four models.

Uses only the Python standard library. A partial workbook requires --allow-missing;
the default requires all 75 predictions from every translation model.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import baseline


NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("", NS)
ET.register_namespace("r", REL)


def q(tag):
    return f"{{{NS}}}{tag}"


def column(number):
    result = ""
    while number:
        number, digit = divmod(number - 1, 26)
        result = chr(65 + digit) + result
    return result


def complexity_labels(path):
    labels = {}
    current = None
    languages = {"Mandarin Chinese": "zh", "Tamil": "ta", "Tagalog": "tl"}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = languages.get(line[3:])
        match = re.match(r"\| (\d\d) \| .*? \| (High|Medium|Low) \|", line)
        if current and match:
            labels[f"idiom-{current}-en-{match.group(1)}"] = match.group(2)
    return labels


def add_cell(row_element, address, value, style=2):
    cell = ET.SubElement(row_element, q("c"), {"r": address, "s": str(style), "t": "inlineStr"})
    inline = ET.SubElement(cell, q("is"))
    text = ET.SubElement(inline, q("t"))
    text.text = str(value) if value is not None else ""


def worksheet(rows, widths, freeze=True, filter_rows=True):
    root = ET.Element(q("worksheet"))
    ET.SubElement(root, q("dimension"), {"ref": f"A1:{column(len(rows[0]))}{len(rows)}"})
    views = ET.SubElement(root, q("sheetViews"))
    view = ET.SubElement(views, q("sheetView"), {"workbookViewId": "0"})
    if freeze:
        ET.SubElement(view, q("pane"), {"xSplit": "4", "ySplit": "1", "topLeftCell": "E2",
                                        "activePane": "bottomRight", "state": "frozen"})
    cols = ET.SubElement(root, q("cols"))
    for i, width in enumerate(widths, 1):
        ET.SubElement(cols, q("col"), {"min": str(i), "max": str(i), "width": str(width), "customWidth": "1"})
    data = ET.SubElement(root, q("sheetData"))
    for row_number, values in enumerate(rows, 1):
        row_element = ET.SubElement(data, q("row"), {"r": str(row_number), "ht": "36" if row_number == 1 else "48", "customHeight": "1"})
        for col_number, value in enumerate(values, 1):
            style = 1 if row_number == 1 else (3 if col_number >= 11 else 2)
            add_cell(row_element, f"{column(col_number)}{row_number}", value, style)
    if filter_rows:
        ET.SubElement(root, q("autoFilter"), {"ref": f"A1:{column(len(rows[0]))}{len(rows)}"})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


STYLES = '''<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Aptos"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF17365D"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment wrapText="1" vertical="center"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf></cellXfs>
</styleSheet>'''


def write_xlsx(path, comparison, info):
    workbook = ET.Element(q("workbook"))
    sheets = ET.SubElement(workbook, q("sheets"))
    ET.SubElement(sheets, q("sheet"), {"name": "Comparison", "sheetId": "1", f"{{{REL}}}id": "rId1"})
    ET.SubElement(sheets, q("sheet"), {"name": "Run info", "sheetId": "2", f"{{{REL}}}id": "rId2"})
    workbook_xml = ET.tostring(workbook, encoding="utf-8", xml_declaration=True)
    content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''
    package_rels = f'''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{PKG}"><Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>'''
    workbook_rels = f'''<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="{PKG}"><Relationship Id="rId1" Type="{REL}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="{REL}/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="{REL}/styles" Target="styles.xml"/></Relationships>'''
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", STYLES)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet(comparison,
                         [24, 18, 20, 25, 17, 36, 40, 40, 40, 40, 18, 18, 18, 18, 22, 22, 22, 22, 45]))
        archive.writestr("xl/worksheets/sheet2.xml", worksheet(info, [28, 110], freeze=False, filter_rows=False))


def export(args):
    source = baseline.examples(args.input)
    predictions = baseline.prediction_map(args.predictions, {baseline.MODELS[x][0] for x in baseline.TRANSLATORS}, source)
    levels = complexity_labels(args.complexity)
    if len(levels) != len(source) or set(levels) != {row["id"] for row in source}:
        raise ValueError("complexity audit IDs do not match input examples")
    missing = [(row["id"], selector) for row in source for selector in baseline.TRANSLATORS
               if (row["id"], baseline.MODELS[selector][0]) not in predictions]
    if missing and not args.allow_missing:
        raise ValueError(f"missing {len(missing)} model translations; use --allow-missing only for a draft workbook")
    for key, prediction in predictions.items():
        if not isinstance(prediction.get("translation"), str) or not prediction["translation"].strip():
            raise ValueError(f"empty translation for {key}")
    header = ["Example ID", "Source language", "Target language", "Source idiom", "Complexity (draft)",
              "Draft meaning (private)", "NLLB translation", "Qwen translation", "MADLAD translation",
              "M2M100 translation", "NLLB meaning 0-2", "Qwen meaning 0-2", "MADLAD meaning 0-2",
              "M2M100 meaning 0-2", "NLLB naturalness 0-2", "Qwen naturalness 0-2",
              "MADLAD naturalness 0-2", "M2M100 naturalness 0-2", "Reviewer notes"]
    # The first ten columns are fixed inspection fields; grading columns remain blank.
    output = [header]
    for row in source:
        translations = []
        for selector in baseline.TRANSLATORS:
            pred = predictions.get((row["id"], baseline.MODELS[selector][0]))
            translations.append(pred["translation"] if pred else "")
        output.append([row["id"], row["source_lang"], row["target_lang"], row["source_text"],
                       levels[row["id"]], row.get("intended_meaning", ""), *translations, *([""] * 9)])
    info = [["Field", "Value"], ["Status", "COMPLETE" if not missing else f"DRAFT: {len(missing)} translations missing"],
            ["Source examples", str(len(source))], ["Input SHA-256", hashlib.sha256(Path(args.input).read_bytes()).hexdigest()],
            ["Complexity", "Provisional analyst labels; require bilingual review"],
            ["Draft meaning", "Private reviewer aid; never given to models"],
            ["Grading", "Enter 0, 1, or 2 for meaning and naturalness after review; this workbook is not blind"],
            ["Model order", ", ".join(baseline.TRANSLATORS)]]
    for selector in baseline.TRANSLATORS:
        model_id, revision, _, _ = baseline.MODELS[selector]
        info.append([selector, f"{model_id} @ {revision}"])
        path = next((Path(path) for path in args.predictions
                     if any(prediction.get("model_id") == model_id for prediction in baseline.read_jsonl(path))), None)
        if path is not None:
            info.append([selector + " file SHA-256", hashlib.sha256(path.read_bytes()).hexdigest()])
    write_xlsx(args.output, output, info)
    print(f"Wrote {len(source)} idioms to {args.output}; missing translations: {len(missing)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/idioms_to_en_draft.jsonl")
    parser.add_argument("--complexity", default="data/idiom_complexity_audit.md")
    parser.add_argument("--predictions", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-missing", action="store_true")
    export(parser.parse_args())


if __name__ == "__main__":
    main()
