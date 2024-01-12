import pywikibot as pwb
from pywikibot import Page, Site
from pywikibot.pagegenerators import PreloadingGenerator, GeneratorFactory
import wikitextparser as wtp
from wikitextparser import Template
import re

s = Site()
s.login()
gen = GeneratorFactory(s)
gen.handle_args(['-cat:Characters galleries', '-ns:0'])
galleries: list[Page] = list(gen.getCombinedGenerator(preload=True))
# galleries = [Page(s, "Mika/gallery")]

gallery_and_student: list[tuple[Page, Page]] = []
students = []
for g in galleries:
    s = Page(s, g.title(underscore=False).split("/")[0])
    gallery_and_student.append((s, g))
    students.append(s)

gen = PreloadingGenerator(students)
students = list(gen)
placeholder = "SP_PLACEHOLDER"

for (s, g) in gallery_and_student:
    gallery = wtp.parse(g.text)
    student_name = s.title()
    variants = {}
    for section in gallery.sections:
        search = re.search(student_name + r" \(([^\)]+)\)", section.title if section.title is not None else "")
        if search is not None:
            image_name = re.search(r"\n(.*\.png)\n", str(section)).group(1)
            variants[image_name] = search.group(1)
    
    parsed = wtp.parse(s.text)
    t = [t for t in parsed.templates if t.name.strip().lower() == "character"]
    assert len(t) == 1
    t: Template = t[0]
    v_index = 1
    while True:
        arg = t.get_arg("Variant" + str(v_index))
        if arg is None:
            break
        arg2 = t.get_arg("Image" + str(v_index))
        assert arg2 is not None
        image_file = arg2.value.strip()
        variant = arg.value.strip()
        assert image_file in variants
        variants.pop(image_file)
        v_index += 1
    for file_name, variant in variants.items():
        arg1_name = f" Variant{v_index} "
        t.set_arg(arg1_name, variant, before="JPName", preserve_spacing=True)
        t.set_arg(f" Image{v_index} ", file_name, after=arg1_name, preserve_spacing=True)
        v_index += 1
    replaced, _ = re.subn(r"(\d)=", r"\1 =", str(t))
    t.string = replaced
    result = str(parsed).replace(placeholder, "")
    if s.text.strip() != str(result).strip():
        print("Error in " + student_name)
        
