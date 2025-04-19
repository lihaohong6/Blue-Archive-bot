from dataclasses import dataclass

from story.story_parser import make_story_text, StoryType
from utils import load_json


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


def main():
    counter = 0
    event_stories = load_event_stories()
    for event in event_stories:
        if 841 == event.id:
            story = make_story_text(event.scenario_groups, StoryType.EVENT)
            print(story.text)
            counter += 1
            if counter > 3:
                break


if __name__ == '__main__':
    main()