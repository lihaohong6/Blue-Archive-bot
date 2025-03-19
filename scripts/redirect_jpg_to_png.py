from pywikibot import Site, FilePage
from pywikibot.pagegenerators import PreloadingGenerator, GeneratorFactory


def main():
    s = Site()
    gen = GeneratorFactory(s)
    gen.handle_args(['-ns:File', '-cat:Memorial_lobby_images', '-titleregex:png$'])
    png_pages = list(gen.getCombinedGenerator())
    jpg_pages = [FilePage(s, p.title(with_ns=True).replace(".png", ".jpg")) for p in png_pages]
    gen = PreloadingGenerator(jpg_pages)
    for p in gen:
        if p.exists():
            continue
        p.set_redirect_target(p.title(with_ns=True).replace(".jpg", ".png"), summary="Redirect jpg to png", create=True)


if __name__ == '__main__':
    main()
else:
    raise RuntimeError("Do not import this module. Just run it.")
