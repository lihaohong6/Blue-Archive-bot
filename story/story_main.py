from pywikibot import Page

from story.event_story import make_event_stories
from story.main_story import make_main_story
from story.relationship_story import make_relationship_stories
from story.side_story import make_side_stories
from utils import get_character_table, s, save_page


def make_character_story_subpages():
    for char in get_character_table().values():
        p = Page(s, char)
        assert p.exists()
        p = Page(s, f"{char}/story")
        save_page(p, "{{CharacterStories}}", summary="batch create character story pages")


def main():
    make_character_story_subpages()
    make_main_story()
    make_relationship_stories()
    make_side_stories()
    make_event_stories()


if __name__ == "__main__":
    main()