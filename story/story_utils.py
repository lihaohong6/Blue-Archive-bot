import json
import re
from dataclasses import dataclass, asdict, field
from enum import Enum
from functools import cache, cached_property
from pathlib import Path

from pywikibot.pagegenerators import GeneratorFactory
from wikitextparser import Template

from story.log_utils import logger
from utils import scenario_character_name, dev_name_to_canonical_name, load_json, load_json_list, s

@cache
def get_existing_sprites() -> dict[str, list[str]]:
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
    return json.load(open(result_file, "r", encoding="utf-8"))

reported_missing_spines: set[str] = set()


def run_hash(string):
    from xxhash import xxh32
    return int(xxh32(string).intdigest())

def get_scenario_character_id(text_ko_original: str) -> tuple[list[tuple[str, str, str, str]], int]:
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
            hashed = run_hash(string)
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

        # deal with cases such as 3;사키;S2_11 and 3;히마리;S2
        if expression_number is not None and "S" in expression_number:
            match = re.search(r"(S\d?)_(\d\d)", expression_number)
            if match is not None:
                spine_suffix, expression_number = match.groups()
            else:
                match = re.search(r"S\d+", expression_number)
                if match is not None:
                    spine_suffix = match.group(0)
                    expression_number = "00"
                else:
                    raise RuntimeError(f"Spine {expression_number} cannot be parsed")
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
        return [row for row in result if row['ModeType'] in {"Main", "SpecialOperation"}]


class StoryType(Enum):
    RELATIONSHIP = 0
    MAIN = 1
    SIDE = 2
    GROUP = 3
    EVENT = 4


def get_story_title_and_summary(query: int, story_type: StoryType) -> tuple[str, str]:
    def process(loaded) -> dict[int, str]:
        data_list = loaded['DataList']
        result: dict[int, str] = {}
        for row in data_list:
            result[row['Key']] = row['En']
        return result

    data = load_json("LocalizeExcelTable.json", process)
    title_key = f"ScenarioDigest_Title_{query}"
    description_key = f"ScenarioDigest_Description_{query}"
    return data.get(run_hash(title_key), None), data.get(run_hash(description_key), None)


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


def make_categories(start: list[str] = None, character_list: dict[str, int] = None, bgm_list: set[str] = None) -> str:
    if character_list is None:
        character_list = []
    if bgm_list is None:
        bgm_list = dict()
    if start is None:
        start = set()
    bgm_string = "{{Story/BGMList | " + " | ".join(str(bgm) for bgm in sorted(bgm_list)) + " }}"
    char_string = "{{Story/CharList | " + " | ".join(sorted(character_list.keys())) + " }}"
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
class StoryInfo:
    title: str
    summary: str
    main_text: str
    category: str
    chars: dict[str, int]
    nav_top: Template = field(default_factory=lambda: Template("{{Story/StoryTop}}"))
    nav_bottom: Template = field(default_factory=lambda: Template("{{Story/StoryBottom}}"))

    # FIXME: the before argument should be dropped
    def add_nav_arg(self, k: str, v: str, top_only: bool = False, before: str = None):
        self.nav_top.set_arg(k, v, before=before)
        if not top_only:
            self.nav_bottom.set_arg(k, v)

    @property
    def text(self):
        raise RuntimeError()

    @cached_property
    def full_text(self):
        def format_nav(nav: str) -> str:
            nav, _ = re.subn(r"(?<! )\|", " |", nav)
            nav, _ = re.subn(r"\|(?! )", "| ", nav)
            nav, _ = re.subn(r"(?<! )}}", " }}", nav)
            return nav

        return "\n".join([
            format_nav(str(self.nav_top)),
            self.main_text,
            format_nav(str(self.nav_bottom)),
            self.category
        ])


def make_story_nav(story: StoryInfo,
                   nav_args: NavArgs):
    args = asdict(nav_args)
    # FIXME: don't fix ordering
    for k in ['next_title', 'next_page', 'prev_title', 'prev_page']:
        v = args[k]
        if v == "":
            continue
        story.add_nav_arg(k, v, before="title")


def make_story_list_nav(stories: list[StoryInfo], page_prefix: str):
    for index, story in enumerate(stories):
        args = NavArgs()
        if index > 0:
            args.prev_title = stories[index - 1].title
            args.prev_page = f"{page_prefix}{index}"
        if index < len(stories) - 1:
            args.next_title = stories[index + 1].title
            args.next_page = f"{page_prefix}{index + 2}"
        make_story_nav(story, args)