import re
from dataclasses import dataclass

from story.log_utils import logger
from story.story_utils import strip_st_line, get_story_event, make_categories, get_story_title_and_summary, StoryType, \
    StoryInfo
from utils import get_bgm_file_info, music_file_name_to_title, get_background_file_name, signature_escape


def story_type_to_cat(story_type: StoryType):
    return {
        StoryType.RELATIONSHIP: "Relationship story episodes",
        StoryType.MAIN: "Main story episodes",
        StoryType.SIDE: "Side story episodes",
        StoryType.GROUP: "Group story episodes",
        StoryType.EVENT: "Event story episodes",
    }.get(story_type)


zmc_regex = re.compile(r"#zmc;(instant|move);-?\d+,-?\d+;\d+(;\d+)?")
st_regex = re.compile(r"#st;\[-?\d+,-?\d+];(serial|instant);\d+;")


def process_info(text) -> str:
    text, _ = re.subn(r"^\[ns] *", "", text)
    text, _ = re.subn(r'\[b](.*)\[/b]', r'<span style="font-weight: bolder">\1</span>', text)
    # [7cd0ff]Make-Up Work Club[-]
    text, _ = re.subn(r'\[([0-9a-zA-Z]{6})]([^[]*)\[-]', r'<span style="color:#\1">\2</span>', text)
    # [7cd0ff]Make-Up Work Club<br/>
    text, _ = re.subn(r'\[([0-9a-zA-Z]{6})]([^[]*)(?=($|<br|\[\1]))', r'<span style="color:#\1">\2</span>', text)
    if "></span>" in text:
        # For empty spans, replace with ZWSP
        text = text.replace("\"></span>", "\">&#8203;</span>")
    return text


def event_list_to_template(event_list: list[dict[str, str]]) -> str:
    result = ["{{Story"]
    for index, event in enumerate(event_list, 1):
        for k, v in event.items():
            if "%d" in k:
                key = k.replace("%d", str(index))
            else:
                key = f"{k}{index}"
            result.append(f"|{key}={v}")
        result.append("")
    result.append("}}")
    return "\n".join(result)


@dataclass
class StoryState:
    hanging_bgm: bool = False
    current_background: str = None
    current_popup: str = None
    live2d_mode: bool = False


@dataclass
class ParsedStory:
    intermediate_text: list[dict[str, str]]
    chars: set[str]
    music: set[str]


def parse_story(lines: list[dict], story_type: StoryType, character_name: str = None) -> ParsedStory:
    bgm_list: set[str] = set()
    character_list: set[str] = set()
    from story.story_utils import get_scenario_character_id
    events: list[dict[str, str]] = []
    option_group = 0
    base_selection_group = -1
    onscreen_characters = set()
    story_title = None
    story_state = StoryState()

    # noinspection PyDefaultArgument
    def add_info(info_text: str, extras: dict[str, str] = {}):
        events.append({"": "info", "text": info_text} | extras)

    for line in lines:
        if "Battle" in line and line["Battle"] == True:
            add_info("A battle ensues")
            continue

        process_bgm(bgm_list, story_state, line, events)

        # parse background
        process_background(character_name, events, line, story_state, story_type)

        process_popup(events, line, story_state)

        script: str = line['ScriptKr']
        lower: str = script.lower()
        text: str = line['TextEn']
        # FIXME: deal with emoticon?
        # text = text + "".join(extract_em(script))
        text = text.replace("#n", "<br/>")
        text, _ = re.subn(r"\[wa:\d+]", "", text)
        text = signature_escape(text)
        text = text.strip()
        sound: str = line['Sound']
        selection_group: int = line['SelectionGroup']
        if selection_group != 0:
            if base_selection_group == -1:
                base_selection_group = selection_group
                selection_group = 1
            else:
                selection_group = selection_group - base_selection_group + 1
        if lower.startswith("#title;"):
            story_title = text.split(";")[1].strip() if ";" in text else text.strip()
            continue
        elif lower.startswith("#place;"):
            add_info(text)
            continue
        elif lower.startswith("#continued"):
            add_info("To be continued")
            continue

        is_st_line, lower = process_special_effects(lower, events)

        lower = lower.strip()
        # Search for strings like "[log=렌게 실루엣]I'm on an adventure to reclaim my youth![/log]"
        match = re.search(r"\[log=([^]]+)]", text)
        if match is not None:
            script = f"3;{match.group(1)};00;lorem ipsum"
            text = re.sub(r"\[/?log=([^]]+)]", "", text)

        character_query_result, speaker = get_scenario_character_id(script)

        option_dict = {}
        if selection_group != 0:
            option_dict = {"group": str(option_group), "option": str(selection_group)}

        if sound is not None and sound != "":
            sound = re.sub(r"^SE", "SE", sound, flags=re.IGNORECASE)
            sound_name = re.sub(r"^ ?(SE|SFX)_", "", sound)
            sound_name = re.sub(r"(?<! )_?([A-Z])", r" \1", sound_name)
            sound_name = re.sub(r"[_ ]\d{2}.?$", "", sound_name, flags=re.IGNORECASE)
            events.append({"": "sound", "sound": sound, "name": sound_name.strip().lower()} | option_dict)

        if lower == "":
            # finished all special effects and no text left, so we are all good except for maybe sound
            if text != "":
                print(f"Unprocessed text {text}")
            pass
        elif lower.startswith("#nextepisode;"):
            add_info(text.replace(";", ": "))
        elif lower.startswith("#na;("):
            text = process_info(text)
            add_info(text, option_dict)
            # TODO: deal with na issues
        elif lower.startswith("#na;") and (len(character_query_result) == 0 or character_query_result[0][0] is None):
            text = process_info(text)
            add_info(text, option_dict)
        elif re.search(r"\[n?s\d*]", text) is not None:
            options = re.split(r"\[n?s\d*]", text)
            options = options[1:]
            options = [o.strip() for o in options]
            if len(options) == 0:
                raise RuntimeError("Expected at least 1 option for " + text)
            elif len(options) == 1:
                events.append({"": "sensei", "text": options[0]} | option_dict)
            else:
                # sensei or reply
                option_group += 1
                base_selection_group = -1
                event = {"": "reply"}
                event.update((f"option%d_{index}", option) for index, option in enumerate(options, 1))
                event['group'] = str(option_group)
                events.append(event)
        elif (len(character_query_result) > 0 and speaker is not None) or (story_state.live2d_mode and text != ""):
            # student line
            if is_st_line:
                text = strip_st_line(text)

            character_query_result = [res for res in character_query_result if
                                      res[0] is not None and res[2] is not None and res[2].strip() != '']
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
            if text.strip() != "":
                if speaker is None:
                    if story_state.live2d_mode:
                        name, nickname, spine, portrait, sequence = character_name, "", "", "", None
                    else:
                        logger.error(f"Line with no speaker: {script}")
                        raise RuntimeError()
                else:
                    name, nickname, spine, portrait, sequence = speaker
                if name is not None and name != "":
                    character_list.add(name)
                portrait_dict = {}
                if spine is not None and spine != "":
                    # Ignore portrait here. Spine is almost always the better one to use.
                    portrait_dict = {
                        "spine": spine,
                        "sequence": str(sequence)
                    }
                event = {"": "student-text", "name": name, "affiliation": nickname, "text": text}
                event = event | portrait_dict | option_dict
                events.append(event)
        elif text != "":
            text = process_info(text)
            add_info(text, option_dict)
        else:
            pass
            # print(f"Unrecognizable line: {script}. Processed: {lower}.")

    if story_state.hanging_bgm:
        events.append({"": "bgm-stop"})

    return ParsedStory(
        intermediate_text=events,
        chars=character_list,
        music=bgm_list)


def process_popup(events, line, story_state):
    if line['PopupFileName'] != "":
        popup_name: str = line['PopupFileName']
        popup_name = popup_name.replace('U', 'u')
        if popup_name != story_state.current_popup:
            events.append({"": "popup", "popup": popup_name})
            story_state.current_popup = popup_name


def process_background(character_name, events, line, story_state, story_type):
    if line['BGName'] != 0:
        file_name = get_background_file_name(line['BGName'])
        if file_name is None:
            logger.warning(f"Background image not found for {line['BGName']}")
        else:
            # in some places (e.g. L2D) the same file name gets repeated multiple times
            if "SpineBG_Lobby" in file_name and story_type == StoryType.RELATIONSHIP:
                story_state.live2d_mode = True
                file_name = f"Memorial Lobby {character_name}"
            else:
                story_state.live2d_mode = False
            if story_state.current_background != file_name:
                events.append({"": "background", "background": file_name})
                story_state.current_background = file_name


def process_bgm(bgm_list, state: StoryState, line, events):
    bgm_id = line['BGMId']
    # sometimes bgm stop is issued at the start; need to avoid that
    if bgm_id != 0 and (bgm_id != 999 or len(events) > 0):
        if bgm_id == 999:
            events.append({"": "bgm-stop"})
            state.hanging_bgm = False
        else:
            bgm_list.add(bgm_id)
            bgm = get_bgm_file_info(bgm_id)
            bgm_title = music_file_name_to_title(bgm.name)

            loop_dict = {}
            if bgm.loop_start is not None or bgm.loop_end is not None:
                if abs(bgm.loop_end - 0.0) > 0.0001:
                    loop_dict = {
                        "loop-start": f"{bgm.loop_start:.2f}",
                        "loop-end": f"{bgm.loop_end:.2f}",
                    }

            events.append({
                              "": "bgm",
                              "bgm": bgm.name,
                              "name": bgm_title,
                              "volume": f"{bgm.volume:.2f}",
                          } | loop_dict)
            state.hanging_bgm = True


def process_special_effects(lower: str, events: list[dict[str, str]]):
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
        events.append({"": "info", "text": "Screen shakes"})
    return is_st_line, lower


def make_story_text(event_ids: int | list[int], story_type: StoryType, cat: str | list[str] | None = None,
                    character_name: str | None = None) -> StoryInfo | None:
    if cat is None:
        cat = story_type_to_cat(story_type)
    if isinstance(cat, str):
        cat = [cat]
    if isinstance(event_ids, int):
        event_ids = [event_ids]
    event_lines = []
    titles: list[str] = []
    summaries = []
    for event_id in event_ids:
        title, summary = get_story_title_and_summary(event_id, story_type)
        if title is not None:
            titles.append(title)
        if summary is not None:
            summaries.append(summary)
        lines = get_story_event(event_id)
        if lines is not None:
            if len(event_lines) > 0:
                event_lines.append({"Battle": True})
            event_lines.extend(lines)
    if len(event_lines) == 0:
        return None
    parsed_story = parse_story(event_lines, story_type, character_name=character_name)
    assert len(titles) > 0
    if len(titles) > 1:
        if any(t != titles[0] for t in titles):
            assert titles[0][-1].isnumeric()
            titles[0] = " ".join(titles[0].split(" ")[:-1])
    title = titles[0]
    summary = "\n\n".join(summaries)
    story_text = event_list_to_template(parsed_story.intermediate_text)
    story = StoryInfo(title=title,
                      summary=summary,
                      main_text=story_text,
                      category=make_categories(cat, parsed_story.chars, parsed_story.music))
    story.add_nav_arg("title", story.title, top_only=True)
    story.add_nav_arg("summary", story.summary, top_only=True)
    return story
