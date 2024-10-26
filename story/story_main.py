import sys
from dataclasses import dataclass

from pywikibot import Page
from story.story_parser import StoryType, make_story, make_relationship_story_pages

from utils import get_character_table, load_favor_schedule, \
    save_json_page
from story.story_utils import get_main_scenarios, make_categories, \
    get_main_event, s

sys.stdout.reconfigure(encoding='utf-8')


def make_main_scenario_text(event: dict) -> str:
    ids = event["FrontScenarioGroupId"] + event["BackScenarioGroupId"]
    event_lines = []
    for event_id in ids:
        event_lines.extend(get_main_event(event_id))
    story = make_story(event_lines, StoryType.MAIN)
    result = ["{{Story/StoryTop}}",
              story.text,
              "{{Story/StoryBottom}}",
              make_categories(["Main story episodes"], story.chars, story.music)]
    return "\n".join(result)


@dataclass
class Story:
    id: int
    title: str
    page: str
    volume: str
    chapter: str
    episode: str
    next_story: "Story" = None
    previous_story: "Story" = None


def make_main_story():
    scenarios = get_main_scenarios()
    root_page = Page(s, f"Main_Story")
    all_episodes: dict[str, dict[str, dict[str, Story]]] = {}
    id_to_story: dict[int, Story] = {}
    for scenario in scenarios:
        story_id = scenario['FrontScenarioGroupId'][0]
        volume = str(scenario['VolumeId'])
        chapter = str(scenario['ChapterId'])
        episode = str(scenario['EpisodeId'])
        if volume not in all_episodes:
            all_episodes[volume] = {}
        if chapter not in all_episodes[volume]:
            all_episodes[volume][chapter] = {}
        page_title = root_page.title() + "/" + f"Volume {volume}/Chapter {chapter}/Episode {episode}"
        story = Story(story_id, "", page_title, volume, chapter, episode)
        id_to_story[story_id] = story
        assert episode not in all_episodes[volume][chapter], "Duplicate episode"
        all_episodes[volume][chapter][episode] = story

    def get_previous_episode(story_id: int) -> Story | None:
        story = id_to_story[story_id]
        vol = story.volume
        chap = story.chapter
        epi = story.episode
        prev_epi = str(int(epi) - 1)
        if prev_epi in all_episodes[vol][chap]:
            return all_episodes[vol][chap][prev_epi]
        if prev_epi == "1":
            prev_chap = str(int(chap) - 1)
            if prev_chap in all_episodes[vol]:
                for i in range(100, 0, -1):
                    r = all_episodes[vol][chap].get(str(i), None)
                    if r is not None:
                        return r
        return None

    def get_next_episode(story_id: int) -> Story | None:
        story = id_to_story[story_id]
        vol = story.volume
        chap = story.chapter
        epi = story.episode
        next_epi = str(int(epi) + 1)
        if next_epi in all_episodes[vol][chap]:
            return all_episodes[vol][chap][next_epi]
        next_chap = str(int(chap) - 1)
        return all_episodes[vol].get(next_chap, {}).get("1", None)

    for story in id_to_story.values():
        story.next_story = get_next_episode(story.id)
        story.previous_story = get_previous_episode(story.id)

    json_obj = {}
    for story in id_to_story.values():
        prev = story.previous_story
        next_story = story.next_story
        json_obj[story.page] = {
            'prev_page': prev.page if prev else '',
            'prev_title': prev.title if prev else '',
            'next_page': next_story.page if next_story else '',
            'next_title': next_story.title if next_story else '',
        }
    save_json_page("Module:Story/navigation.json", json_obj)

    for scenario in scenarios:
        story_id = scenario['FrontScenarioGroupId'][0]
        story = id_to_story[story_id]
        text = make_main_scenario_text(scenario)
        page = Page(s, story.page)
        if page.text.strip() != text:
            page.text = text
            page.save(summary="batch create experimental main story pages")
        if int(story.episode) >= 5:
            break



def make_all_relationship_story_pages():
    favor_schedule = load_favor_schedule()
    character_table = get_character_table()
    for character_id, event_list in favor_schedule.items():
        if character_id not in character_table:
            print(f"Character id {character_id} has no corresponding name.")
            continue
        try:
            char_name = character_table[character_id]
            if char_name != "Shimiko":
                continue
            make_relationship_story_pages(event_list, char_name)
            print(character_table[character_id] + " done")
        except NotImplementedError as e:
            print(e)
            print(character_table[character_id] + " failed")


def main():
    make_main_story()


if __name__ == "__main__":
    main()
