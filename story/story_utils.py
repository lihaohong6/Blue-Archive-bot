import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from pywikibot import Site
from pywikibot.pagegenerators import GeneratorFactory
from torch.fx.passes.pass_manager import logger

from utils import scenario_character_name, dev_name_to_canonical_name, load_json, load_json_list

s = Site()
sprites_cache = {}

def get_existing_sprites() -> dict[str, list[str]]:
    if len(sprites_cache) > 0:
        return sprites_cache
    result_file = Path("cache/sprites.json")
    if not result_file.exists():
        gen = GeneratorFactory(s)
        gen.handle_args(['-cat:Character sprites', '-cat:Character sprite redirects', '-ns:File'])
        gen = gen.getCombinedGenerator()
        result: dict[str, list[str]] = {}
        for p in gen:
            title = p.title(with_ns=False, underscore=False)
            name, num = re.search(r"^(.*)[ _](\d\d)\.png", title).groups()
            if name not in result:
                result[name] = []
            result[name].append(num)
        json.dump(result, open(result_file, "w", encoding="utf-8"), ensure_ascii=False, indent=4)
    sprites_cache.update(json.load(open(result_file, "r", encoding="utf-8")))
    return sprites_cache

reported_missing_spines: set[str] = set()


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
        # deal with cases such as 3;사키;S2_11
        search_text = re.search(r"^\d+;([^;]+);([S_\d]+);?", original)
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
            logger.warning(f"Cannot find scenario character name in table. Text: {name_ko}. Hash: {hashed}.")
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

        # Sometimes spine does not agree with portrait. In that case, use spine unless spine is empty but portrait
        # is not.
        if spine != portrait and spine.strip() == '' and portrait != '':
            spine = portrait
        existing_sprites = get_existing_sprites()
        if spine != "" and spine not in existing_sprites:
            if (spine + " diorama") in existing_sprites:
                spine += " diorama"
            else:
                if spine not in reported_missing_spines:
                    logger.warning(f"Spine {spine} not found")
                    reported_missing_spines.add(spine)

        # deal with cases such as 3;사키;S2_11
        if expression_number is not None and "S" in expression_number:
            match = re.search(r"(S\d?)_(\d\d)", expression_number)
            assert match is not None
            spine_suffix, expression_number = match.groups()
            spine += " " + spine_suffix

        if spine in existing_sprites and expression_number not in existing_sprites[spine]:
            repl = existing_sprites[spine][0]
            logger.debug(f"{spine}_{expression_number} does not exist. Replacing with {repl}.")
            expression_number = repl

        obj = (name, nickname, spine, portrait, expression_number)
        # check if there is text after the last semicolon; if so, this is the speaker
        if re.search(r"^\d+;([^;]+);([S_\d]+);.", original) is not None or na:
            speaker = obj
        result.append(obj)
    return result, speaker


def get_main_scenarios() -> list[dict]:
    with open ("json/ScenarioModeExcelTable.json", "r", encoding="utf-8") as f:
        result = json.load(f)
        result = result['DataList']
        return [row for row in result if row['ModeType'] == "Main"]


def get_story_title_and_summary(query: int | str) -> tuple[str, str]:
    """
    This file is organized in a way that summary immediately follows the title, so we can take advantage
    of this by recording the index of each json entry.
    """

    def process(loaded: dict) -> tuple[list, dict, dict]:
        loaded = loaded['DataList']
        localization_list: list[str] = []
        localization_dict: dict[int, int] = {}
        en_to_index: dict[str, list[int]] = {}
        for index, row in enumerate(loaded):
            row_id = row['Key']
            row_text = row['En']
            localization_list.append(row_text)
            localization_dict[row_id] = index
            def add_to_dict(text: str):
                if text not in en_to_index:
                    en_to_index[text] = []
                en_to_index[text].append(index)
            add_to_dict(row_text)
            row_text_changed = re.sub(r" +[12]$", "", row_text)
            if row_text_changed != row_text:
                add_to_dict(row_text_changed)
            if "Part" in row_text:
                add_to_dict(row_text.replace("Part ", ""))
        return localization_list, localization_dict, en_to_index

    lst, id_to_index, en_to_index = load_json("LocalizeExcelTable.json", process)

    if isinstance(query, int):
        index = id_to_index[query]
        return lst[index], lst[index + 1]
    else:
        indices: list[int] | None = en_to_index.get(query, None)
        if indices is None or len(indices) > 3:
            return query, ""
        summaries = []
        for index in indices[1:]:
            summaries.append(lst[index + 1])
        return query, " ".join(summaries)


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
    line, _ = re.subn(r"\[log=[^]]+]", "", line)
    line = line.replace("[/log]", "")
    line, _ = re.subn(r"\[wa:\d+]", "", line)
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


def get_story_event(query_group_id: int) -> list[dict] | None:
    e = get_events("ScenarioScriptExcelTable{0}.json")
    return e.get(query_group_id, None)


@dataclass
class NavArgs:
    prev_title: str = ""
    prev_page: str = ""
    next_title: str = ""
    next_page: str = ""


@dataclass
class TitleArgs:
    title: str = ""
    summary: str = ""


def make_custom_nav(nav_top: str,
                    nav_bottom: str,
                    nav_args: NavArgs,
                    title_args: TitleArgs) -> tuple[str, str]:
    def make_args(args: dict[str, str]) -> str:
        return " | ".join(f"{k}={v}" for k, v in args.items() if v)

    nav_string = make_args(asdict(nav_args))
    title_string = make_args(asdict(title_args))
    nav_top = nav_top.replace("}}", " | " + nav_string + " | " + title_string + " }}")
    nav_bottom = nav_bottom.replace("}}", " | " + nav_string + " }}")
    return nav_top, nav_bottom