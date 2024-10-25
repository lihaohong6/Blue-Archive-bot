import pickle
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pywikibot import Page, Site
from pywikibot.pagegenerators import GeneratorFactory
from wikitextparser import parse

import json


s = Site()


json_cache: dict[str | tuple[str, ...], Any] = {}


def load_json[T](file_name: str, processor: Callable[[dict], T] = lambda x: x) -> T:
    if file_name not in json_cache:
        json_cache[file_name] = processor(json.load(open("json/" + file_name, "r", encoding="utf-8")))
    return json_cache[file_name]


def load_json_list[T](files: tuple[str, ...], processor: Callable[[list[dict]], T]) -> T:
    if files not in json_cache:
        json_dicts = []
        for f in files:
            p = Path("json") / f
            if p.exists():
                json_dicts.append(json.load(open(p, "r", encoding="utf-8")))
        json_cache[files] = processor(json_dicts)
    return json_cache[files]


def normalize_char_name(original: str) -> str:
    return re.sub(r" ?\(.+\)", "", original)


def get_character_table(use_cache: bool = True) -> dict[int, str]:
    path = Path("cache/char_id.pickle")
    if path.exists() and use_cache:
        result = pickle.load(open(path, "rb"))
    else:
        path.parent.mkdir(exist_ok=True)
        gen = GeneratorFactory(s)
        gen.handle_args(["-cat:Characters"])
        gen = gen.getCombinedGenerator(preload=True)
        result = {}
        for p in gen:
            char_id = int(re.search(r"Id *= *([0-9]+)", p.text).group(1))
            char_name = re.search(r"\| *(Wiki)?[Nn]ame *= *(?P<name>[^\n]+)", p.text).group("name")
            result[char_id] = char_name
        pickle.dump(result, open(path, "wb"))
    return result


dev_name_map: dict[str, str] = {}


def dev_name_to_canonical_name(dev_name: str) -> str:
    if len(dev_name_map) == 0:
        def read_dev_name_map(fname: str):
            name_map = json.load(open(fname, "r", encoding="utf-8"))
            for k, v in name_map.items():
                wiki_name = v['firstname']
                if v['variant'] is not None:
                    wiki_name += f" ({v['variant']})"
                dev_name_map[k] = wiki_name
        read_dev_name_map('json/devname_map.json')
        read_dev_name_map('json/devname_map_aux.json')
    if dev_name == "Null":
        return ""
    if dev_name in dev_name_map:
        return dev_name_map[dev_name]
    if dev_name.capitalize() in dev_name_map:
        return dev_name_map[dev_name.capitalize()]
    if dev_name.lower() in dev_name_map:
        return dev_name_map[dev_name.lower()]
    print("Cannot find canonical name of " + dev_name)
    return ""


def load_momotalk() -> dict[int, list[dict]]:
    result = {}
    for i in range(0, 10):
        file_name = Path(f"json/AcademyMessanger{i}ExcelTable.json")
        if not file_name.exists():
            continue
        momotalk = json.load(open(file_name, "r", encoding="utf-8"))
        if 'DataList' in momotalk:
            momotalk = momotalk['DataList']
        for talk in momotalk:
            cid = talk['CharacterId']
            if cid not in result:
                result[cid] = []
            result[cid].append(talk)
    return result


cached_favor_schedule = {}


def load_favor_schedule() -> dict[int, list[dict]]:
    if len(cached_favor_schedule) == 0:
        loaded = json.load(open("json/AcademyFavorScheduleExcelTable.json", "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            cid = row['CharacterId']
            if cid not in cached_favor_schedule:
                cached_favor_schedule[cid] = []
            cached_favor_schedule[cid].append(row)
    return cached_favor_schedule


scenario_character_name: dict[int, dict] = {}

background_file_name: dict[int, str] = {}


def get_background_file_name(background_id: int) -> str:
    if len(background_file_name) == 0:
        loaded = json.load(open("json/ScenarioBGNameExcelTable.json", "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            bg_id = row['Name']
            bg_name: str = row['BGFileName']
            background_file_name[bg_id] = bg_name.split("/")[-1]
    return background_file_name[background_id]


bgm_file_info: dict[int, tuple[str, list[float]]] = {}


def get_bgm_file_info(query_id: int) -> tuple[str, list[float]]:
    def list_or_none(l: list) -> str | None:
        if len(l) == 0:
            return None
        return l[0]
    
    if len(bgm_file_info) == 0:
        loaded = json.load(open("json/BGMExcelTable.json", "r", encoding="utf-8"))
        loaded = loaded['DataList']
        for row in loaded:
            bgm_id = row['Id']
            bgm_name: str = list_or_none(row['Path'])
            loop_start = list_or_none(row['LoopStartTime'])
            loop_end = list_or_none(row['LoopEndTime'])
            volume = list_or_none(row['Volume'])
            transition_time = list_or_none(row['LoopTranstionTime'])
            offset_time = list_or_none(row['LoopOffsetTime'])
            bgm_file_info[bgm_id] = (bgm_name.split("/")[-1], [loop_start, loop_end, volume, transition_time, offset_time])
    if query_id in bgm_file_info:
        return bgm_file_info[query_id]
    raise RuntimeError(f"Bgm with id {query_id} not found.")


music_dict: dict[int, str] = {}


def get_music_info(music_id: int) -> str:
    if len(music_dict) == 0:
        p = Page(s, "Music")
        parsed = parse(p.text)
        for t in parsed.templates:
            if t.name.strip() != "Track":
                continue
            music_dict[int(t.get_arg("Id").value)] = t.get_arg("Title").value.strip()
    return music_dict[music_id]


def music_file_name_to_title(file_name: str) -> str:
    bgm_id = int(re.search(r"\d+", file_name).group(0))
    bgm_name = get_music_info(bgm_id)
    if bgm_name == "":
        return file_name
    return bgm_name


if __name__ == "__main__":
    raise NotImplementedError("Do not run this script directly.")