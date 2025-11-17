from ctypes import c_ulong
from itertools import groupby

from pywikibot import Page

from story.story_parser import make_story_text
from story.story_utils import StoryType, make_story_list_nav
from utils import load_json, s, save_page, get_localized_club_name


def get_side_stories() -> dict[int, list[dict]]:
    result = load_json("ScenarioModeExcelTable.json")
    result = result['DataList']
    return dict((k, list(v))
                for k, v in groupby([row for row in result if row['ModeType'] in {"Sub"}],
                                    lambda row: row['VolumeId']))


def make_side_stories():
    all_stories = get_side_stories()
    club_story_page = Page(s, "Club Story")
    club_story_page_text = []
    for _, story_list in all_stories.items():
        story_list.sort(key=lambda k: k['EpisodeId'])
        club = story_list[0]["NeedClub"]
        assert club != "None"
        stories = [make_story_text(event["FrontScenarioGroupId"] + event["BackScenarioGroupId"], StoryType.GROUP) for event in story_list]
        root_page = Page(s, f"{club_story_page.title()}/{club}")
        localized_club = get_localized_club_name(club)
        root_page_text = [f"{{{{ClubStoryTop | name={localized_club} }}}}"]
        make_story_list_nav(stories, root_page.title() + "/")
        club_story_page_text.append(f"==[[/{club}|{localized_club}]]==")
        for index, story in enumerate(stories, 1):
            page = Page(s, f"{root_page.title()}/{index}")
            save_page(page, story.full_text, "Batch create club stories")
            root_page_text.append(f";[[{page.title()}|{story.title}]]\n{story.summary}")
            club_story_page_text.append(f"# [[{page.title()}|{story.title}]]")
        root_page_text.append("{{ClubStoryBottom}}")
        save_page(root_page, "\n".join(root_page_text), "Batch create club stories")
    save_page(club_story_page, "\n".join(club_story_page_text), "Batch create club stories")


def main():
    make_side_stories()


if __name__ == "__main__":
    main()