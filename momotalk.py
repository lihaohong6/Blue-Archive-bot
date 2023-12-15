from itertools import takewhile
import json
from pathlib import Path
import pickle
import re
import pywikibot as pwb
from pywikibot.pagegenerators import GeneratorFactory
import sys
sys.stdout.reconfigure(encoding='utf-8')

# def get_character_table() -> dict[int, str]:
#     character_json = json.load(open("json/CharacterExcelTable.json", "r", encoding="utf-8"))
#     if 'DataList' in character_json:
#         character_json = character_json['DataList']
#     converter = {
#         'default': '',
#         'swimsuit': '(Swimsuit)',
#         'Swimsuit': '(Swimsuit)',
#         'RidingSuit': '(Riding)',
#         'Casual': '(Casual)',
#         'Newyear': '(New Year)'
#     }
#     first_name_converter = {
#         'Zunko': 'Junko',
#         'Hihumi': 'Hifumi',
#         # 'Aris': 'Arisu',
#     }
#     result: dict[int, str] = {}
#     for item in character_json:
#         char_name = item['DevName']
#         if char_name.count("_") != 1:
#             continue
#         first_name, suffix = char_name.split("_")
#         char_name = first_name_converter.get(first_name, first_name) + " " + converter.get(suffix, "")
#         result[item['Id']] = char_name.strip()
#     return result


def get_character_table() -> dict[int, str]:
    path = Path("cache/char_id.pickle")
    if path.exists():
        result = pickle.load(open(path, "rb"))
    else:
        path.parent.mkdir(exist_ok=True)
        s = pwb.Site()
        gen = GeneratorFactory(s)
        gen.handle_args(["-cat:Characters"])
        gen = gen.getCombinedGenerator(preload=True)
        result = {}
        for p in gen:
            char_id = int(re.search(r"Id *= *([0-9]+)", p.text).group(1))
            char_name = re.search(r"\| Name = ([^\n]+)", p.text).group(1)
            result[char_id] = char_name
        pickle.dump(result, open(path, "wb"))
    return result


def load_momotalk() -> dict[int, list[dict]]:
    result = {}
    for i in range(0, 10):
        file_name = Path(f"json/AcademyMessanger{i}ExcelTable.json")
        if not file_name.exists():
            continue
        momotalk = json.load(open(file_name, "r", encoding="utf-8"))
        if 'DataList' in momotalk:
            momotalk = momotalk['DataList']
        for talk in momotalk:
            cid = talk['CharacterId']
            if cid not in result:
                result[cid] = []
            result[cid].append(talk)
    return result


def find_convergence_point(conversations: list[dict], options: list[dict]) -> tuple[int, list[list[int]]]:
    """
    When dialogue branches based on Sensei's choice, find out at which point the conversation
    converges to the same lines.

    Args:
        conversations (list[dict]): all lines in this conversation
        options (list[int]): a list of all possible options

    Returns:
        tuple[int, list[list[int]]]: convergence point and ids of unique lines for each options
    """
    conversation_dict: dict[int, list[dict]] = {}
    for c in conversations:
        gid = c['MessageGroupId']
        if gid not in conversation_dict:
            conversation_dict[gid] = []
        conversation_dict[gid].append(c)
    
    paths: list[list[int]] = []
    for option_index, option in enumerate(options):
        paths.append([])
        oid = option['NextGroupId']
        paths[option_index].append(oid)
        while oid in conversation_dict:
            next_id = conversation_dict[oid][-1]['NextGroupId']
            if next_id not in conversation_dict:
                break
            paths[option_index].append(next_id)
            oid = next_id
    path_sets: list[set[int]] = []
    for path in paths:
        path_set = set()
        for cid in path:
            path_set.add(cid)
        path_sets.append(path_set)
    convergence = -1
    for cid in paths[0]:
        for path_set in path_sets:
            if cid not in path_set:
                break
        else:
            convergence = cid
            break
    # assert convergence != -1, str(options)
    
    return convergence, [list(takewhile(lambda x: x != convergence, path)) for path in paths]
        
    


student_reply_group: int = 0
def make_conversation(conversation: list[dict], char_name: str, 
                      conversation_counter: int) -> str:
    result = []
    # result.append(f'<tab name="Conversation {conversation_counter}">')
    result.append(f'<span id="momotalk-{conversation_counter}"></span>')
    result.append("{{MomoTalk")
    char_name_short = char_name.split()[0]
    n = len(conversation)

    prev_group_id = -1
    i = 0
    counter = 1
    global student_reply_group
    relationship_event_found = 0
    reply_convergence = -1
    reply_group: dict[int, int] = {}
    no_favor_schedule: set[int] = set()
    while i < n:
        c = conversation[i]
        group_id = c['MessageGroupId']
        if c['MessageCondition'] == "Answer":
            # Sensei's line
            if i < n - 1 and group_id == conversation[i + 1]['MessageGroupId']:
                candidates = [c]
                while i < n - 1 and conversation[i]['MessageGroupId'] == conversation[i + 1]['MessageGroupId']:
                    i += 1
                    candidates.append(conversation[i])
                options = ''.join(f'|option{counter}_{index + 1}={c["MessageEN"]}\n' for index, c in enumerate(candidates))
                line = f"|{counter}=reply\n{options}"
                # TODO: find convergence point and create a dict labelling all groups before this convergence point
                #  for each student line, query this convergence point
                # set flags for differing student responses
                reply_convergence, reply_list = find_convergence_point(conversation, candidates)
                for index, replies in enumerate(reply_list):
                    if len(replies) > 0:
                        no_favor_schedule.add(replies[-1])
                    for reply_id in replies:
                        reply_group[reply_id] = index + 1
                if len(reply_list) > 0 and len(reply_list[-1]) > 0:
                    no_favor_schedule.remove(reply_list[-1][-1])
                student_reply_group += 1
                line += f"|group{counter}={student_reply_group}\n"
            else:
                line = f"|{counter}=sensei\n|text{counter}={c['MessageEN']}\n"
                if group_id in reply_group:
                    line += f"|group{counter}={student_reply_group}\n|option{counter}={reply_group[group_id]}\n"
        else:
            # student response
            if c['MessageType'] == 'Image':
                line = f"|{counter}=student-image\n|file{counter}={c['ImagePath'].split('/')[-1]}"
            else:
                line = f"|{counter}=student-text\n|text{counter}={c['MessageEN']}"
            if group_id != prev_group_id:
                line += f"\n|name{counter}={char_name_short}\n|profile{counter}={char_name}"
            line += "\n"
            if group_id in reply_group:
                line += f"|group{counter}={student_reply_group}\n|option{counter}={reply_group[group_id]}\n"
        # extra conditions ensure that relatioship popup does not appear twice
        if c['FavorScheduleId'] != 0 and group_id not in no_favor_schedule:
            counter += 1
            line += f"\n|{counter}=relationship\n|name{counter}={char_name_short}\n"
            relationship_event_found += 1
        result.append(line)
        prev_group_id = group_id
        i += 1
        counter += 1
    assert relationship_event_found == 1, f"For {char_name}: relationship event should occur exactly once; occurred {relationship_event_found} time(s) instead. Last group id: {group_id}"
        
    result.append("}}")
    # result.append("</tab>")
    
    return "\n".join(result)


def make_seo(student_name: str):
    return f"""{{{{#seo:
    |title={student_name} MomoTalks
    |title_mode=append
    |keywords={student_name},MomoTalk,chat,messenger,ingame,dialogue,Blue Archive,モモトーク
    |description=All MomoTalk chats with {student_name}
    |image = {student_name}.png
    |image_alt = {student_name} MomoTalks
}}}}"""


def make_character_momotalk(momotalk: list[dict], char_name: str) -> str:
    suspicion = 0
    for t in momotalk:
        if t['MessageEN'] == "" and t['MessageType'] != "Image":
            suspicion += 1
    if suspicion > 3:
        print(f"ERROR: {char_name}'s MomoTalk contains too much whitespace")
        return ""
    
    
    current = []
    # result = ["<tabs plain>"]
    result = []
    counter = 1
    global student_reply_group
    student_reply_group = 0
    
    for m in momotalk:
        if m['MessageCondition'] == 'FavorRankUp':
            if len(current) > 0:
                result.append(make_conversation(current, char_name, counter))
                counter += 1
                current = []
        current.append(m)
    result.append(make_conversation(current, char_name, counter))
    
    ## result.append("</tabs>")
    result.append("[[Category:MomoTalk]]")
    return make_seo(char_name) + "\n\n".join(result)


s = pwb.Site()
def create_momotalk_page(student_name, text):
    p = pwb.Page(s, f"{student_name}/MomoTalk")
    # if p.exists():
    #     print(f"ERROR: {student_name}/MomoTalk already exists")
    #     return
    # if "#seo" in p.text:
    #     print(f"INFO: {student_name} already contains seo info")
    #     return
    # if not pwb.Page(s, student_name).exists():
    #     print("ERROR: Cannot find base page for " + student_name)
    #     return
    if text.strip() == "":
        print(f"ERROR: text for {student_name} is empty.")
        return
    assert p.text == text
    # p.text = text
    # p.save("update with SEO tag")


def main():
    char_dict = get_character_table()
    momotalk_dict = load_momotalk()
    with open("result.txt", "w", encoding="utf-8") as out_file:
        for char_id, momotalk in momotalk_dict.items():
            if char_id not in char_dict:
                continue
            char_name = char_dict[char_id]
            char_name = char_name[0].capitalize() + char_name[1:]
            momotalk_text = make_character_momotalk(momotalk, char_name)
            # create_momotalk_page(char_name, momotalk_text)
            out_file.write(momotalk_text)
            out_file.write("\n\n")


if __name__ == "__main__":
    main()
