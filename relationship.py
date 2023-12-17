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
        lower = lower.replace("\n", "")
        while re.search(r"#wait;\d+", lower) is not None:
            lower = re.sub(r"#wait;\d+", "", lower)
        if "#all;hide" in lower:
            lower = lower.replace("#all;hide", "")
        while "#st;" in lower:
            lower = re.sub(r"#st;\[-?\d+,-?\d+];(serial|instant);\d+;", "", lower)
            pass
        if "#clearst" in lower:
            lower = lower.replace("#clearst", "")
        if "#bgshake" in lower:
            lower = lower.replace("#bgshake", "")

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
            print("Unrecognizable line: " + script)

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
        print(make_favor_page(character_table[character_id], event_list))
        break


if __name__ == "__main__":
    main()
