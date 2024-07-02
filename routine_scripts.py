from pywikibot import Site, Page
from pywikibot.pagegenerators import GeneratorFactory, PreloadingGenerator

s = Site()


def dialog_cats():
    gen = GeneratorFactory(s)
    gen.handle_args(["-cat:Characters", "-ns:0"])
    gen = gen.getCombinedGenerator()
    pages = [Page(s, f"Category:{page.title()} dialog") for page in gen]
    existing = set(p.title() for p in PreloadingGenerator(pages))
    for p in pages:
        if p.title() not in existing:
            p.text = "[[Category:Dialogs by character]]"
            p.save("batch create character dialog categories")
    gen = GeneratorFactory(s)
    gen.handle_args(["-cat:Characters audio", "-ns:0"])
    gen = gen.getCombinedGenerator()
    for page in gen:
        page: Page
        title = page.title().replace("/audio", "")
        existing_files = GeneratorFactory(s)
        existing_files.handle_args([f"-cat:{title} dialog"])
        existing_files = set(p.title(with_ns=True, underscore=True) for p in existing_files.getCombinedGenerator())
        out_files = GeneratorFactory(s)
        out_files.handle_args(['-imagesused:' + page.title(underscore=True), '-titleregex:ogg$'])
        out_files = out_files.getCombinedGenerator(preload=True)
        for file_page in out_files:
            if file_page.title(with_ns=True, underscore=True) in existing_files:
                continue
            setattr(file_page, "_bot_may_edit", True)
            file_page.text += f"\n[[Category:{title} dialog]]"
            file_page.save("batch add dialog categories")


if __name__ == '__main__':
    dialog_cats()
