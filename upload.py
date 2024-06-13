from pathlib import Path
import re
import pywikibot as pwb
from pywikibot.page import FilePage
from pywikibot.site import APISite
from pywikibot.specialbots import UploadRobot
from pywikibot.pagegenerators import PreloadingGenerator

from utils import normalize_char_name

s: APISite = pwb.Site()
s.login()
path = Path("./upload")

def upload_cut_scenes():
    image_path = Path(r"./upload")
    
    def glob() -> list[Path]:
        def name_filter(f: str) -> bool:
            return re.search(r"_(Kr|kr|Tw|tw|Th|th)\.jpg", f) is None
            
        return [f for f in image_path.glob("*.jpg") if name_filter(f.name)]
    
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
            s.upload(FilePage(s, "File:" + f.name), source_filename=str(f), comment="Batch upload background images and cutscenes",
                     text=cat)
        except Exception as e:
            print(f.name, e)

def upload_files():
    EXTENSION = "png"
    COMMENT = "Batch upload fankit images"
    TEXT = "[[Category:Fankit images]]"
    REDIRECT = False
    already_exist = set()
    
    def name_mapper(original: str, with_file: bool = True) -> str:
        prefix = ""
        if with_file:
            prefix = "File:"
        return prefix + original
        return prefix + "Memorial Lobby " + original
    
    gen = (FilePage(s, name_mapper(f.name)) for f in path.glob(f"*.{EXTENSION}"))
    preload = PreloadingGenerator(generator=gen)
    exists_count = 0
    for p in preload:
        p: FilePage
        if p.exists():
            already_exist.add(p.title(underscore=False, with_ns=False))
            already_exist.add(p.title(underscore=True, with_ns=False))
            exists_count += 1
    print(exists_count, "files already exist")
    for f in path.glob(f"*.{EXTENSION}"):
        if name_mapper(f.name, with_file=False) in already_exist:
            continue
        try:
            s.upload(FilePage(s, name_mapper(f.name)), source_filename=str(f), comment=COMMENT,
                     text=TEXT)
        except Exception as e:
            if not REDIRECT:
                continue
            error_string = str(e)
            search = re.search(r"duplicate of \['(.+\." + EXTENSION +")\'\]", error_string)
            if search is not None:
                p = FilePage(s, name_mapper(f.name))
                p.text = f"#REDIRECT [[File:{search.group(1)}]]"
                p.save(summary="Redirect to existing file")
            else:
                print(f.name, "\n", e)

def rename_files():
    files = path.glob("*.png")
    for f in files:
        fname = f.name
        f.rename(path.joinpath(f"Fankit {fname}"))
        
        
upload_files()
