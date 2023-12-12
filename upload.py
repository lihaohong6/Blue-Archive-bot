from pathlib import Path
import re
import pywikibot as pwb
from pywikibot.page import FilePage
from pywikibot.site import APISite
from pywikibot.specialbots import UploadRobot

s: APISite = pwb.Site()
p = Path("./upload")

def upload_images():
    for i in range(74, 112):
        source = p.joinpath(f"{i}.png")
        if not source.exists():
            print(source.name)
        s.upload(FilePage(s, f"File:yonkoma_{i}_2.png"), source_filename=str(source), comment="Batch upload second image of 4-panel manga",
                 text="[[Category:4-panel manga]]")

upload_images()

def rename_files():
    for f in p.glob("*.png"):
        fname = f.name
        num = int(re.search(r"(\d+)", fname).group(1))
        offset = 101 if fname[0] == 'b' else 0
        num += offset
        f.rename(p.joinpath(f"{num}.png"))
