from dataclasses import dataclass, field
import json
import re
import pywikibot as pwb
from pywikibot.pagegenerators import PreloadingGenerator

@dataclass
class Stage:
    chapter: int
    stage: str
    hard: bool
    s_rank: int
    turn_count: int
    three_star_reward: int = -1
    challenge_turn_count: int = -1
    challenge_reward: list[tuple[int, int]] = field(default_factory=list)

def read_stages() -> dict[int, Stage]:
    d = dict()
    lst = json.load(open("json/CampaignStageExcelTable.json", "r"))['DataList']
    for stage in lst:
        name = stage['Name']
        if "Sub_Stage" in name or "Tutorial_Stage" in name:
            continue
        chapter = int(re.search(r"CHAPTER(\d+)_", name).group(1))
        stage_number = stage['StageNumber']
        assert stage_number == 'A' or int(stage_number) > 0
        hard = 'Hard_Main_Stage' in name
        d[stage["Id"]] = Stage(chapter, stage_number, hard, 
                               stage['StarConditionTacticRankSCount'],
                               stage["StarConditionTurnCount"])
    return d


def read_three_star(stages: dict[int, Stage]):
    lst = json.load(open("json/CampaignStageRewardExcelTable.json", "r"))['DataList']
    for reward in lst:
        group_id = reward['GroupId']
        if group_id not in stages:
            continue
        if reward['RewardTag'] != "ThreeStar":
            continue
        amount = reward['StageRewardAmount']
        stages[group_id].three_star_reward = amount


def read_min_turn(stages: dict[int, Stage]):
    lst = json.load(open("json/MissionExcelTable.json", "r"))['DataList']
    for challenge in lst:
        if challenge['Category'] != 'Challenge':
            continue
        if challenge['Description'] != "Mission_Complete_Campaign_Stage_Minimum_Turn":
            continue
        id = challenge['ChallengeStageShortcut']
        stage = stages[id]
        stage.challenge_turn_count = challenge['CompleteConditionCount']
        stage.challenge_reward = list(zip(challenge['MissionRewardParcelId'], challenge['MissionRewardAmount']))


item_mapper: dict[int, str] = {
    3: 'Pyroxene',
    10: 'Novice Activity Report',
    11: 'Normal Activity Report',
    1: 'Credits'
}


def get_item(id: int) -> str:
    if id not in item_mapper:
        print(id)
        exit(0)
    return item_mapper.get(id, str(id))


def make_template(stage: Stage):
    challenge_rewards = "<br/>".join("{{ItemCard|" + get_item(item) + f"|quantity={quantity}" + "}}" 
                                     for item, quantity in reversed(stage.challenge_reward))
    template = f"""{{{{ObjectivesTable
|Objective2 = Acquire S rank {stage.s_rank} times
|Objective3 = Clear stage within {stage.turn_count} turns
|ObjectiveReward = {{{{ItemCard|Pyroxene|quantity={stage.three_star_reward}}}}}
|Challenge = Clear stage within {stage.challenge_turn_count} turns
|ChallengeReward = {challenge_rewards}
}}}}"""
    return template


def propagate(stages: dict[int, Stage]):
    s = pwb.Site()
    d: dict[str, Stage] = dict()
    pages = []
    for stage in stages.values():
        title = f"{stage.chapter}-{stage.stage}{'H' if stage.hard else ''}"
        d[title] = stage
        page = pwb.Page(s, "Missions/" + title)
        pages.append(page)
        
    gen = PreloadingGenerator(pages)
    for page in gen:
        page: pwb.Page
        text = page.text
        if "ObjectivesTable" in text:
            continue
        mission = page.title().replace("Missions/", "")
        stage = d[mission]
        template = make_template(stage)
        section = f"==Objectives==\n{template}\n"
        text, replacements = re.subn(r"(\n==Str)", "\n" + section + r"\1", text, re.MULTILINE)
        if replacements == 0:
            text = text.replace("[[Category:Missions", section + "\n[[Category:Missions")
        setattr(page, "_bot_may_edit", True)
        page.text = text
        page.save(summary="autogenerate objectives", minor=False)


def main():
    stages = read_stages()
    read_min_turn(stages)
    read_three_star(stages)
    propagate(stages)

if __name__ == "__main__":
    main()