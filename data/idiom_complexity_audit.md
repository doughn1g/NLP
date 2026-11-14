# Provisional complexity audit of the 75 draft idioms

This audit uses the source phrases and the draft glosses in `idioms_to_en_draft.jsonl`. It does **not** use model translations as proof of difficulty. Complexity here means how difficult it would be to recover the intended figurative sense from a literal reading of the isolated expression. It does not measure word count, sentence length, frequency, or actual model error rate.

Research distinguishes semantic transparency from decomposability and recommends speaker ratings rather than assuming that all idioms have the same difficulty ([Pagliai 2024](https://aclanthology.org/2024.cogalex-1.6/)). These labels are therefore **provisional analyst judgments**, not validated psycholinguistic ratings. Native or highly proficient bilingual reviewers should confirm the phrase, its gloss, and its difficulty in the source language. The dataset has no sentence context, which can change both interpretation and difficulty.

| Level | Working criterion | Count |
| --- | --- | ---: |
| High | Literal image leaves the intended meaning hard to infer, or an allusion or culturally specific convention is needed | 27 |
| Medium | Figurative or conventional meaning, but the image gives a useful clue | 30 |
| Low | Meaning is fairly transparent, or the item is mainly a figurative lexical word rather than a challenging phrase | 18 |

| Source | High | Medium | Low | Total |
| --- | ---: | ---: | ---: | ---: |
| Mandarin Chinese | 12 | 8 | 5 | 25 |
| Tamil | 3 | 13 | 9 | 25 |
| Tagalog | 12 | 9 | 4 | 25 |
| **All** | **27** | **30** | **18** | **75** |

## Mandarin Chinese

| ID | Idiom | Level | Reason |
| --- | --- | --- | --- |
| 01 | 画蛇添足 | High | Snake-and-feet story does not state the cost of needless additions. |
| 02 | 对牛弹琴 | Medium | Cow-as-audience image hints at a message wasted on its listener. |
| 03 | 亡羊补牢 | High | Repairing a pen after losing sheep needs the implied lesson. |
| 04 | 杯弓蛇影 | High | Cup, bow, and snake image is hard to interpret without its allusion. |
| 05 | 井底之蛙 | Medium | Restricted view from a well suggests narrow perspective. |
| 06 | 守株待兔 | High | Waiting by a tree for a rabbit needs the familiar story. |
| 07 | 雪中送炭 | Medium | Supplying heat during snow suggests timely help. |
| 08 | 掩耳盗铃 | High | Covering ears while stealing a bell requires an inference about self-deception. |
| 09 | 自相矛盾 | Low | Contradicting oneself is largely recoverable from the wording. |
| 10 | 半途而废 | Low | Giving up halfway is comparatively transparent. |
| 11 | 一举两得 | Low | Two gains from one action is explicit. |
| 12 | 一箭双雕 | Medium | One-arrow image hints at two outcomes and has an English analogue. |
| 13 | 纸上谈兵 | Medium | Paper strategy hints at theory without practice. |
| 14 | 盲人摸象 | High | Touching an elephant needs the story about partial evidence. |
| 15 | 刻舟求剑 | High | Marking a boat to find a sword needs the story about changed circumstances. |
| 16 | 得不偿失 | Low | The loss-gain imbalance is explicit. |
| 17 | 落井下石 | Medium | Throwing stones into a well suggests worsening someone's trouble. |
| 18 | 破釜沉舟 | High | Breaking pots and sinking boats needs historical or strategic context. |
| 19 | 三心二意 | Medium | Multiple hearts or intentions hint at indecision. |
| 20 | 狐假虎威 | High | Fox borrowing a tiger's force needs the animal tale. |
| 21 | 滥竽充数 | High | The instrument-and-numbers allusion is opaque without its story. |
| 22 | 画龙点睛 | High | Painting a dragon's eyes needs the finishing-touch convention. |
| 23 | 开门见山 | Medium | Open-door/mountain image suggests directness but remains figurative. |
| 24 | 眉开眼笑 | Low | Smiling face is near literal. |
| 25 | 胸有成竹 | High | Bamboo already in the chest needs an artistic allusion. |

The Mandarin items are seeded from local PETCI reference data. Its English glosses are not ground truth; bilingual review is required.

## Tamil

| ID | Idiom | Level | Reason |
| --- | --- | --- | --- |
| 01 | தலைக்கு மேல் வெள்ளம் | Medium | Flood over one's head suggests being overwhelmed. |
| 02 | அள்ளிக் குவித்தல் | Low | Piling up largely signals accumulating; check whether it is idiomatic in isolation. |
| 03 | அண்டப்புழுகன் | Low | Single figurative word for a liar; weak phrase-level test. |
| 04 | அள்ளியிறைத்தல் | Medium | Scattering or pouring out hints at excessive spending. |
| 05 | அரக்கப் பறக்க | Medium | Set phrase for haste; its exact figurative force needs review. |
| 06 | அழுங்குப்பிடி | Low | Lexicalized stubbornness; weak phrase-level test. |
| 07 | அகலக் கால் வைத்தல் | Medium | Wide step hints at overreaching. |
| 08 | ஆகாயக் கோட்டை | Medium | Castle in the sky suggests an unrealistic plan. |
| 09 | ஆறப்போடல் | Medium | Putting aside to cool gives a clue to delay. |
| 10 | ஆசை வார்த்தை | Low | Enticing words are fairly transparent; check deceptive sense. |
| 11 | ஆழம் பார்த்தல் | Medium | Testing depth suggests testing a person. |
| 12 | இலை மறை காய் | Medium | Fruit behind leaves suggests concealment. |
| 13 | இளிச்சவாயன் | Low | Single figurative word for a gullible person; weak phrase-level test. |
| 14 | இட்டுக்கட்டுதல் | Low | Lexicalized verb for inventing a story; weak phrase-level test. |
| 15 | இலவு காத்த கிளி | High | Parrot and tree image needs a cultural story to yield futile waiting. |
| 16 | இரண்டு தோணியில் கால் வைத்தல் | Medium | Feet in two boats suggest incompatible commitments. |
| 17 | ஈரல் கருகுதல் | Medium | Burning liver suggests distress but is culturally specific. |
| 18 | ஈயோட்டுதல் | Medium | Swatting flies suggests idleness. |
| 19 | உள்ளங்கையில் நெல்லிக்கனி | High | Fruit in a palm does not clearly convey obviousness without convention. |
| 20 | உப்பில்லாப் பேச்சு | Medium | Saltless speech suggests empty talk. |
| 21 | உச்சி குளிர்தல் | Medium | Cooling crown has a nonliteral positive-emotion sense. |
| 22 | உலை வைத்தல் | High | Furnace image does not clearly convey causing ruin; gloss needs priority review. |
| 23 | அரை மனிதன் | Low | Half-person insult is fairly transparent; check usage. |
| 24 | அகடவிகடம் | Low | Single lexical item for a trick; weak phrase-level test. |
| 25 | உதவாக்கரை | Low | Single lexical item for a useless person; weak phrase-level test. |

The [Tamil source list](https://thamizhkalanchiyam360.blogspot.com/2018/09/blog-post_18.html) explicitly includes both words and phrases under its idiom heading. That makes the nine low items possible idiomatic expressions, but several are weak choices for a **complex multiword idiom** benchmark. Their glosses and natural usage still need bilingual review.

## Tagalog

| ID | Idiom | Level | Reason |
| --- | --- | --- | --- |
| 01 | bukas ang palad | Medium | Open-palm image hints at generosity. |
| 02 | balitang kutsero | High | Coachman news does not transparently mean an unreliable rumor. |
| 03 | naglalaro ng apoy | High | Playing with fire suggests risk but not the source handout's specific infidelity sense; context is needed. |
| 04 | naghalo ang balat sa tinalupan | High | Skin and peel image is opaque for a quarrel. |
| 05 | parang natuka ng ahas | High | Snake-bite image does not specify being stunned into silence. |
| 06 | bulang-gugo | High | Culturally specific image is opaque for a person generous with money. |
| 07 | itaga mo sa bato | Medium | Carving in stone hints at certainty or remembering a promise. |
| 08 | maglubid ng buhangin | High | Making rope from sand does not transparently mean lying. |
| 09 | makati ang dila | Medium | Itchy tongue hints at talkativeness or gossip. |
| 10 | umaalon ang dibdib | Medium | Waving chest hints at nervousness. |
| 11 | pag-iisang dibdib | High | Uniting chests needs a convention to mean marriage. |
| 12 | anghel ng tahanan | Medium | Angel-of-the-home image suggests a child but is not exact. |
| 13 | sariling pugad | Low | Own nest maps fairly directly to own home. |
| 14 | utang na loob | High | Inner debt has a culturally specific gratitude and obligation sense. |
| 15 | parang aso't pusa | Low | Cats-and-dogs quarrel is readily inferable and has an English analogue. |
| 16 | nag-alsa balutan | Medium | Raising or packing a bundle hints at departure. |
| 17 | pinagbubuhatan ng kamay | Low | Raised hand makes violence relatively transparent. |
| 18 | nagbabagong-loob | Low | Changing one's inner self suggests reform. |
| 19 | di makabasag-pinggan | High | Unable to break a plate does not directly mean meekness. |
| 20 | anak-pawis | Medium | Child of sweat suggests a laborer. |
| 21 | makati ang paa | Medium | Itchy feet suggests restlessness or going out. |
| 22 | mabigat ang dugo | High | Heavy blood does not directly convey dislike. |
| 23 | namuti ang mata | High | Eyes turning white needs a convention to mean a long wait. |
| 24 | ningas-cogon | High | Cogon grass fire is culturally specific for brief enthusiasm. |
| 25 | bukambibig | Medium | Mouth-related compound hints at repeated mention; check lexical form. |

The [Tagalog teaching handout](https://dunonglingkod.mapua.edu.ph/ALEAP/Assets/Mga%20Sawikain%20at%20Salawikain.pdf) explicitly teaches most of these as idioms. It gives `naglalaro ng apoy` the narrower sense of infidelity; the draft gloss in `idioms_to_en_draft.jsonl` currently includes the broader "dangerous affair" reading. A bilingual reviewer should settle that label before grading translations.

## Decision for the benchmark

The set contains **75 draft idiomatic items, but not 75 high-complexity idioms** under this working definition. It has 27 high, 30 medium, and 18 low items, with the largest imbalance in Tamil. A fair difficulty-focused comparison should have bilingual reviewers validate these labels and either replace lower-complexity Tamil items or report results by complexity tier. Do not infer that model errors alone establish an idiom's complexity.
