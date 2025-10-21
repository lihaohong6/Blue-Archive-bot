import re
import sys
from pathlib import Path
from typing import Callable

import pywikibot as pwb
from pywikibot.page import FilePage
from pywikibot.pagegenerators import PreloadingGenerator

s = pwb.Site()
s.login()
upload_path = Path("./upload")


def upload_cut_scenes(image_path: Path) -> None:
    def glob() -> list[Path]:
        def name_filter(f: str) -> bool:
            return re.search(r"_(kr|tw|th)\.jpg", f, re.IGNORECASE) is None

        return [f for f in image_path.rglob("*.jpg") if name_filter(f.name)]

    already_exist = set()
    gen = (FilePage(s, "File:" + f.name) for f in glob())
    preload = PreloadingGenerator(generator=gen)
    for p in preload:
        p: FilePage
        if p.exists():
            already_exist.add(p.title(underscore=True, with_ns=False))
    for f in glob():
        if f.name in already_exist:
            continue
        is_cut_scene = False
        if f.name.startswith("BG_CS"):
            is_cut_scene = True

        if is_cut_scene:
            cat = "[[Category:Cutscenes]]"
        else:
            cat = "[[Category:Background images]]"

        try:
            s.upload(FilePage(s, "File:" + f.name), source_filename=str(f),
                     comment="Batch upload background images and cutscenes",
                     text=cat)
        except Exception as e:
            print(f.name, e)


def upload_files(extensions: tuple[str, ...],
                 path: Path,
                 text: str,
                 comment: str = "Batch upload files",
                 redirect: bool = False,
                 file_name_filter: Callable[[str], bool] = lambda f: True,
                 name_mapper: Callable[[str], str] = lambda f: f):
    assert path.exists()

    already_exist = set()

    def get_all_files():
        result = []
        for e in extensions:
            result.extend(path.rglob(f"*.{e}"))
        return [f for f in result if file_name_filter(f.name)]

    file_list = get_all_files()
    print(f"{len(file_list)} files found")

    gen = (FilePage(s, "File:" + name_mapper(f.name)) for f in file_list)
    preload = PreloadingGenerator(generator=gen)
    exists_count = 0
    for p in preload:
        p: FilePage
        if p.exists():
            already_exist.add(p.title(underscore=False, with_ns=False))
            already_exist.add(p.title(underscore=True, with_ns=False))
            exists_count += 1
    print(exists_count, "files already exist")
    for f in file_list:
        if name_mapper(f.name) in already_exist:
            continue
        try:
            s.upload(FilePage(s, "File:" + name_mapper(f.name)), source_filename=str(f), comment=comment,
                     text=text)
        except Exception as e:
            if not redirect:
                continue
            error_string = str(e)
            search = re.search(r"duplicate of \['([^']+)'", error_string)
            if search is None:
                search = re.search(r'duplicate of \["([^"]+)"', error_string)
            if search is not None:
                p = FilePage(s, "File:" + name_mapper(f.name))
                p.text = f"#REDIRECT [[File:{search.group(1)}]]"
                p.save(summary="Redirect to existing file")
            else:
                print(f.name, "\n", e)


def upload_bgm(path: Path):
    upload_files(("ogg",),
                 path=path,
                 text="[[Category:Background music]]",
                 comment="Batch upload bgm",
                 redirect=True)


def normalize_png(file_name: str) -> str:
    o, _ = re.subn(r"\.png", ".png", file_name, flags=re.IGNORECASE)
    o = o[0].upper() + o[1:]
    return o


def upload_momotalk_images(path: Path):
    upload_files(("png", ),
                 path=path,
                 text="[[Category:MomoTalk images]]",
                 file_name_filter=lambda f: f.lower().startswith("mo"),
                 name_mapper=normalize_png)


def upload_story_popups(path: Path):
    upload_files(("png", ),
                 path=path,
                 text="[[Category:Story popup images]]",
                 file_name_filter=lambda f: f.lower().startswith("popup"),
                 name_mapper=normalize_png)


def upload_sound_effects(path: Path):
    upload_files(("wav", ),
                 path=path,
                 text="[[Category:Sound effects]]",
                 file_name_filter=lambda f: f.startswith("SE"),)


def upload_story():
    if sys.platform.startswith("linux"):
        root = Path("/home/peter/Documents/Programs/ba-cdn/data_jp/cdn_data")
    else:
        root = Path(r"D:\BA\ba-cdn\data_jp\cdn_data")
    assert root.exists()
    cur = max([subdir for subdir in root.iterdir() if subdir.is_dir()], key=lambda f: f.name)
    assert cur.exists()
    data = cur / "MediaResources" / "GameData"
    assert data.exists()
    ui_path = data / "UIs"
    scenario_path = ui_path / "03_Scenario"
    assert scenario_path.exists()
    upload_cut_scenes(scenario_path / "01_Background")
    scenario_image_path = scenario_path / "04_ScenarioImage"
    assert scenario_image_path.exists()
    upload_momotalk_images(scenario_image_path)
    upload_story_popups(scenario_image_path)
    upload_bgm(data / "Audio" / "BGM")



def rename_files(path: Path):
    files = path.glob("*.png")
    for f in files:
        fname = f.name
        f.rename(path.joinpath(f"Fankit {fname}"))


def main():
    upload_story()


if __name__ == "__main__":
    main()
