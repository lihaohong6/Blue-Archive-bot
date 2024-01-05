import re

import json
from pathlib import Path
import sys
from utils import get_character_table, load_favor_schedule

sys.stdout.reconfigure(encoding='utf-8')

localization_list: list[str] = []
localization_dict: dict[int, int] = {}


def get_localization(localization_id: int) -> tuple[str, str]:
    if len(localization_list) == 0:
        loaded = json.load(open("json/LocalizeScenarioExcelTable.json", "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for index, row in enumerate(loaded):
            row_id = row['Key']
            row_text = row['En']
            localization_list.append(row_text)
            localization_dict[row_id] = index
    index = localization_dict[localization_id]
    return localization_list[index], localization_list[index + 1]


favor_events: dict[int, list[dict]] = {}


def get_favor_event(query_group_id: int) -> list[dict]:
    if len(favor_events) == 0:
        for i in range(1, 10):
            path = Path(f"json/ScenarioScriptFavor{i}ExcelTable.json")
            if not path.exists():
                continue
            loaded = json.load(open(path, "r", encoding="utf-8"))
            loaded = loaded['DataList']
            for row in loaded:
                group_id = row['GroupId']
                if group_id not in favor_events:
                    favor_events[group_id] = []
                favor_events[group_id].append(row)
    return favor_events[query_group_id]


def make_nav_span(event: dict) -> str:
    return f'<span id="relationship-{event["OrderInGroup"]}"></span><span id="relationship-favor-{event["FavorRank"]}"></span>'


zmc_regex = re.compile(r"#zmc;(instant|move);-?\d+,-?\d+;\d+(;\d+)?")
st_regex = re.compile(r"#st;\[-?\d+,-?\d+];(serial|instant);\d+;")


def make_favor_event(char_name: str, event: dict) -> str:
    from utils import get_scenario_character_id
    localization_id = event["LocalizeScenarioId"]
    event_name, event_summary = get_localization(localization_id)
    lines = get_favor_event(event['ScenarioSriptGroupId'])
    result = []
    for line in lines:
        script: str = line['ScriptKr']
        lower: str = script.lower()
        text: str = line['TextEn']
        if lower.startswith("#title;"):
            lower = ""
        elif lower.startswith("#place;"):
            lower = ""

        # process special commands
        while re.search(r"#wait;\d+", lower) is not None:
            lower = re.sub(r"#wait;\d+", "", lower)
        if "#all;hide" in lower:
            lower = lower.replace("#all;hide", "")
        while re.search(zmc_regex, lower) is not None:
            lower, _ = re.subn(zmc_regex, "", lower)
        while re.search(r"#\d;", lower) is not None:
            lower, _ = re.subn(r"#\d;(hide|closeup|stiff|shake|dr|jump|d|em;)?", "", lower)
        while re.search(st_regex, lower) is not None:
            # TODO: resolve the speaker of st lines
            lower, _ = re.subn(st_regex, "", lower)
            lower = ""
            pass
        while "#fontsize;" in lower:
            lower = re.sub(r"#fontsize;\d+", "", lower)
        if "#clearst" in lower:
            lower = lower.replace("#clearst", "")
        if "#bgshake" in lower:
            lower = lower.replace("#bgshake", "")

        lower = lower.strip()
        character_query_result = get_scenario_character_id(lower)
        if lower == "":
            # finished all special effects and no text left, so we are all good
            pass
        elif lower.startswith("#na;"):
            # 3rd person description
            pass
        elif lower.startswith("[s") or lower.startswith("[ns"):
            # Sensei choice
            pass
        elif character_query_result is not None:
            # student line
            name, nickname, spine, portrait = character_query_result
        else:
            print("Unrecognizable line: " + script + "\nProcessed: " + lower)

        def parse_bgm():
            bgm_id = line['BGMId']
            if bgm_id != 0:
                pass

    return f"={event_name}=\n{make_nav_span(event)}{event_summary}"


def make_favor_page(char_name: str, event_list: list[dict]) -> str:
    result = []
    for event in event_list:
        result.append(make_favor_event(char_name, event))
    return "\n\n".join(result)


def main():
    favor_schedule = load_favor_schedule()
    character_table = get_character_table()
    for character_id, event_list in favor_schedule.items():
        if character_id not in character_table:
            print(f"Character id {character_id} has no corresponding name.")
            continue
        try:
            make_favor_page(character_table[character_id], event_list)
            print(character_table[character_id] + " done")
        except NotImplementedError as e:
            print(e)
            print(character_table[character_id] + " failed")


if __name__ == "__main__":
    main()
