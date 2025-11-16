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
    event_content_id: int
    scenario_groups: list[int]


def load_valentine_meetups() -> list[int]:
    table = load_json("EventContentScenarioExcelTable.json")
    table = table['DataList']
    result: list[int] = []
    for d in table:
        scenario_group_ids = d['ScenarioGroupId']
        is_meetup = d['IsMeetup']
        if not is_meetup:
            continue
        assert len(scenario_group_ids) == 1
        result.append(scenario_group_ids[0])
    return result


def load_event_stories() -> list[Event]:
    table = load_json("EventContentScenarioExcelTable.json")
    table = table['DataList']
    result: list[Event] = []
    for d in table:
        event_content_id = d['EventContentId']
        scenario_group_ids = d['ScenarioGroupId']
        is_meetup = d['IsMeetup']
        # Process Valentine meetups separately
        if is_meetup:
            continue
        append = False
        if str(scenario_group_ids[0]).endswith("5") and len(result) > 0 and result[-1].event_content_id == event_content_id:
            # If they are the same event and the diff is 5, we have a battle
            if result[-1].scenario_groups[-1] - scenario_group_ids[0] == -5:
                append = True
        if append:
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


def make_event_stories():
    event_stories: dict[int, list[StoryInfo]] = {}
    for event in load_event_stories():
        if event.event_content_id not in event_stories:
            event_stories[event.event_content_id] = []
        story = make_story_text(event.scenario_groups, StoryType.EVENT)
        if story is None:
            logging.error(f"Could not parse story for event {event.event_content_id}")
            continue
        event_stories[event.event_content_id].append(story)
    event_pages = dict((e.event_id, e) for e in get_wiki_events())
    for event_id, story_list in event_stories.items():
        if event_id not in event_pages:
            logging.warning(f"Could not find event page for event id {event_id}")
            continue
        story_titles = []
        wiki_page = event_pages[event_id].event_page
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
        # There's some special navigation for Valentine stories. Do not touch this page.
        if "♡" in story_root_page_title and "Valentine" in story_root_page_title:
            continue
        story_root_page = Page(s, story_root_page_title)
        root_page_text = "<noinclude>{{EventStoryTop}}</noinclude>\n"
        root_page_text += "\n".join(
            f"#[[{titles[0]}|{titles[1]}]]" for index, titles in enumerate(story_titles, start=1))
        root_page_text += "<noinclude>[[Category:Event stories]]</noinclude>"
        save_page(story_root_page, root_page_text, summary="batch create event story navigation page")


def make_valentine_stories():
    meetups = load_valentine_meetups()
    name_to_story: dict[str, StoryInfo] = {}
    for scenario_group_id in meetups:
        story = make_story_text(scenario_group_id, StoryType.EVENT)
        # The most frequently appearing character is probably the one we're looking for
        char_name = list(sorted(story.chars.items(), key=lambda item: item[1], reverse=True))[0][0]
        name_to_story[char_name] = story
    root_page = Page(s, "Happy Schale ♡ Valentine patrol/Story")
    assert root_page.exists() and not root_page.isRedirectPage()
    story_list = []
    for char_name, story in name_to_story.items():
        page = Page(s, root_page.title() + "/" + char_name)
        save_page(page, story.full_text, summary="valentine character dating story page")
        story_list.append(f"* [[{page.title()}|{char_name}: {story.title}]]")
    # page = Page(s, "Happy Schale ♡ Valentine patrol/Dates")
    # save_page(page, "\n".join(story_list), summary="valentine dating stories page")


def main():
    make_event_stories()
    # make_valentine_stories()


if __name__ == '__main__':
    main()