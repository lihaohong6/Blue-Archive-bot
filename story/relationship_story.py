import itertools
from dataclasses import dataclass, field

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from story.story_parser import make_story_text
from story.story_utils import s, StoryType, StoryInfo, make_story_nav, NavArgs
from utils import load_favor_schedule, get_character_table, save_page


@dataclass
class RelationshipStory:
    story_info: StoryInfo
    sequence: int
    favor: int

    def page(self, char_name) -> str:
        return f"{char_name}/Relationship Story/{self.sequence}"


@dataclass
class CharacterStory:
    char_name: str
    text: str = ""
    story_list: list[RelationshipStory] = field(default_factory=list)

    @property
    def page(self):
        return f"{self.char_name}/Relationship Story"


def parse_character_relationship_story(event_list: list[dict], char_name: str) -> CharacterStory:
    char_story = CharacterStory(char_name)
    base_text = ["{{Story/RelationshipStoryTop}}"]
    for index, event in enumerate(event_list, 1):
        favor_level = event["FavorRank"]
        story = make_story_text(event['ScenarioSriptGroupId'], StoryType.RELATIONSHIP, character_name=char_name)
        if story is None:
            raise RuntimeError(f"Story of {char_name} with event {event} failed to parse")
        story = RelationshipStory(story, index, favor_level)
        char_story.story_list.append(story)
        base_text.append(f"==[[/{story.sequence}|{story.story_info.title}]]==")
        base_text.append(story.story_info.summary)
    base_text.append("[[Category:Relationship stories]]")
    char_story.text = "\n\n".join(base_text)
    return char_story


def parse_all_relationship_story_pages():
    favor_schedule = load_favor_schedule()
    character_table = get_character_table()
    all_stories: list[CharacterStory] = []
    for character_id, event_list in favor_schedule.items():
        if character_id not in character_table:
            print(f"Character id {character_id} has no corresponding name.")
            continue
        try:
            char_name = character_table[character_id]
            story = parse_character_relationship_story(event_list, char_name)
            all_stories.append(story)
        except NotImplementedError as e:
            print(e)
            print(character_table[character_id] + " failed")

    for character_story in all_stories:
        stories = character_story.story_list
        for index, story in enumerate(stories):
            next_story = stories[index + 1] if index + 1 < len(stories) else None
            prev_story = stories[index - 1] if index - 1 >= 0 else None
            args = NavArgs()
            if next_story is not None:
                args.next_title = next_story.story_info.title
                args.next_page = next_story.page(character_story.char_name)
            if prev_story is not None:
                args.prev_title = prev_story.story_info.title
                args.prev_page = prev_story.page(character_story.char_name)
            make_story_nav(story.story_info, args)

    return all_stories


def make_relationship_stories():
    stories = parse_all_relationship_story_pages()
    all_titles = itertools.chain.from_iterable([[char_stories.page] + [story.page(char_stories.char_name)
                                                                       for story in char_stories.story_list]
                                                for char_stories in stories])
    pages = PreloadingGenerator(Page(s, title) for title in all_titles)
    title_to_page: dict[str, Page] = dict((p.title(), p) for p in pages)
    for char_stories in stories:
        char_name = char_stories.char_name
        for story in char_stories.story_list:
            page_title = story.page(char_name)
            assert page_title in title_to_page, f"{story.page} is not in cached page list"
            page = title_to_page[page_title]
            save_page(page, story.story_info.full_text, "batch generate relationship story pages")
        page = title_to_page[char_stories.page]
        save_page(page, char_stories.text, "batch generate relationship story pages")


def main():
    make_relationship_stories()


if __name__ == "__main__":
    main()
