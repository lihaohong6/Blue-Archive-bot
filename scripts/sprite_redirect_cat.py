import re

from pywikibot import Site
from pywikibot.pagegenerators import GeneratorFactory, AllpagesPageGenerator

s = Site()
gen = AllpagesPageGenerator(start="!", namespace="File", includeredirects=True, site=s, content=True)
for page in gen:
    if "REDIRECT" in page.text and "ategory" not in page.text and re.search(r"[_ ]\d\d\.png", page.title()) is not None:
        page.text += "\n[[Category:Character sprite redirects]]"
        page.save(summary="add category to track sprite redirects")

