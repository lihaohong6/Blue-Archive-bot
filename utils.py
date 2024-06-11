import pickle
import re
from pathlib import Path

import pywikibot as pwb
from pywikibot.pagegenerators import GeneratorFactory

import json


def normalize_char_name(original: str) -> str:
    return re.sub(r" ?\(.+\)", "", original)


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


dev_name_map: dict[str, str] = {}


def dev_name_to_canonical_name(dev_name: str) -> str:
    if len(dev_name_map) == 0:
        def read_dev_name_map(fname: str):
            name_map = json.load(open(fname, "r", encoding="utf-8"))
            for k, v in name_map.items():
                wiki_name = v['firstname']
                if v['variant'] is not None:
                    wiki_name += f" ({v['variant']})"
                dev_name_map[k] = wiki_name
        read_dev_name_map('json/devname_map.json')
        read_dev_name_map('json/devname_map_aux.json')
    if dev_name == "Null":
        return ""
    if dev_name in dev_name_map:
        return dev_name_map[dev_name]
    if dev_name.capitalize() in dev_name_map:
        return dev_name_map[dev_name.capitalize()]
    if dev_name.lower() in dev_name_map:
        return dev_name_map[dev_name.lower()]
    print("Cannot find canonical name of " + dev_name)
    return ""


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


def get_scenario_character_id(text_ko_original: str) -> tuple[list[tuple[str, str, str, str]], int]:
    from xxhash import xxh32
    result = []
    speaker = None
    if len(scenario_character_name) == 0:
        path = Path("json/ScenarioCharacterNameExcelTable.json")
        loaded = json.load(open(path, "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            cid = row['CharacterName']
            scenario_character_name[cid] = row
    # search_text = re.search(r"^\d+;([^;a-zA-Z]+) ?([a-zA-Z]+)?;\d+;?", text_ko)
    for original in text_ko_original.split("\n"):
        search_text = re.search(r"^\d+;([^;]+);(\d+);?", original)
        if search_text is not None:
            name_ko = search_text.group(1)
            expression_number = search_text.group(2)
            na = False
        else:
            search_text = re.search(r"#na;([^\n#;]+)(;.+)?", original)
            if search_text is not None:
                na = True
                if search_text.group(2) is not None:
                    name_ko = search_text.group(1)
                else:
                    result.append([None, None, None, None, None])
                    continue
                expression_number = None
            else:
                continue
                
        # a -> A; b -> B
        name_ko = name_ko.upper()
        hashed = int(xxh32(name_ko).intdigest())
        if hashed not in scenario_character_name:
            raise NotImplementedError(f"Cannot find scenario character name in table. Text: {name_ko}. Hash: {hashed}.")
            continue
        row = scenario_character_name[hashed]
        name = row['NameEN']
        nickname = row['NicknameEN']
        spine = row['SpinePrefabName'].split("/")[-1]
        if spine is not None and spine.strip() != "":
            spine = spine.replace("CharacterSpine_", "")
            spine = dev_name_to_canonical_name(spine)
        portrait = row['SmallPortrait'].split("/")[-1]
        if portrait is not None and portrait != "":
            if "Student_Portrait_" in portrait:
                portrait = portrait.replace("Student_Portrait_", "")
                portrait = dev_name_to_canonical_name(portrait)
            elif "NPC_Portrait_" in portrait:
                portrait = portrait.replace("NPC_Portrait_", "")
                portrait = dev_name_to_canonical_name(portrait)
        if na:
            spine, portrait = '', ''
        
        # check if there is text after the last semicolon; if so, this is the speaker
        obj = (name, nickname, spine, portrait, expression_number)
        if re.search(r"^\d+;([^;]+);(\d+);.", original) is not None or na:
            speaker = obj
        result.append(obj)
    return result, speaker


background_file_name: dict[int, str] = {}


def get_background_file_name(background_id: int) -> str:
    if len(background_file_name) == 0:
        loaded = json.load(open("json/ScenarioBGNameExcelTable.json", "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            bg_id = row['Name']
            bg_name: str = row['BGFileName']
            background_file_name[bg_id] = bg_name.split("/")[-1]
    return background_file_name[background_id]


bgm_file_info: dict[int, tuple[str, list[float]]] = {}


def get_bgm_file_info(query_id: int) -> tuple[str, list[float]]:
    def list_or_none(l: list) -> str | None:
        if len(l) == 0:
            return None
        return l[0]
    
    if len(bgm_file_info) == 0:
        loaded = json.load(open("json/BGMExcelTable.json", "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            bgm_id = row['Id']
            bgm_name: str = list_or_none(row['Path'])
            loop_start = list_or_none(row['LoopStartTime'])
            loop_end = list_or_none(row['LoopEndTime'])
            volume = list_or_none(row['Volume'])
            transition_time = list_or_none(row['LoopTranstionTime'])
            offset_time = list_or_none(row['LoopOffsetTime'])
            bgm_file_info[bgm_id] = (bgm_name.split("/")[-1], [loop_start, loop_end, volume, transition_time, offset_time])
    if query_id in bgm_file_info:
        return bgm_file_info[query_id]
    raise RuntimeError(f"Bgm with id {query_id} not found.")


def get_main_scenarios() -> list[dict]:
    with open ("json/ScenarioModeExcelTable.json", "r", encoding="utf-8") as f:
        result = json.load(f)
        result = result['DataList']
        return [row for row in result if row['ModeType'] == "Main"]


if __name__ == "__main__":
    raise NotImplementedError("Do not run this script directly.")