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
    image_path = Path(r"D:\BA\MediaResources\UIs\03_Scenario\01_Background")
    
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
            print(f.name, e)

def upload_audio():
    already_exist = set()
    gen = (FilePage(s, "File:" + f.name) for f in path.glob("*.wav"))
    preload = PreloadingGenerator(generator=gen)
    for p in preload:
        p: FilePage
        if p.exists():
            already_exist.add(p.title(underscore=True, with_ns=False))
    print(len(already_exist), " audio files already exist")
    for f in path.glob("*.wav"):
        if f.name in already_exist:
            continue
        try:
            s.upload(FilePage(s, "File:" + f.name), source_filename=str(f), comment="Batch upload sound effects",
                     text="[[Category:Sound effects]]")
        except Exception as e:
            error_string = str(e)
            search = re.search(r"duplicate of \['(.+\.wav)\'\]", error_string)
            if search is not None:
                p = FilePage(s, "File:" + f.name)
                p.text = f"#REDIRECT [[File:{search.group(1)}]]"
                p.save(summary="Redirect to existing audio file")
            else:
                print(f.name, "\n", e)
                
upload_audio()

def rename_files():
    for f in p.glob("*.png"):
        fname = f.name
        num = int(re.search(r"(\d+)", fname).group(1))
        offset = 101 if fname[0] == 'b' else 0
        num += offset
        f.rename(p.joinpath(f"{num}.png"))
