<<<<<<< HEAD
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


scenario_character_name: dict[int, dict] = {}


def get_scenario_character_id(text_ko: str) -> tuple[str, str, str, str] | None:
    from xxhash import xxh32
    if len(scenario_character_name) == 0:
        path = Path("json/ScenarioCharacterNameExcelTable.json")
        loaded = json.load(open(path, "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            cid = row['CharacterName']
            scenario_character_name[cid] = row
    # search_text = re.search(r"^\d+;([^;a-zA-Z]+) ?([a-zA-Z]+)?;\d+;?", text_ko)
    search_text = re.search(r"^\d+;([^;]+);\d+;?", text_ko)
    if search_text is None:
        return None
    text_ko = search_text.group(1)
    # a -> A; b -> B
    if text_ko[-1].isascii():
        text_ko = text_ko[:-1] + text_ko[-1].upper()
    hashed = int(xxh32(text_ko).intdigest())
    if hashed not in scenario_character_name:
        raise NotImplementedError(f"Cannot find scenario character name in table. Text: {text_ko}. Hash: {hashed}.")
        return None
    row = scenario_character_name[hashed]
    name = row['NameEN']
    nickname = row['NicknameEN']
    spine = row['SpinePrefabName'].split("/")[-1]
    portrait = row['SmallPortrait'].split("/")[-1]
    return name, nickname, spine, portrait


if __name__ == "__main__":
    raise NotImplementedError("Do not run this script directly.")