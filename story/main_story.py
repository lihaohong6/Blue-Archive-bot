from dataclasses import dataclass

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from story.story_parser import StoryInfo, make_story_text, StoryType
from story.story_utils import s, get_story_title_and_summary, get_main_scenarios
from utils import save_json_page


def make_main_story_text(event: dict) -> StoryInfo | None:
    ids = event["FrontScenarioGroupId"] + event["BackScenarioGroupId"]
    return make_story_text(ids, story_type=StoryType.MAIN)


@dataclass
class MainStory:
    id: int
    title: str
    page: str
    volume: int
    chapter: int
    episode: int
    next_story: "MainStory" = None
    previous_story: "MainStory" = None


EpisodeDict = dict[int, dict[int, dict[int, MainStory]]]
main_story_root_page = Page(s, f"Main Story")
volume_map: dict[int, str] = {
    100: 'F'
}


def make_main_story_title(volume: int | None = None, chapter: int | None = None, episode: int | None = None) -> str:
    result = "Main Story"
    if volume is not None:
        result += f"/Volume {volume_map.get(volume, volume)}"
    if chapter is not None:
        result += f"/Chapter {chapter}"
    if episode is not None:
        result += f"/Episode {episode}"
    return result


def generate_parent_page(all_episodes: EpisodeDict):
    for volume in all_episodes:
        page = Page(s, make_main_story_title(volume))
        result = []
        for chapter in all_episodes[volume]:
            result.append(f"==Chapter {chapter}==")
            for episode, story in all_episodes[volume][chapter].items():
                result.append(f";[[{story.page}|Episode {story.episode}: {story.title}]]")
                summary = get_story_title_and_summary(story.title)[1]
                result.append(summary)
        string = "\n".join(result)
        if page.text != string:
            page.text = string
            page.save("generate navigational page")


def make_main_story():
    scenarios = get_main_scenarios()
    all_episodes: EpisodeDict = {}
    id_to_story: dict[int, MainStory] = {}
    id_to_story_info: dict[int, StoryInfo] = {}

    for scenario in scenarios:
        story_id = scenario['FrontScenarioGroupId'][0]
        volume = scenario['VolumeId']
        chapter = scenario['ChapterId']
        episode = scenario['EpisodeId']
        story_info = make_main_story_text(scenario)
        if story_info is None:
            print(make_main_story_title(volume, chapter, episode) + " cannot be found")
            continue
        id_to_story_info[story_id] = story_info
        if volume not in all_episodes:
            all_episodes[volume] = {}
        if chapter not in all_episodes[volume]:
            all_episodes[volume][chapter] = {}
        page_title = make_main_story_title(volume, chapter, episode)
        story = MainStory(story_id, story_info.title, page_title, volume, chapter, episode)
        id_to_story[story_id] = story
        assert episode not in all_episodes[volume][chapter], "Duplicate episode"
        all_episodes[volume][chapter][episode] = story

    # make_nav(all_episodes, id_to_story)

    # Do not call this function unless you want to regenerate these
    # generate_parent_page(all_episodes)

    gen = PreloadingGenerator(Page(s, story.page) for story in id_to_story.values())
    title_to_page: dict[str, Page] = dict((page.title(), page) for page in gen)

    for story_id, story in id_to_story.items():
        if story.volume != 0:
            continue
        story_info = id_to_story_info.get(story_id, None)
        if story_info is None:
            print(make_main_story_title(story.volume, story.chapter, story.episode) + " cannot be found")
            continue
        page = title_to_page[story.page]
        if page.text.strip() != story_info.text:
            page.text = story_info.text
            page.save(summary="batch create experimental main story pages")


def make_nav(all_episodes, id_to_story):
    generate_nav(all_episodes, id_to_story)
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


def generate_nav(all_episodes, id_to_story: dict[int, MainStory]):
    def get_previous_episode(story_id: int) -> MainStory | None:
        story = id_to_story[story_id]
        vol = story.volume
        chap = story.chapter
        epi = story.episode
        prev_epi = epi - 1
        if prev_epi in all_episodes[vol][chap]:
            return all_episodes[vol][chap][prev_epi]
        if prev_epi == 0:
            prev_chap = chap - 1
            if prev_chap in all_episodes[vol]:
                for i in range(100, 0, -1):
                    r = all_episodes[vol][prev_chap].get(i, None)
                    if r is not None:
                        return r
        return None

    def get_next_episode(story_id: int) -> MainStory | None:
        story = id_to_story[story_id]
        vol = story.volume
        chap = story.chapter
        epi = story.episode
        next_epi = epi + 1
        if next_epi in all_episodes[vol][chap]:
            return all_episodes[vol][chap][next_epi]
        next_chap = chap + 1
        return all_episodes[vol].get(next_chap, {}).get(1, None)

    for story in id_to_story.values():
        story.next_story = get_next_episode(story.id)
        story.previous_story = get_previous_episode(story.id)
