import re
from dataclasses import dataclass
from enum import Enum

from pywikibot import Page

from story.story_utils import strip_st_line, get_story_title_and_summary, get_favor_event, make_categories, s
from utils import get_bgm_file_info, music_file_name_to_title, get_background_file_name


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


zmc_regex = re.compile(r"#zmc;(instant|move);-?\d+,-?\d+;\d+(;\d+)?")
st_regex = re.compile(r"#st;\[-?\d+,-?\d+];(serial|instant);\d+;")
option_group: int = 0


def process_info(text) -> str:
    text, _ = re.subn(r"^\[ns] *", "", text)
    text, _ = re.subn(r'\[b](.*)\[/b]', r'<span style="font-weight: bolder">\1</span>', text)
    # [7cd0ff]Make-Up Work Club[-]
    text, _ = re.subn(r'\[([0-9a-zA-Z]{6})]([^[]*)\[-]', r'<span style="color:#\1">\2</span>', text)
    # [7cd0ff]Make-Up Work Club<br/>
    text, _ = re.subn(r'\[([0-9a-zA-Z]{6})]([^[]*)(?=($|<br|\[\1]))', r'<span style="color:#\1">\2</span>', text)
    return text


def make_story(lines: list[dict], story_type: StoryType, character_name: str = None) -> StoryInfo:
    bgm_list: set[str] = set()
    character_list: set[str] = set()
    global option_group
    base_selection_group = -1
    from story.story_utils import get_scenario_character_id
    result = ["{{Story"]
    counter = 0
    hanging_bgm = False
    current_background = None
    onscreen_characters = set()
    live2d_mode = False
    story_title = None
    for line in lines:
        if "Battle" in line and line["Battle"] == True:
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}=A battle ensues")
            continue

        counter, hanging_bgm = process_bgm(bgm_list, counter, hanging_bgm, line, result)

        # parse background
        if line['BGName'] != 0:
            file_name = get_background_file_name(line['BGName'])
            if file_name is None:
                print(f"Background image not found for {line['BGName']}")
            else:
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
        text, _ = re.subn(r"\[wa:\d+]", "", text)
        sound: str = line['Sound']
        selection_group: int = line['SelectionGroup']
        if selection_group != 0:
            if base_selection_group == -1:
                base_selection_group = selection_group
                selection_group = 1
            else:
                selection_group = selection_group - base_selection_group + 1
        if lower.startswith("#title;"):
            story_title = text.split(";")[1].strip()
            result.append(f"|title={story_title}")
            continue
        elif lower.startswith("#place;"):
            counter += 1
            result.append(f"|{counter}=place\n|place{counter}={text}")
            continue
        elif lower.startswith("#continued"):
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}=To be continued")
            continue

        counter, is_st_line, lower = process_special_effects(counter, lower, result)

        lower = lower.strip()
        if is_st_line:
            match = re.search(r"\[log=([^]]+)]", text)
            if match is not None:
                lower = f"3;{match.group(1)};00"
        character_query_result, speaker = get_scenario_character_id(script)

        group_and_option_string = ""

        def make_group_and_option_string():
            nonlocal group_and_option_string
            if selection_group != 0:
                group_and_option_string = f"\n|group{counter + 1}={option_group}\n|option{counter + 1}={selection_group}"
            else:
                group_and_option_string = ""

        if sound is not None and sound != "":
            make_group_and_option_string()
            sound_name = re.sub(r"^ ?(SE|SFX)_", "", sound)
            sound_name = re.sub(r"(?<! )_?([A-Z])", r" \1", sound_name)
            sound_name = re.sub(r"(_| )\d{2}.?$", "", sound_name, flags=re.IGNORECASE)
            counter += 1
            result.append(f"|{counter}=sound\n|sound{counter}={sound}\n|name{counter}={sound_name.strip().lower()}{group_and_option_string}")

        if lower == "":
            # finished all special effects and no text left, so we are all good except for maybe sound
            pass
        elif lower.startswith("#nextepisode;"):
            counter += 1
            result.append(f"|{counter}=info\n|text{counter}={text.replace(';', ': ')}")
        elif lower.startswith("#na;("):
            make_group_and_option_string()
            counter += 1
            text = process_info(text)
            result.append(f"|{counter}=info\n|text{counter}={text}{group_and_option_string}")
            # TODO: deal with na issues
        elif lower.startswith("#na;") and (len(character_query_result) == 0 or character_query_result[0][0] is None):
            make_group_and_option_string()
            counter += 1
            text = process_info(text)
            result.append(f"|{counter}=info\n|text{counter}={text}{group_and_option_string}")
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

            character_query_result = [res for res in character_query_result if res[0] is not None and res[2] is not None and res[2].strip() != '']
            characters = set("".join(s for s in r if s is not None) for r in character_query_result)
            if characters != onscreen_characters and len(character_query_result) > 1:
                # FIXME: this feature is disabled because no good rule can be devised
                pass
                # onscreen_characters = characters
                # counter += 1
                # params = "|".join(
                #     f"char{index}={r[2]}|sequence{index}={r[4]}" for index, r in enumerate(character_query_result))
                # make_group_and_option_string()
                # result.append(f"|{counter}=screen\n"
                #               f"|content{counter}={{{{Story/Row|{params}}}}}" + group_and_option_string)
            make_group_and_option_string()
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
            make_group_and_option_string()
            counter += 1
            text = process_info(text)
            result.append(f"|{counter}=info\n|text{counter}={text}{group_and_option_string}")
        else:
            pass
            # print(f"Unrecognizable line: {script}. Processed: {lower}.")

    if hanging_bgm:
        counter += 1
        result.append(f"|{counter}=bgm-stop")

    result.append("}}")
    result = "\n\n".join(result)

    return StoryInfo(story_title, result, character_list, bgm_list)


def process_bgm(bgm_list, counter, hanging_bgm, line, result):
    bgm_id = line['BGMId']
    # sometimes bgm stop is issued at the start; need to avoid that
    if bgm_id != 0 and (bgm_id != 999 or counter > 0):
        counter += 1
        if bgm_id == 999:
            result.append(f"|{counter}=bgm-stop")
            hanging_bgm = False
        else:
            bgm_list.add(bgm_id)
            bgm = get_bgm_file_info(bgm_id)
            bgm_title = music_file_name_to_title(bgm.name)

            loop_string = f"\n|loop-start{counter}={bgm.loop_start:.2f}\n|loop-end{counter}={bgm.loop_end:.2f}" \
                if bgm.loop_start is not None or bgm.loop_end is not None \
                else ""

            result.append(f"|{counter}=bgm\n|bgm{counter}={bgm.name}\n|name{counter}={bgm_title}\n"
                          f"|volume{counter}={bgm.volume:.2f}{loop_string}")
            hanging_bgm = True
    return counter, hanging_bgm


def process_special_effects(counter: int, lower: str, result: list[str]):
    # process special commands
    is_st_line = True
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
    return counter, is_st_line, lower


def make_relationship_story_pages(event_list: list[dict], char_name: str):
    global option_group
    base_page = Page(s, f"{char_name}/Relationship Story")
    base_text = ["{{Story/RelationshipStoryTop}}"]
    for event in event_list:
        localization_id = event["LocalizeScenarioId"]
        event_name, event_summary = get_story_title_and_summary(localization_id)
        episode_result = ["{{Story/RelationshipStoryEpisodeTop|" +
                          f"title={event_name}|summary={event_summary}" +
                          "}}"]
        lines = get_favor_event(event['ScenarioSriptGroupId'])
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
