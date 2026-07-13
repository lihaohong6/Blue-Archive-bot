import io
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Callable

import UnityPy
import pywikibot as pwb
from pywikibot.page import FilePage
from pywikibot.pagegenerators import PreloadingGenerator

s = pwb.Site()
s.login()
upload_path = Path("./cache/upload")
upload_path.mkdir(exist_ok=True, parents=True)


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
                 name_mapper: Callable[[str], str] = lambda f: f,
                 exists_name_mapper: Callable[[str], list[str]] | None = None):
    assert path.exists()

    if exists_name_mapper is None:
        exists_name_mapper = lambda f: [name_mapper(f)]

    already_exist = set()

    def get_all_files():
        result = []
        for e in extensions:
            result.extend(path.rglob(f"*.{e}"))
        return [f for f in result if file_name_filter(f.name)]

    file_list = get_all_files()
    print(f"{len(file_list)} files found")

    gen = (pwb.Page(s, "File:" + name) for f in file_list for name in exists_name_mapper(f.name))
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
        if any(name in already_exist for name in exists_name_mapper(f.name)):
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


def wav_to_ogg(wav_bytes: bytes) -> bytes:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "ogg", "pipe:1"],
        input=wav_bytes, stdout=subprocess.PIPE, check=True,
    )
    return result.stdout


def extract_sound_effects(patch_pack_path: Path, output_path: Path):
    output_path.mkdir(parents=True, exist_ok=True)
    for zip_path in sorted(patch_pack_path.glob("FullPatch_*.zip")):
        with zipfile.ZipFile(zip_path) as z:
            for bundle_name in z.namelist():
                if not bundle_name.endswith(".bundle") or "sfx" not in bundle_name.lower():
                    continue
                env = UnityPy.load(io.BytesIO(z.read(bundle_name)))
                for obj in env.objects:
                    if obj.type.name != "AudioClip":
                        continue
                    clip = obj.read()
                    if not clip.m_Name.startswith("SE"):
                        continue
                    for sample_name, sample_bytes in clip.samples.items():
                        out_file = output_path / (Path(sample_name).stem + ".ogg")
                        if not out_file.exists():
                            out_file.write_bytes(wav_to_ogg(sample_bytes))


def sound_effect_name_variants(f: str) -> list[str]:
    stem = f.rsplit(".", 1)[0]
    return [stem + ".ogg", stem + ".wav"]


def upload_sound_effects(path: Path):
    upload_files(("ogg", ),
                 path=path,
                 text="[[Category:Sound effects]]",
                 comment="Batch upload sound effects",
                 redirect=True,
                 file_name_filter=lambda f: f.startswith("SE"),
                 exists_name_mapper=sound_effect_name_variants)


def upload_story():
    if sys.platform.startswith("linux"):
        root = Path("/home/peter/Documents/Programs/ba-cdn/data_jp/cdn_data")
    else:
        root = Path(r"D:\BA\ba-cdn\data_jp\cdn_data")
    assert root.exists()
    cur = max([subdir for subdir in root.iterdir() if subdir.is_dir()], key=lambda f: f.name)
    # assert cur.exists()
    # data = cur / "MediaResources" / "GameData"
    # assert data.exists()
    # ui_path = data / "UIs"
    # scenario_path = ui_path / "03_Scenario"
    # assert scenario_path.exists()
    # upload_cut_scenes(scenario_path / "01_Background")
    # scenario_image_path = scenario_path / "04_ScenarioImage"
    # assert scenario_image_path.exists()
    # upload_momotalk_images(scenario_image_path)
    # upload_story_popups(scenario_image_path)
    # upload_bgm(data / "Audio" / "BGM")
    se_path = upload_path / "SE"
    extract_sound_effects(cur / "Android_PatchPack", se_path)
    upload_sound_effects(se_path)



def rename_files(path: Path):
    files = path.glob("*.png")
    for f in files:
        fname = f.name
        f.rename(path.joinpath(f"Fankit {fname}"))


def main():
    upload_story()


if __name__ == "__main__":
    main()
