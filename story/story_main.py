from pywikibot import Page

from utils import get_character_table, s, save_page


def make_character_story_subpages():
    for char in get_character_table().values():
        p = Page(s, char)
        assert p.exists()
        p = Page(s, f"{char}/story")
        save_page(p, "{{CharacterStories}}", summary="batch create character story pages")


def main():
    make_character_story_subpages()


if __name__ == "__main__":
    main()