import itertools
from dataclasses import dataclass, field

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from story.story_parser import StoryType, make_story_text, STORY_TOP, STORY_BOTTOM
from story.story_utils import s, get_story_title_and_summary
from utils import load_favor_schedule, get_character_table


@dataclass
class RelationshipStory:
    title: str
    summary: str
    text: str
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
        localization_id = event["LocalizeScenarioId"]
        event_name, event_summary = get_story_title_and_summary(localization_id)
        story = make_story_text(event['ScenarioSriptGroupId'], StoryType.RELATIONSHIP, character_name=char_name)
        if story is None:
            raise RuntimeError(f"Story of {char_name} with event {event} failed to parse")
        story = RelationshipStory(event_name, event_summary, story.text, index, favor_level)
        char_story.story_list.append(story)
        base_text.append(f"==[[/{story.sequence}|{event_name}]]==")
        base_text.append(event_summary)
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
            args: dict[str, str] = {}
            if next_story is not None:
                args.update({
                    'next_title': next_story.title,
                    'next_page': next_story.page(character_story.char_name)
                })
            if prev_story is not None:
                args.update({
                    'prev_title': prev_story.title,
                    'prev_page': prev_story.page(character_story.char_name)
                })

            def make_args() -> str:
                return " | ".join(f"{k}={v}" for k, v in args.items())

            nav_string = make_args()
            args = {
                'title': story.title,
                'summary': story.summary
            }
            title_string = make_args()
            top = STORY_TOP.replace("}}", " | " + nav_string + " | " + title_string + " }}")
            bottom = STORY_BOTTOM.replace("}}", " | " + nav_string + " }}")
            story.text = story.text.replace(STORY_TOP, top).replace(STORY_BOTTOM, bottom)

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
            page: Page = title_to_page[page_title]
            # FIXME: Every page would be touched otherwise. This is not ideal. We would need to update all stories
            #  at some point
            if page.text == "":
                page.text = story.text
                page.save("batch generate relationship story pages")
        page = title_to_page[char_stories.page]
        if page.text.strip() != char_stories.text:
            page.text = char_stories.text
            page.save("batch generate relationship story pages")


def main():
    make_relationship_stories()


if __name__ == "__main__":
    main()
