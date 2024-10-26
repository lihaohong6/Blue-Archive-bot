import json
import re
from pathlib import Path

from pywikibot import Site

from utils import scenario_character_name, dev_name_to_canonical_name, load_json, load_json_list

s = Site()

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
        string_options = [name_ko, name_ko.upper(), name_ko.lower(), name_ko.encode('utf-8')]
        for string in string_options:
            hashed = int(xxh32(string).intdigest())
            if hashed in scenario_character_name:
                break
        else:
            print(f"Cannot find scenario character name in table. Text: {name_ko}. Hash: {hashed}.")
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


def get_main_scenarios() -> list[dict]:
    with open ("json/ScenarioModeExcelTable.json", "r", encoding="utf-8") as f:
        result = json.load(f)
        result = result['DataList']
        return [row for row in result if row['ModeType'] == "Main"]


def get_story_title_and_summary(localization_id: int) -> tuple[str, str]:
    """
    This file is organized in a way that summary immediately follows the title, so we can take advantage
    of this by recording the index of each json entry.
    """

    def process(loaded: dict) -> tuple[list, dict]:
        loaded = loaded['DataList']
        localization_list: list[str] = []
        localization_dict: dict[int, int] = {}
        for index, row in enumerate(loaded):
            row_id = row['Key']
            row_text = row['En']
            localization_list.append(row_text)
            localization_dict[row_id] = index
        return localization_list, localization_dict

    lst, d = load_json("LocalizeExcelTable.json", process)

    index = d[localization_id]
    return lst[index], lst[index + 1]


def make_nav_span(event: dict) -> str:
    return f'<span id="relationship-{event["OrderInGroup"]}"></span><span id="relationship-favor-{event["FavorRank"]}"></span>'


def em_map(regex: re.Match[str]):
    # mapper = {
    #     '땀': 'sweat',
    #     '속상함': 'anxious',
    #     '반짝': 'twinkle',
    #     '…': 'ellipsis',
    # }
    d = regex.groupdict()
    result = d['m1'] if d["m1"] is not None else d['m2']
    return "{{emoticon|" + result + "}}"


def extract_em(string) -> list[str]:
    regex = re.compile(r"#\d;em;((?P<m1>…)|\[(?P<m2>[^\]]+)\])")
    result = []
    while True:
        match = re.search(regex, string)
        if match is None:
            break
        result.append(em_map(match))
        string = re.sub(regex, "", string)
    return result


def strip_st_line(line: str) -> str:
    line, _ = re.subn(r"\[log=[^\]]+\]", "", line)
    line = line.replace("[/log]", "")
    line, _ = re.subn(r"\[wa:\d+\]", "", line)
    return line


def make_categories(start: list[str] = None, character_list: set[str] = None, bgm_list: set[str] = None) -> str:
    if character_list is None:
        character_list = []
    if bgm_list is None:
        bgm_list = set()
    if start is None:
        start = set()
    bgm_string = "{{Story/BGMList | " + " | ".join(str(bgm) for bgm in sorted(bgm_list)) + " }}"
    char_string = "{{Story/CharList | " + " | ".join(sorted(character_list)) + " }}"
    return bgm_string + char_string + "\n".join(f"[[Category:{c}]]" for c in start)


def get_events(pattern: str) -> dict:
    def process(d: list[dict]) -> dict[int, list[dict]]:
        result: dict[int, list[dict]] = {}
        for loaded in d:
            loaded = loaded['DataList']
            for row in loaded:
                group_id = row['GroupId']
                if group_id not in result:
                    result[group_id] = []
                result[group_id].append(row)
        return result

    file_names = tuple(pattern.format(i) for i in range(1, 10))
    e = load_json_list(file_names, process)
    return e


def get_favor_event(query_group_id: int) -> list[dict]:
    e = get_events("ScenarioScriptFavor{0}ExcelTable.json")
    return e[query_group_id]


def get_main_event(query_group_id: int) -> list[dict] | None:
    e = get_events("ScenarioScriptExcelTable{0}.json")
    return e.get(query_group_id)
