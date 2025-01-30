import pywikibot as pwb
from pywikibot.pagegenerators import GeneratorFactory
import re

s = pwb.Site()

def navbox1():
    schools = ["Abydos", "Gehenna", "Hyakkiyako", "Millennium", "Red Winter", "Shanhaijing", "SRT", "Trinity", "Valkyrie"]

    for school in schools:
        gen = GeneratorFactory(site=s)
        gen.handle_args(["-cat:Students of " + school, "-ns:0"])
        gen = gen.getCombinedGenerator(preload=True)
        for page in gen:
            page: pwb.Page
            text = page.text
            text = text.replace(r"{{CharacterNavbox}}", r"{{Kivotos|" + school + r"}}")
            if page.text.strip() == text.strip():
                print("No change on " + page.title())
                continue
            setattr(page, "_bot_may_edit", True)
            page.text = text
            page.save("Replace navbox with [[Template:Kivotos]]", minor=True)


def main():
    gen = GeneratorFactory(site=s)
    gen.handle_args(["-cat:Club navbox"])
    gen = gen.getCombinedGenerator()
    for club in gen:
        club: pwb.Page
        club_name = club.title(with_ns=False)
        for char_page in club.linkedPages():
            if not char_page.exists():
                continue
            text = char_page.text
            if "{{Character" not in text:
                continue
            if re.search(r"\{\{ *" + club_name + " *\}\}", text) is not None:
                print("Template already exists in " + char_page.title())
                continue
            text = text.replace(r"{{Kivotos|", "{{" + club_name + "}}\n{{Kivotos|")
            if text == char_page.text:
                print("Skipping " + char_page.title())
                continue
            setattr(char_page, "_bot_may_edit", True)
            char_page.text = text
            char_page.save("Add club tempalte", minor=True)


if __name__ == "__main__":
    main()
