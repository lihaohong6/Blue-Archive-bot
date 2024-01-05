from pathlib import Path
import re
import pywikibot as pwb
from pywikibot.page import FilePage
from pywikibot.site import APISite
from pywikibot.specialbots import UploadRobot
from pywikibot.pagegenerators import PreloadingGenerator

s: APISite = pwb.Site()
path = Path("./upload")

def upload_images():
    already_exist = set()
    gen = (FilePage(s, "File:" + f.name) for f in path.glob("*.jpg"))
    preload = PreloadingGenerator(generator=gen)
    for p in preload:
        p: FilePage
        if p.exists():
            already_exist.add(p.title(underscore=True, with_ns=False))
    for f in path.glob("*.jpg"):
        if f.name in already_exist:
            continue
        is_cutscene = False
        if f.name.startswith("BG_CS"):
            is_cutscene = True
            
        if is_cutscene:
            cat = "[[Category:Cutscenes]]"
        else:
            cat = "[[Category:Background images]]"
        
        try:
            s.upload(FilePage(s, "File:" + f.name), source_filename=str(f), comment="Batch upload background images and cutscenes",
                    text=cat)
        except Exception as e:
            print(e)

upload_images()

def rename_files():
    for f in p.glob("*.png"):
        fname = f.name
        num = int(re.search(r"(\d+)", fname).group(1))
        offset = 101 if fname[0] == 'b' else 0
        num += offset
        f.rename(p.joinpath(f"{num}.png"))
