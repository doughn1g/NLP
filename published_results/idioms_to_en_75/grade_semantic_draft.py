"""Apply preliminary judgments against researched source-language meanings."""

from collections import Counter
import csv
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "FINAL_75_IDIOMS_4_MODELS_UNGRADED.xlsx"
OUTPUT = HERE / "GRADED_75_IDIOMS_4_MODELS_SEMANTIC_DRAFT.xlsx"
DECISIONS = HERE / "GRADED_75_IDIOMS_4_MODELS_SEMANTIC_DECISIONS.csv"
SUMMARY = HERE / "GRADED_75_IDIOMS_4_MODELS_SEMANTIC_SUMMARY.csv"
CSV_SOURCE = HERE / "FINAL_75_IDIOMS_4_MODELS_SIDE_BY_SIDE.csv"
MODELS = ("nllb", "qwen", "madlad", "m2m100")
PETCI = "https://github.com/kenantang/petci"
TAMIL = "https://thamizhkalanchiyam360.blogspot.com/2018/09/blog-post_18.html"
TAGALOG = "https://dunonglingkod.mapua.edu.ph/ALEAP/Assets/Mga%20Sawikain%20at%20Salawikain.pdf"
DEPED = "https://www.deped.gov.ph/wp-content/uploads/Q4-LAS-VE8-23.pdf"
TAMIL_ONE = "https://www.tamilvu.org/courses/diploma/a081/a0813/html/a08135qc.htm"

# English interpretations of the source-language definitions, independently
# checked against PETCI's dictionary entries and the cited Tamil/Tagalog lists.
SOURCE_MEANINGS = {
    "zh": [
        "spoil something by adding a needless extra", "address someone unable to appreciate or understand",
        "repair a problem after a loss; better late than never", "fear an imagined danger or become suspicious without cause",
        "have a narrow outlook or limited experience", "wait for chance gains without working",
        "give timely help in hardship", "deceive oneself about an obvious fact",
        "contradict oneself", "stop halfway without completing something",
        "achieve two aims with one action", "achieve two aims with one action",
        "theorize without practical understanding", "mistake a partial view for the whole",
        "use a method that ignores changed circumstances", "incur a loss greater than the gain",
        "take advantage of or worsen someone's existing trouble", "commit with no possibility of retreat",
        "be indecisive or half-hearted", "use another person's power to intimidate",
        "occupy a place without the required ability", "add the decisive finishing touch",
        "come straight to the point", "beam with joy", "have a well-formed plan in mind beforehand",
    ],
    "ta": [
        "be in a situation already beyond control; exact short form needs review",
        "earn a great deal", "be a liar", "spend excessively", "act in great haste",
        "be stubborn or persistent", "go beyond proper limits", "indulge in excessive fantasy",
        "postpone something", "use deceptive talk", "assess someone's qualifications",
        "remain concealed", "be easily deceived", "say something that did not happen",
        "wait and be disappointed", "engage in two activities simultaneously",
        "feel great distress", "have no work to do", "be plainly visible",
        "speak pointlessly", "feel very happy", "cause someone else's ruin",
        "be a person without standing or respect", "use a trick or stratagem", "be a useless person",
    ],
    "tl": [
        "be generous and willingly help others", "spread a story lacking truth",
        "be unfaithful to one's spouse or partner", "a serious quarrel or commotion breaks out",
        "be stunned or stopped short by surprise", "be generous and ready to spend money",
        "remember it or be certain a promise will be kept", "tell lies",
        "be talkative or prone to gossip", "feel nervous", "get married",
        "the children of the home", "one's own home", "owe gratitude for a kindness",
        "quarrel continually", "leave home or run away", "be physically struck or hurt",
        "change one's behavior or opinion", "be very meek or gentle",
        "be a manual worker or laborer", "like to go out or wander",
        "feel strong dislike toward someone", "wait for a long time",
        "show enthusiasm that soon fades", "mention someone or something repeatedly",
    ],
}


def meaning_source(language, number):
    if language == "zh":
        return PETCI
    if language == "ta":
        return TAMIL_ONE if number == 1 else TAMIL
    return DEPED if number == 1 else TAGALOG

# Each set contains the 1-based source idiom numbers in that language.
# All unspecified decisions are 0: the intended meaning is absent.
GRADES = {
    "zh": {
        "nllb": {2: set(), 1: {9}},
        "qwen": {2: {1, 3, 7, 9, 10, 11, 16, 20, 22, 23, 24, 25}, 1: {19, 21}},
        "madlad": {2: {9, 11, 24}, 1: set()},
        "m2m100": {2: set(), 1: {9, 10}},
    },
    "ta": {
        "nllb": {2: set(), 1: set()},
        "qwen": {2: set(), 1: {2, 16}},
        "madlad": {2: set(), 1: {2}},
        "m2m100": {2: set(), 1: set()},
    },
    "tl": {
        "nllb": {2: set(), 1: {3, 14, 18}},
        "qwen": {2: {14, 18}, 1: {3, 15, 16}},
        "madlad": {2: set(), 1: {3, 14, 15, 18, 21}},
        "m2m100": {2: set(), 1: set()},
    },
}

NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
Q = "{" + NS["x"] + "}"


def grade(language, model, number):
    marks = GRADES[language][model]
    assert not marks[2] & marks[1]
    return 2 if number in marks[2] else 1 if number in marks[1] else 0


def cell_text(cell):
    node = cell.find("x:is/x:t", NS)
    return node.text or "" if node is not None else ""


def set_cell(row, column, value):
    address = f"{column}{row.attrib['r']}"
    cell = next((c for c in row.findall("x:c", NS) if c.attrib.get("r") == address), None)
    if cell is None:
        cell = ET.SubElement(row, Q + "c", {"r": address, "t": "inlineStr"})
    cell.attrib["t"] = "inlineStr"
    for child in list(cell):
        cell.remove(child)
    inline = ET.SubElement(cell, Q + "is")
    ET.SubElement(inline, Q + "t").text = str(value)


def main():
    with CSV_SOURCE.open(encoding="utf-8", newline="") as file:
        source_rows = list(csv.DictReader(file))
    assert len(source_rows) == 75
    assert all(len(meanings) == 25 for meanings in SOURCE_MEANINGS.values())
    counts = Counter()
    decisions = []
    with ZipFile(SOURCE) as original:
        sheet = ET.fromstring(original.read("xl/worksheets/sheet1.xml"))
        info = ET.fromstring(original.read("xl/worksheets/sheet2.xml"))
        data_rows = sheet.findall("x:sheetData/x:row", NS)
        assert len(data_rows) == 76
        set_cell(data_rows[0], "F", "Researched idiom meaning (English)")
        for workbook_row, source in zip(data_rows[1:], source_rows):
            cells = {c.attrib["r"].rstrip("0123456789"): cell_text(c)
                     for c in workbook_row.findall("x:c", NS)}
            assert cells["A"] == source["id"]
            language = source["source_lang"]
            number = int(source["id"].rsplit("-", 1)[1])
            source_meaning = SOURCE_MEANINGS[language][number - 1]
            source_uri = meaning_source(language, number)
            set_cell(workbook_row, "F", source_meaning)
            for model, col in zip(MODELS, "KLMN"):
                score = grade(language, model, number)
                set_cell(workbook_row, col, score)
                counts[language, model, score] += 1
                decisions.append({
                    "example_id": source["id"], "source_lang": language,
                    "source_text": source["source_text"],
                    "source_meaning": source_meaning, "meaning_source": source_uri,
                    "draft_meaning_for_comparison_only": source["draft_meaning"],
                    "model": model,
                    "translation": source[model + "_translation"],
                    "semantic_score_0_2": score,
                    "decision": ("Intended meaning preserved" if score == 2 else
                                 "Meaning partly conveyed" if score == 1 else
                                 "Intended meaning absent; literal-only, incorrect, or unclear"),
                })
            set_cell(workbook_row, "S", "Preliminary semantic judgment against researched source meaning; bilingual review needed.")
        assert len(decisions) == 300
        info_rows = info.findall("x:sheetData/x:row", NS)
        for row in info_rows:
            cells = {c.attrib["r"].rstrip("0123456789"): cell_text(c)
                     for c in row.findall("x:c", NS)}
            if cells.get("A") == "Status":
                set_cell(row, "B", "PRELIMINARY source-meaning grades; 300 outputs scored; bilingual review pending")
            elif cells.get("A") == "Grading":
                set_cell(row, "B", "Meaning only: 0 = literal-only/wrong/unclear; 1 = partial; 2 = intended meaning preserved. Naturalness left blank.")
        data = info.find("x:sheetData", NS)
        new_row = ET.SubElement(data, Q + "row", {"r": str(len(info_rows) + 1)})
        set_cell(new_row, "A", "Evaluator")
        set_cell(new_row, "B", "AI preliminary judgment against cited source-language definitions; not blinded or bilingual validated")
        info.find("x:dimension", NS).attrib["ref"] = f"A1:B{len(info_rows) + 1}"
        updated = {
            "xl/worksheets/sheet1.xml": ET.tostring(sheet, encoding="utf-8", xml_declaration=True),
            "xl/worksheets/sheet2.xml": ET.tostring(info, encoding="utf-8", xml_declaration=True),
        }
        with ZipFile(OUTPUT, "w") as target:
            for entry in original.infolist():
                target.writestr(entry, updated.get(entry.filename, original.read(entry.filename)))

    with DECISIONS.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(decisions)
    summary = []
    for language in GRADES:
        for model in MODELS:
            summary.append({"source_lang": language, "model": model,
                            "score_0": counts[language, model, 0],
                            "score_1": counts[language, model, 1],
                            "score_2": counts[language, model, 2],
                            "total": 25})
    with SUMMARY.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    assert all(row["score_0"] + row["score_1"] + row["score_2"] == 25 for row in summary)
    print(f"Wrote {OUTPUT.name}, {DECISIONS.name}, {SUMMARY.name}")


if __name__ == "__main__":
    main()
