import re

import json
from pathlib import Path
import sys
from utils import get_background_file_name, get_bgm_file_name, get_character_table, load_favor_schedule

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


option_group: int = 0


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


def make_favor_event(char_name: str, event: dict) -> str:
    global option_group
    from utils import get_scenario_character_id
    localization_id = event["LocalizeScenarioId"]
    event_name, event_summary = get_localization(localization_id)
    lines = get_favor_event(event['ScenarioSriptGroupId'])
    result = ["{{Story"]
    counter = 0
    hanging_bgm = False
    for line in lines:
        bgm_id = line['BGMId']
        # sometimes bgm stop is issued at the start; need to avoid that
        if bgm_id != 0 and (bgm_id != 999 or counter > 0):
            counter += 1
            if bgm_id == 999:
                result.append(f"|{counter}=bgm-stop")
                hanging_bgm = False
            else:
                result.append(f"|{counter}=bgm\n|bgm{counter}={get_bgm_file_name(bgm_id)[0]}")
                hanging_bgm = True
                
        if line['BGName'] != 0:
            file_name = get_background_file_name(line['BGName'])
            counter += 1
            result.append(f"|{counter}=background\n|background{counter}={file_name}")
        
        script: str = line['ScriptKr']
        lower: str = script.lower()
        text: str = line['TextEn']
        text = text + "".join(extract_em(script))
        sound: str = line['Sound']
        selection_group: int = line['SelectionGroup']
        if lower.startswith("#title;"):
            result.append(f"|title={text}")
            lower = ""
            continue
        elif lower.startswith("#place;"):
            result.append(f"|place={text}")
            lower = ""
            continue
        
        is_st_line = False
        # process special commands
        while re.search(r"#wait;\d+", lower) is not None:
            lower = re.sub(r"#wait;\d+", "", lower)
        if "#all;hide" in lower:
            lower = lower.replace("#all;hide", "")
        while re.search(zmc_regex, lower) is not None:
            lower, _ = re.subn(zmc_regex, "", lower)
        while re.search(r"#\d;", lower) is not None:
            lower, _ = re.subn(r"#\d;(hide|closeup|stiff|shake|dr|jump|d|em)?", "", lower)
        if re.search(st_regex, lower) is not None or lower.startswith("#st;"):
            lower = ""
            is_st_line = True
        while "#fontsize;" in lower:
            lower = re.sub(r"#fontsize;\d+", "", lower)
        if "#clearst" in lower:
            lower = lower.replace("#clearst", "")
        if "#bgshake" in lower:
            lower = lower.replace("#bgshake", "")
            counter += 1
            sound_string = f"\n|sound={counter}={sound}" if sound != "" else ""
            result.append(f"|{counter}=info\n|text{counter}=Screen shakes{sound_string}")
            sound = ""
            
        group_and_option_string = ""
        if selection_group != 0:
            group_and_option_string = f"\n|group={option_group}\n|option{counter}={selection_group}"

        lower = lower.strip()
        if is_st_line:
            match = re.search(r"\[log=([^\]]+)\]", text)
            if match is not None:
                log = match.group(1)
                lower = f"3;{log};00"
        character_query_result = get_scenario_character_id(lower)
        
        if sound is not None and sound != "":
            counter += 1
            sound_name = re.sub(r"^ ?(SE|SFX)_", "", sound)
            sound_name = re.sub(r"(?<! )_?([A-Z])", r" \1", sound_name)
            sound_name = re.sub(r"(_| )\d{2}.?$", "", sound_name, flags=re.IGNORECASE)
            result.append(f"|{counter}=sound\n|sound{counter}={sound}\n|name{counter}={sound_name.strip().lower()}")
        if lower == "":
            # finished all special effects and no text left, so we are all good except for maybe sound
            pass
        elif lower.startswith("#na;("):
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}={text}")
        elif lower.startswith("#na;"):
            counter += 1
            result.append(f"|{counter}=no-speaker\n|text{counter}={text}")
        elif lower.startswith("[s") or lower.startswith("[ns"):
            options = re.split(r"\[n?s\d*\]", text)
            options = options[1:]
            options = [o.strip() for o in options]
            if len(options) == 0:
                raise RuntimeError("Expected at least 1 option for " + text)
            elif len(options) == 1:
                counter += 1
                result.append(f"|{counter}=sensei\n|text{counter}={options[0]}{group_and_option_string}")
            else:
                # sensei or reply
                option_group += 1
                counter += 1
                result_line = f"|{counter}=reply\n"
                result_line += "\n".join(f"|option{counter}_{index}={o}" for index, o in enumerate(options, 1))
                result_line += f"\n|group{counter}={option_group}"
                result.append(result_line)
        elif character_query_result is not None:
            # student line
            if is_st_line:
                text = strip_st_line(text)
            if text.strip() != "":
                name, nickname, spine, portrait = character_query_result
                counter += 1
                result.append(f"|{counter}=student-text\n|name{counter}={name}\n"
                            f"|affiliation{counter}={nickname}\n|portrait{counter}={portrait}\n"
                            f"|spine{counter}={spine}\n|text{counter}={text}{group_and_option_string}")
        else:
            print("Unrecognizable line: " + script + "\nProcessed: " + lower)
            
    if hanging_bgm:
        counter += 1
        result.append(f"|{counter}=bgm-stop")

    result.append("}}")
    result = "\n\n".join(result)
    
    return f"={event_name}=\n{make_nav_span(event)}{event_summary}\n{result}"


def make_favor_page(char_name: str, event_list: list[dict]) -> str:
    result = []
    global option_group
    option_group = 0
    for event in event_list:
        result.append(make_favor_event(char_name, event))
    return "\n\n".join(result)


def main():
    favor_schedule = load_favor_schedule()
    character_table = get_character_table()
    with open("result.txt", "w", encoding="utf-8") as f:
        for character_id, event_list in favor_schedule.items():
            if character_id not in character_table:
                print(f"Character id {character_id} has no corresponding name.")
                continue
            try:
                char_name = character_table[character_id]
                if char_name != "Miyu (Swimsuit)":
                    continue
                s = make_favor_page(char_name, event_list)
                f.write(char_name + "!!!\n\n")
                f.write(s)
                f.write("\n\n")
                print(character_table[character_id] + " done")
            except NotImplementedError as e:
                print(e)
                print(character_table[character_id] + " failed")


if __name__ == "__main__":
    main()
