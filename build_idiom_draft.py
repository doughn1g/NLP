"""Create the 75-row isolated-idiom draft for translation into English.

The lists are research seeds, not bilingual-reviewed benchmark labels.
Run: python build_idiom_draft.py
"""

import json
from pathlib import Path


PETCI = "data/petci/filtered.json"
TAMIL_SOURCE = "https://thamizhkalanchiyam360.blogspot.com/2018/09/blog-post_18.html"
TAGALOG_SOURCE = "https://dunonglingkod.mapua.edu.ph/ALEAP/Assets/Mga%20Sawikain%20at%20Salawikain.pdf"

# Idiom, draft English meaning. Meanings are private reviewer aids, never model input.
ZH = [
    ("画蛇添足", "make something worse by adding unnecessary detail"),
    ("对牛弹琴", "speak to an audience that cannot appreciate or understand"),
    ("亡羊补牢", "take corrective action after a loss"),
    ("杯弓蛇影", "be frightened by an imagined danger"),
    ("井底之蛙", "have a narrow view of the world"),
    ("守株待兔", "wait passively for luck instead of working"),
    ("雪中送炭", "give timely help to someone in need"),
    ("掩耳盗铃", "deceive oneself while doing something obviously wrong"),
    ("自相矛盾", "contradict oneself"),
    ("半途而废", "give up halfway"),
    ("一举两得", "achieve two aims with one action"),
    ("一箭双雕", "achieve two goals with one move"),
    ("纸上谈兵", "discuss strategy without practical experience"),
    ("盲人摸象", "judge a whole from only one part"),
    ("刻舟求剑", "cling to an outdated method despite changed circumstances"),
    ("得不偿失", "suffer a loss that outweighs the gain"),
    ("落井下石", "make things worse for someone already in trouble"),
    ("破釜沉舟", "commit fully by removing the possibility of retreat"),
    ("三心二意", "be indecisive or halfhearted"),
    ("狐假虎威", "use someone else's power to intimidate people"),
    ("滥竽充数", "fill a position without having the needed ability"),
    ("画龙点睛", "add a finishing touch that brings something to life"),
    ("开门见山", "get straight to the point"),
    ("眉开眼笑", "beam with happiness"),
    ("胸有成竹", "have a well-considered plan beforehand"),
]

TA = [
    ("தலைக்கு மேல் வெள்ளம்", "be overwhelmed by trouble", "data/pilot.jsonl"),
    ("அள்ளிக் குவித்தல்", "earn or accumulate a great deal", TAMIL_SOURCE),
    ("அண்டப்புழுகன்", "a habitual liar", TAMIL_SOURCE),
    ("அள்ளியிறைத்தல்", "spend far too much", TAMIL_SOURCE),
    ("அரக்கப் பறக்க", "in a great hurry", TAMIL_SOURCE),
    ("அழுங்குப்பிடி", "stubbornly hold one's ground", TAMIL_SOURCE),
    ("அகலக் கால் வைத்தல்", "overreach or go beyond one's means", TAMIL_SOURCE),
    ("ஆகாயக் கோட்டை", "an unrealistic dream or fantasy", TAMIL_SOURCE),
    ("ஆறப்போடல்", "put something off until later", TAMIL_SOURCE),
    ("ஆசை வார்த்தை", "deceptive or enticing sweet talk", TAMIL_SOURCE),
    ("ஆழம் பார்த்தல்", "test someone's ability or character", TAMIL_SOURCE),
    ("இலை மறை காய்", "something kept concealed", TAMIL_SOURCE),
    ("இளிச்சவாயன்", "a gullible person", TAMIL_SOURCE),
    ("இட்டுக்கட்டுதல்", "invent a false story", TAMIL_SOURCE),
    ("இலவு காத்த கிளி", "wait in vain and end up disappointed", TAMIL_SOURCE),
    ("இரண்டு தோணியில் கால் வைத்தல்", "try to pursue two incompatible paths at once", TAMIL_SOURCE),
    ("ஈரல் கருகுதல்", "suffer intense distress", TAMIL_SOURCE),
    ("ஈயோட்டுதல்", "sit idle with nothing to do", TAMIL_SOURCE),
    ("உள்ளங்கையில் நெல்லிக்கனி", "something plain and obvious", TAMIL_SOURCE),
    ("உப்பில்லாப் பேச்சு", "pointless or empty talk", TAMIL_SOURCE),
    ("உச்சி குளிர்தல்", "feel very pleased", TAMIL_SOURCE),
    ("உலை வைத்தல்", "bring ruin on someone", TAMIL_SOURCE),
    ("அரை மனிதன்", "a person held in low regard", TAMIL_SOURCE),
    ("அகடவிகடம்", "a cunning trick", TAMIL_SOURCE),
    ("உதவாக்கரை", "a useless person", TAMIL_SOURCE),
]

TL = [
    ("bukas ang palad", "generous and willing to help", "data/pilot.jsonl"),
    ("balitang kutsero", "an untrue rumor", TAGALOG_SOURCE),
    ("naglalaro ng apoy", "engaging in a dangerous affair or infidelity", TAGALOG_SOURCE),
    ("naghalo ang balat sa tinalupan", "a serious quarrel broke out", TAGALOG_SOURCE),
    ("parang natuka ng ahas", "left speechless by surprise", TAGALOG_SOURCE),
    ("bulang-gugo", "generous with money", TAGALOG_SOURCE),
    ("itaga mo sa bato", "remember or trust that a promise will be kept", TAGALOG_SOURCE),
    ("maglubid ng buhangin", "tell lies", TAGALOG_SOURCE),
    ("makati ang dila", "talkative or prone to gossip", TAGALOG_SOURCE),
    ("umaalon ang dibdib", "feel nervous or anxious", TAGALOG_SOURCE),
    ("pag-iisang dibdib", "getting married", TAGALOG_SOURCE),
    ("anghel ng tahanan", "a child in the family", TAGALOG_SOURCE),
    ("sariling pugad", "one's own home", TAGALOG_SOURCE),
    ("utang na loob", "a debt of gratitude", TAGALOG_SOURCE),
    ("parang aso't pusa", "always quarreling", TAGALOG_SOURCE),
    ("nag-alsa balutan", "left home or ran away", TAGALOG_SOURCE),
    ("pinagbubuhatan ng kamay", "subjected to physical violence", TAGALOG_SOURCE),
    ("nagbabagong-loob", "changing one's ways for the better", TAGALOG_SOURCE),
    ("di makabasag-pinggan", "meek or very gentle", TAGALOG_SOURCE),
    ("anak-pawis", "a laborer or working-class person", TAGALOG_SOURCE),
    ("makati ang paa", "restless and fond of going out", TAGALOG_SOURCE),
    ("mabigat ang dugo", "feel strong dislike toward someone", TAGALOG_SOURCE),
    ("namuti ang mata", "wait for a very long time", TAGALOG_SOURCE),
    ("ningas-cogon", "enthusiasm that fades quickly", TAGALOG_SOURCE),
    ("bukambibig", "someone or something mentioned constantly", TAGALOG_SOURCE),
]


def build():
    petci = {item["chinese"]: item["id"] for item in json.loads(Path(PETCI).read_text(encoding="utf-8"))}
    assert len(ZH) == len(TA) == len(TL) == 25
    rows = []
    for lang, items in (("zh", ZH), ("ta", TA), ("tl", TL)):
        seen = set()
        for number, entry in enumerate(items, 1):
            idiom, meaning = entry[:2]
            assert idiom not in seen
            seen.add(idiom)
            source = PETCI if lang == "zh" else entry[2]
            if lang == "zh":
                assert idiom in petci, f"Missing PETCI idiom: {idiom}"
            rows.append({"id": f"idiom-{lang}-en-{number:02d}", "source_lang": lang, "target_lang": "en",
                         "kind": "idiom", "group_id": f"{lang}_{number:02d}", "idiom": idiom,
                         "source_text": idiom, "context_status": "isolated_idiom",
                         "intended_meaning": meaning, "review_status": "draft",
                         "source_reference": source,
                         "source_record_id": petci[idiom] if lang == "zh" else None})
    out = Path("data/idioms_to_en_draft.jsonl")
    out.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(f"Wrote {len(rows)} draft idioms to {out}")


if __name__ == "__main__":
    build()
