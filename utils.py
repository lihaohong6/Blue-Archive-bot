import pickle
import re
from pathlib import Path

import pywikibot as pwb
from pywikibot.pagegenerators import GeneratorFactory

import json


def get_character_table() -> dict[int, str]:
    path = Path("cache/char_id.pickle")
    if path.exists():
        result = pickle.load(open(path, "rb"))
    else:
        path.parent.mkdir(exist_ok=True)
        s = pwb.Site()
        gen = GeneratorFactory(s)
        gen.handle_args(["-cat:Characters"])
        gen = gen.getCombinedGenerator(preload=True)
        result = {}
        for p in gen:
            char_id = int(re.search(r"Id *= *([0-9]+)", p.text).group(1))
            char_name = re.search(r"\| Name = ([^\n]+)", p.text).group(1)
            result[char_id] = char_name
        pickle.dump(result, open(path, "wb"))
    return result


def load_momotalk() -> dict[int, list[dict]]:
    result = {}
    for i in range(0, 10):
        file_name = Path(f"json/AcademyMessanger{i}ExcelTable.json")
        if not file_name.exists():
            continue
        momotalk = json.load(open(file_name, "r", encoding="utf-8"))
        if 'DataList' in momotalk:
            momotalk = momotalk['DataList']
        for talk in momotalk:
            cid = talk['CharacterId']
            if cid not in result:
                result[cid] = []
            result[cid].append(talk)
    return result


cached_favor_schedule = {}


def load_favor_schedule() -> dict[int, list[dict]]:
    if len(cached_favor_schedule) == 0:
        loaded = json.load(open("json/AcademyFavorScheduleExcelTable.json", "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            cid = row['CharacterId']
            if cid not in cached_favor_schedule:
                cached_favor_schedule[cid] = []
            cached_favor_schedule[cid].append(row)
    return cached_favor_schedule
