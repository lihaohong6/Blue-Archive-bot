import json
from pathlib import Path
import re
import pywikibot as pwb
from pywikibot.pagegenerators import GeneratorFactory
import sys
from momotalk import get_character_table
sys.stdout.reconfigure(encoding='utf-8')

localization_list: list[str] = []
localization_dict: dict[int, int] = {}
def get_localization(id: int) -> tuple[str, str]:
    if len(localization_list) == 0:
        loaded = json.load(open("json/LocalizeScenarioExcelTable.json", "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for index, row in enumerate(loaded):
            row_id = row['Key']
            row_text = row['En']
            localization_list.append(row_text)
            localization_dict[row_id] = index
    index = localization_dict[id]
    return localization_list[index], localization_list[index + 1]


favor_events: dict[int, list[dict]] = {}
def get_favor_event(query_group_id: int) -> list[dict]:
    if len(favor_events) == 0:
        for i in range(1, 10):
            path = Path(f"json/ScenarioScriptFavor{i}ExcelTable.json")
            loaded = json.load(open(path, "r", encoding="utf-8"))
            loaded = loaded['DataList']
            for row in loaded:
                group_id = row['GroupId']
                if group_id not in favor_events:
                    favor_events[group_id] = []
                favor_events[group_id].append(row)
    return favor_events[query_group_id]


scenario_character_name: dict[str, dict] = {}
def get_character_id(text_ko: str) -> dict[str, tuple[str, str, str]] | None:
    if len(scenario_character_name) is None:
        path = Path("json/ScenarioCharacterNameExcelTable.json")
        loaded = json.load(open(path, "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            cid = row['CharacterName']
            scenario_character_name[cid] = row
    
    

def load_favor_schedule() -> dict[int, list[dict]]:
    loaded = json.load(open("json/AcademyFavorScheduleExcelTable.json", "r", encoding="utf-8"))
    loaded = loaded['DataList']
    result = {}
    for row in loaded:
        cid = row['CharacterId']
        if cid not in result:
            result[cid] = []
        result[cid].append(row)
    return result


def make_nav_span(event: dict) -> str:
    return f'<span id="relationship-{event["OrderInGroup"]}"></span><span id="relationship-favor-{event["FavorRank"]}"></span>'


def make_favor_event(char_name: str, event: dict) -> str:
    localization_id = event["LocalizeScenarioId"]
    event_name, event_summary = get_localization(localization_id)
    lines = get_favor_event(event['ScenarioSriptGroupId'])
    for line in lines:
        pass
    return f"={event_name}=\n{make_nav_span()}{event_summary}"


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