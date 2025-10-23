from dataclasses import dataclass

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from story.story_parser import make_story_text
from story.story_utils import s, get_main_scenarios, StoryType, NavArgs, make_story_nav, \
    StoryInfo
from utils import save_page


def make_main_story_text(event: dict) -> StoryInfo | None:
    ids = event["FrontScenarioGroupId"] + event["BackScenarioGroupId"]
    return make_story_text(ids, story_type=StoryType.MAIN)


@dataclass
class MainStory:
    id: int
    story_info: StoryInfo
    page: str
    volume: int
    chapter: int
    episode: int


EpisodeDict = dict[int, dict[int, dict[int, MainStory]]]
# main_story_root_page = Page(s, f"Main Story")
volume_map: dict[int, str] = {
    100: 'F',
    114514: 'EX',
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
                result.append(f";[[{story.page}|Episode {story.episode}: {story.story_info.title}]]")
                result.append(story.story_info.summary)
        string = "\n".join(result)
        if page.text != string:
            page.text = string
            page.save("generate navigational page")


def make_main_story():
    scenarios = get_main_scenarios()
    all_episodes: EpisodeDict = {}
    id_to_story: dict[int, MainStory] = {}

    for scenario in scenarios:
        scenario_group = scenario['FrontScenarioGroupId']
        if len(scenario_group) == 0:
            continue
        story_id = scenario_group[0]
        volume = scenario['VolumeId']
        chapter = scenario['ChapterId']
        episode = scenario['EpisodeId']
        mode = scenario['ModeType']
        assert mode in {"Main", "SpecialOperation"}, f"Unknown mode {mode}"
        if mode == 'SpecialOperation':
            volume = 114514
        story_info = make_main_story_text(scenario)
        if story_info is None:
            print(make_main_story_title(volume, chapter, episode) + " cannot be found")
            continue
        if volume not in all_episodes:
            all_episodes[volume] = {}
        if chapter not in all_episodes[volume]:
            all_episodes[volume][chapter] = {}
        page_title = make_main_story_title(volume, chapter, episode)
        story = MainStory(story_id, story_info, page_title, volume, chapter, episode)
        id_to_story[story_id] = story
        assert episode not in all_episodes[volume][chapter], "Duplicate episode"
        all_episodes[volume][chapter][episode] = story

    generate_nav(all_episodes, id_to_story)

    # Do not call this function unless you want to regenerate these
    # generate_parent_page(all_episodes)

    gen = PreloadingGenerator(Page(s, story.page) for story in id_to_story.values())
    title_to_page: dict[str, Page] = dict((page.title(), page) for page in gen)

    for story_id, story in id_to_story.items():
        story_info = story.story_info
        page = title_to_page[story.page]
        save_page(page, story_info.full_text, summary="update main story pages")


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
        nav = NavArgs()
        next_story = get_next_episode(story.id)
        if next_story is not None:
            nav.next_page = next_story.page
            nav.next_title = next_story.story_info.title
        prev_story = get_previous_episode(story.id)
        if prev_story is not None:
            nav.prev_page = prev_story.page
            nav.prev_title = prev_story.story_info.title
        make_story_nav(story.story_info, nav)


def main():
    make_main_story()


if __name__ == "__main__":
    main()
