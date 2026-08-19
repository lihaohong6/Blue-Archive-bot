from dataclasses import dataclass

from pywikibot import Page
from pywikibot.pagegenerators import PreloadingGenerator

from story.story_parser import make_story_text
from story.story_utils import s, get_main_scenarios, StoryType, NavArgs, make_story_nav, \
    StoryInfo, save_story_page
from utils import save_page


def make_main_story_text(event: dict) -> StoryInfo | None:
    ids = event["FrontScenarioGroupId"] + event["BackScenarioGroupId"]
    return make_story_text(ids, story_type=StoryType.MAIN)


@dataclass
class MainStory:
    id: int
    story_info: StoryInfo
    page: str
    series: int
    volume: str
    chapter: int
    episode: int

    @property
    def volume_key(self) -> tuple[int, str]:
        return self.series, self.volume


VolumeKey = tuple[int, str]
EpisodeDict = dict[VolumeKey, dict[int, dict[int, MainStory]]]
# main_story_root_page = Page(s, f"Main Story")
volume_map: dict[int, str] = {
    100: 'F',
    114514: 'EX',
}


def get_series(scenario: dict) -> int:
    """Which main story series (act) a scenario belongs to. Series1 is act 1, Series2 act 2."""
    return 2 if scenario['SubType'] == "Series2" else 1


def get_volume(scenario: dict) -> str:
    """The volume label used in page titles, e.g. "1", "F", "EX", "P"."""
    mode = scenario['ModeType']
    if mode == 'Prologue':
        return 'P'
    if mode == 'SpecialOperation':
        return 'EX'
    if get_series(scenario) == 2:
        # act 2's Main volumes carry their displayed number separately from VolumeId
        return scenario['DisplayVolumeId']
    return str(volume_map.get(scenario['VolumeId'], scenario['VolumeId']))


def make_main_story_title(series: int, volume: str | None = None, chapter: int | None = None,
                          episode: int | None = None) -> str:
    result = "Main Story"
    if series != 1:
        result += f"/Act {series}"
    if volume is not None:
        result += f"/Volume {volume}"
    if chapter is not None:
        result += f"/Chapter {chapter}"
    if episode is not None:
        result += f"/Episode {episode}"
    return result


def generate_parent_page(all_episodes: EpisodeDict):
    """Create the volume index pages. Existing pages are left alone: they get hand-edited
    with chapter titles and intro prose, which this function cannot reproduce."""
    for series, volume in all_episodes:
        page = Page(s, make_main_story_title(series, volume))
        if page.exists():
            continue
        result = []
        for chapter in all_episodes[series, volume]:
            result.append(f"==Chapter {chapter}==")
            for episode, story in all_episodes[series, volume][chapter].items():
                result.append(f";[[{story.page}|Episode {story.episode}: {story.story_info.title}]]")
                result.append(story.story_info.summary)
        string = "\n".join(result)
        save_page(page, string, "generate navigational page")


def collect_episodes() -> tuple[EpisodeDict, dict[int, MainStory]]:
    scenarios = get_main_scenarios()
    all_episodes: EpisodeDict = {}
    id_to_story: dict[int, MainStory] = {}

    for scenario in scenarios:
        scenario_group = scenario['FrontScenarioGroupId']
        if len(scenario_group) == 0:
            scenario_group = scenario['BackScenarioGroupId']
        story_id = scenario_group[0]
        chapter = scenario['ChapterId']
        episode = scenario['EpisodeId']
        mode = scenario['ModeType']
        assert mode in {"Main", "SpecialOperation", "Prologue"}, f"Unknown mode {mode}"
        series = get_series(scenario)
        volume = get_volume(scenario)
        story_info = make_main_story_text(scenario)
        if story_info is None:
            print(make_main_story_title(series, volume, chapter, episode) + " cannot be found")
            continue
        volume_key = (series, volume)
        if volume_key not in all_episodes:
            all_episodes[volume_key] = {}
        if chapter not in all_episodes[volume_key]:
            all_episodes[volume_key][chapter] = {}
        page_title = make_main_story_title(series, volume, chapter, episode)
        story = MainStory(story_id, story_info, page_title, series, volume, chapter, episode)
        assert story_id not in id_to_story, f"Duplicate story id {story_id}"
        id_to_story[story_id] = story
        assert episode not in all_episodes[volume_key][chapter], f"Duplicate episode: {page_title}"
        all_episodes[volume_key][chapter][episode] = story

    return all_episodes, id_to_story


def make_main_story():
    all_episodes, id_to_story = collect_episodes()

    generate_nav(all_episodes, id_to_story)

    # Do not call this function unless you want to generate index pages for new volumes
    # generate_parent_page(all_episodes)

    gen = PreloadingGenerator(Page(s, story.page) for story in id_to_story.values())
    title_to_page: dict[str, Page] = dict((page.title(), page) for page in gen)

    for story_id, story in id_to_story.items():
        story_info = story.story_info
        page = title_to_page[story.page]
        save_story_page(page, story_info, summary="update main story pages")


def generate_nav(all_episodes, id_to_story: dict[int, MainStory]):
    def get_previous_episode(story_id: int) -> MainStory | None:
        story = id_to_story[story_id]
        vol = story.volume_key
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
        vol = story.volume_key
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
