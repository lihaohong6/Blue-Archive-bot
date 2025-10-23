import logging
import re
from dataclasses import dataclass

from pywikibot import Page
from pywikibot.pagegenerators import GeneratorFactory

from story.story_parser import make_story_text
from story.story_utils import make_story_nav, NavArgs, StoryType, StoryInfo
from utils import load_json, s, save_page


@dataclass
class Event:
    id: int
    scenario_groups: list[int]


def load_event_stories() -> list[Event]:
    table = load_json("EventContentScenarioExcelTable.json")
    table = table['DataList']
    result = []
    for d in table:
        event_content_id = d['EventContentId']
        scenario_group_ids = d['ScenarioGroupId']
        if str(scenario_group_ids[0]).endswith("5") and len(result) > 0:
            result[-1].scenario_groups.extend(scenario_group_ids)
        else:
            result.append(Event(event_content_id, scenario_group_ids))
    return result


@dataclass
class WikiEvent:
    event_page: Page
    event_id: int


def get_wiki_events() -> list[WikiEvent]:
    gen = GeneratorFactory()
    gen.handle_args(['-cat:Events', '-ns:0', '-titleregexnot:.*/.*'])
    gen = gen.getCombinedGenerator(preload=True)
    result = []

    for page in gen:
        page: Page
        event_id_match = re.search(r"OriginalId *= *(\d+)", page.text)
        if not event_id_match:
            logging.error(f"Could not find event id for page {page.title()}")
            continue
        event_id = int(event_id_match.group(1))
        result.append(WikiEvent(page, event_id))
    return result


def main():
    event_stories: dict[int, list[StoryInfo]] = {}
    for event in load_event_stories():
        if event.id not in event_stories:
            event_stories[event.id] = []
        story = make_story_text(event.scenario_groups, StoryType.EVENT)
        if story is None:
            logging.error(f"Could not parse story for event {event.id}")
            continue
        event_stories[event.id].append(story)
    event_pages = dict((e.event_id, e) for e in get_wiki_events())
    for event_id, story_list in event_stories.items():
        if event_id not in event_pages:
            logging.warning(f"Could not find event page for event id {event_id}")
            continue
        story_titles = []
        wiki_page = event_pages[event_id].event_page
        if "Valentine" in wiki_page.title():
            continue
        story_root_page_title = wiki_page.title(underscore=True) + "/Story"
        story_page_title_template = story_root_page_title + "/{}"
        for story_index, story in enumerate(story_list, 1):
            story_page_title = story_page_title_template.format(str(story_index))
            story_page = Page(s, story_page_title)
            nav_args = NavArgs()
            real_index = story_index - 1
            if real_index > 0:
                nav_args.prev_title = story_list[real_index - 1].title
                nav_args.prev_page = story_page_title_template.format(str(story_index - 1))
            if real_index < len(story_list) - 1:
                nav_args.next_title = story_list[real_index + 1].title
                nav_args.next_page = story_page_title_template.format(str(story_index + 1))
            make_story_nav(story, nav_args)
            save_page(story_page, story.full_text, summary="batch create event story page")
            story_titles.append((story_page_title, story.title))
        story_root_page = Page(s, story_root_page_title)
        root_page_text = "\n".join(f"#[[{titles[0]}|{titles[1]}]]" for index, titles in enumerate(story_titles, start=1))
        root_page_text += "<noinclude>[[Category:Event stories]]</noinclude>"
        save_page(story_root_page, root_page_text, summary="batch create event story navigation page")


if __name__ == '__main__':
    main()