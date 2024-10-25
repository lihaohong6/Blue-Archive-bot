import re
import sys
from dataclasses import dataclass
from enum import Enum

from pywikibot import Page, Site

from utils import get_background_file_name, get_bgm_file_info, get_character_table, get_main_scenarios, \
    load_favor_schedule, music_file_name_to_title, load_json, load_json_list

sys.stdout.reconfigure(encoding='utf-8')
s = Site()


class StoryType(Enum):
    RELATIONSHIP = 0
    MAIN = 1
    SIDE = 2
    GROUP = 3


@dataclass
class StoryInfo:
    title: str | None
    text: str
    chars: set[str]
    music: set[str]


def get_localization(localization_id: int) -> tuple[str, str]:
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

    lst, d = load_json("LocalizeScenarioExcelTable.json", process)

    index = d[localization_id]
    return lst[index], lst[index + 1]


favor_events: dict[int, list[dict]] = {}


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


def get_main_event(query_group_id: int) -> list[dict]:
    e = get_events("ScenarioScriptMain{0}ExcelTable.json")
    return e[query_group_id]


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


def make_story(lines: list[dict], story_type: StoryType, character_name: str = None) -> StoryInfo:
    bgm_list: set[str] = set()
    character_list: set[str] = set()
    global option_group
    base_selection_group = -1
    from utils import get_scenario_character_id
    result = ["{{Story"]
    counter = 0
    hanging_bgm = False
    current_background = None
    onscreen_characters = set()
    live2d_mode = False
    story_title = None
    for line in lines:
        bgm_id = line['BGMId']
        # sometimes bgm stop is issued at the start; need to avoid that
        if bgm_id != 0 and (bgm_id != 999 or counter > 0):
            counter += 1
            if bgm_id == 999:
                result.append(f"|{counter}=bgm-stop")
                hanging_bgm = False
            else:
                file_name, bgm_info = get_bgm_file_info(bgm_id)
                bgm_loop_start, bgm_loop_end, bgm_volume = bgm_info[:3]
                bgm_name = music_file_name_to_title(file_name)

                loop_string = f"\n|loop-start{counter}={bgm_loop_start}\n|loop-end{counter}={bgm_loop_end}" \
                    if bgm_loop_start is not None or bgm_loop_end is not None \
                    else ""

                result.append(f"|{counter}=bgm\n|bgm{counter}={file_name}\n|name{counter}={bgm_name}\n"
                              f"|volume{counter}={bgm_volume}{loop_string}")
                hanging_bgm = True

                bgm_list.add(file_name)

        # parse background
        if line['BGName'] != 0:
            file_name = get_background_file_name(line['BGName'])
            # in some places (e.g. L2D) the same file name gets repeated multiple times
            if "SpineBG_Lobby" in file_name and story_type == StoryType.RELATIONSHIP:
                live2d_mode = True
                file_name = f"Memorial Lobby {character_name}"
            else:
                live2d_mode = False
            if current_background != file_name:
                counter += 1
                result.append(f"|{counter}=background\n|background{counter}={file_name}")
                current_background = file_name

        script: str = line['ScriptKr']
        lower: str = script.lower()
        text: str = line['TextEn']
        # don't deal with emoticon for now
        # text = text + "".join(extract_em(script))
        text = text.replace("#n", "<br/>")
        sound: str = line['Sound']
        selection_group: int = line['SelectionGroup']
        if selection_group != 0:
            if base_selection_group == -1:
                base_selection_group = selection_group
                selection_group = 1
            else:
                selection_group = selection_group - base_selection_group + 1
        if lower.startswith("#title;"):
            story_title = text.replace(';', ': ')
            result.append(f"|title={story_title}")
            lower = ""
            continue
        elif lower.startswith("#place;"):
            counter += 1
            result.append(f"|{counter}=place\n|place{counter}={text}")
            lower = ""
            continue
        elif lower.startswith("#continued"):
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}=To be continued")
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
            is_st_line = True
        while "#fontsize;" in lower:
            lower = re.sub(r"#fontsize;\d+", "", lower)
        if "#clearst" in lower:
            lower = lower.replace("#clearst", "")
        if "#bgshake" in lower:
            lower = lower.replace("#bgshake", "")
            counter += 1
            # no longer embedding sound into info
            # sound_string = f"\n|sound={counter}={sound}" if sound != "" else ""
            result.append(f"|{counter}=info\n|text{counter}=Screen shakes")
            # sound = ""

        lower = lower.strip()
        if is_st_line:
            match = re.search(r"\[log=([^\]]+)\]", text)
            if match is not None:
                lower = f"3;{match.group(1)};00"
        character_query_result, speaker = get_scenario_character_id(lower)

        if sound is not None and sound != "":
            counter += 1
            sound_name = re.sub(r"^ ?(SE|SFX)_", "", sound)
            sound_name = re.sub(r"(?<! )_?([A-Z])", r" \1", sound_name)
            sound_name = re.sub(r"(_| )\d{2}.?$", "", sound_name, flags=re.IGNORECASE)
            result.append(f"|{counter}=sound\n|sound{counter}={sound}\n|name{counter}={sound_name.strip().lower()}")

        if lower == "":
            # finished all special effects and no text left, so we are all good except for maybe sound
            pass
        elif lower.startswith("#nextepisode;"):
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}={text.replace(';', ': ')}")
        elif lower.startswith("#na;("):
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}={text}")
            # TODO: deal with na issues
        elif lower.startswith("#na;") and (len(character_query_result) == 0 or character_query_result[0][0] is None):
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}={text}")
        elif lower.startswith("[s") or lower.startswith("[ns"):
            options = re.split(r"\[n?s\d*]", text)
            options = options[1:]
            options = [o.strip() for o in options]
            if len(options) == 0:
                raise RuntimeError("Expected at least 1 option for " + text)
            elif len(options) == 1:
                counter += 1
                if selection_group != 0:
                    group_and_option_string = f"\n|group{counter}={option_group}\n|option{counter}={selection_group}"
                else:
                    group_and_option_string = ""
                result.append(f"|{counter}=sensei\n|text{counter}={options[0]}{group_and_option_string}")
            else:
                # sensei or reply
                option_group += 1
                base_selection_group = -1
                counter += 1
                result_line = f"|{counter}=reply\n"
                result_line += "\n".join(f"|option{counter}_{index}={o}" for index, o in enumerate(options, 1))
                result_line += f"\n|group{counter}={option_group}"
                result.append(result_line)
        elif (len(character_query_result) > 0 and speaker is not None) or (live2d_mode and text != ""):
            # student line
            if is_st_line:
                text = strip_st_line(text)
            characters = set("".join(s for s in r if s is not None) for r in character_query_result)
            if selection_group != 0:
                group_and_option_string = f"\n|group{counter + 1}={option_group}\n|option{counter + 1}={selection_group}"
            else:
                group_and_option_string = ""
            if characters != onscreen_characters and len(character_query_result) > 1:
                onscreen_characters = characters
                counter += 1
                params = "|".join(
                    f"char{index}={r[2]}|sequence{index}={r[4]}" for index, r in enumerate(character_query_result))
                result.append(f"|{counter}=screen\n"
                              f"|content{counter}={{{{Story/Row|{params}}}}}")
            if text.strip() != "":
                if speaker is None:
                    if live2d_mode:
                        name, nickname, spine, portrait, sequence = character_name, "", "", "", None
                    else:
                        print(f"Line with no speaker: {script}")
                        raise RuntimeError()
                else:
                    name, nickname, spine, portrait, sequence = speaker
                if name is not None and name != "":
                    character_list.add(name)
                counter += 1
                if portrait == "" and spine == "":
                    portrait_string = ""
                else:
                    portrait_string = f"\n|portrait{counter}={portrait}\n|spine{counter}={spine}\n|sequence{counter}={sequence}"
                result.append(f"|{counter}=student-text\n|name{counter}={name}\n"
                              f"|affiliation{counter}={nickname}\n"
                              f"|text{counter}={text}{group_and_option_string}{portrait_string}")
        elif text != "":
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}={text}")
        else:
            pass
            # print(f"Unrecognizable line: {script}. Processed: {lower}.")

    if hanging_bgm:
        counter += 1
        result.append(f"|{counter}=bgm-stop")

    result.append("}}")
    result = "\n\n".join(result)

    return StoryInfo(story_title, result, character_list, bgm_list)


def make_categories(start: list[str] = None, character_list: set[str] = None, bgm_list: set[str] = None) -> str:
    if character_list is None:
        character_list = []
    if bgm_list is None:
        bgm_list = set()
    if start is None:
        start = set()
    bgm_string = "{{Story/BGMList | " + " | ".join(re.search(r"\d+", bgm).group(0) for bgm in bgm_list) + " }}"
    char_string = "{{Story/CharList | " + " | ".join(character_list) + " }}"
    return bgm_string + char_string + "\n".join(f"[[Category:{c}]]" for c in start)


def make_relationship_story_pages(event_list: list[dict], char_name: str):
    base_page = Page(s, f"{char_name}/Relationship Story")
    base_text = ["{{Story/RelationshipStoryTop}}"]
    for event in event_list:
        localization_id = event["LocalizeScenarioId"]
        event_name, event_summary = get_localization(localization_id)
        episode_result = ["{{Story/RelationshipStoryEpisodeTop|" +
                          f"title={event_name}|summary={event_summary}" +
                          "}}"]
        lines = get_favor_event(event['ScenarioSriptGroupId'])
        global option_group
        option_group = 0
        story = make_story(lines, StoryType.RELATIONSHIP, character_name=char_name)
        episode_result.append(f"==Story==\n"
                              f"{story.text}")
        episode_result.append(make_categories(['Relationship story episodes'], story.chars, story.music))
        sub_page = Page(s, base_page.title() + f"/{event_name}")
        setattr(sub_page, "_bot_may_edit", True)
        sub_page.text = "\n".join(episode_result)
        sub_page.save(summary="batch create relation story episodes")
        base_text.append(f"=={event_name}==")
        base_text.append(f"[[/{event_name}|Full story]]")
        base_text.append(event_summary)
    base_text.append("[[Category:Relationship stories]]")
    base_page.text = "\n\n".join(base_text)
    base_page.save(summary="batch create relationship story pages")


def make_main_scenario_text(event: dict) -> str:
    ids = event["FrontScenarioGroupId"] + event["BackScenarioGroupId"]
    event_lines = []
    for event_id in ids:
        event_lines.extend(get_main_event(event_id))
    story = make_story(event_lines, StoryType.MAIN)
    result = ["{{Story/MainStoryTop}}",
              story.text,
              "{{Story/MainStoryBottom}}",
              make_categories(["Main story episodes"], story.chars, story.music)]
    return "\n".join(result)


def make_main_story():
    scenarios = get_main_scenarios()
    root_page = Page(s, f"Main_Story")
    all_episodes: dict[str, dict[str, dict[str, str]]] = {}
    for scenario in scenarios:
        text = make_main_scenario_text(scenario)
        volume = str(scenario['VolumeId'])
        chapter = str(scenario['ChapterId'])
        episode = str(scenario['EpisodeId'])
        if volume not in all_episodes:
            all_episodes[volume] = {}
        if chapter not in all_episodes[volume]:
            all_episodes[volume][chapter] = {}
        page = Page(s, root_page.title() + "/" + f"Volume {volume}/Chapter {chapter}/Episode {episode}")
        if page.text.strip() != text:
            page.text = text
            page.save(summary="batch create experimental main story pages")
        if int(episode) >= 5:
            break



def make_all_relationship_story_pages():
    favor_schedule = load_favor_schedule()
    character_table = get_character_table()
    for character_id, event_list in favor_schedule.items():
        if character_id not in character_table:
            print(f"Character id {character_id} has no corresponding name.")
            continue
        try:
            char_name = character_table[character_id]
            if char_name != "Shimiko":
                continue
            make_relationship_story_pages(event_list, char_name)
            print(character_table[character_id] + " done")
        except NotImplementedError as e:
            print(e)
            print(character_table[character_id] + " failed")


def main():
    make_main_story()


if __name__ == "__main__":
    main()
