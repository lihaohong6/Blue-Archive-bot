import re

from pywikibot.pagegenerators import GeneratorFactory
import wikitextparser as wtp

from utils import find_template, save_json_page

def update_mission_drops():
    gen = GeneratorFactory()
    gen.handle_args(['-cat:Missions', '-ns:0'])
    gen = gen.getCombinedGenerator(preload=True)

    result: list[dict] = []
    for page in gen:
        parsed = wtp.parse(page.text)
        t = find_template(parsed, "MissionRewards")
        drops = {}
        for arg in t.arguments:
            arg_name = arg.name.strip()
            # Find all template arguments that contain Main or Other. Do not include Prob or Amount args.
            if all(k not in arg_name for k in ['Main', 'Other']) or any(k in arg_name for k in ['Prob', 'Amount']):
                continue
            item_name = arg.value.strip()
            item_prob = t.get_arg(arg.name.rstrip() + "Prob ")
            if item_prob is None:
                # Each item should have an accompanying Prob or Amount.
                assert \
                    t.get_arg(arg.name.rstrip() + "Amount ") is not None,\
                    f"On {page.title()}, arg {arg.name} has not corresponding prob or amount"
                continue
            item_prob = item_prob.value.strip()
            if item_name not in drops:
                drops[item_name] = []
            drops[item_name].append(item_prob)
        result.append({
            'mission': page.title(),
            'drops': drops
        })

    save_json_page("Module:MissionDrops/data.json", result)


def get_template_arg(arg_name: str, text: str):
    m = re.search(rf"{arg_name} *= *(.+)\n", text)
    if m is None:
        return None
    return m.group(1).strip()


def generate_furniture_interactions():
    gen = GeneratorFactory()
    gen.handle_args(['-cat:Furniture', '-ns:0'])
    gen = gen.getCombinedGenerator(preload=True)
    result: dict[str, list[str]] = {}
    for page in gen:
        m = get_template_arg("CharacterInteraction", page.text)
        if m is None:
            continue
        icon = get_template_arg("Icon", page.text)
        furniture_name = page.title().split("/")[-1]
        char_list = m.split(",")
        for char_name in char_list:
            if char_name is None or char_name.strip() == "":
                continue
            result[char_name] = [furniture_name, icon]
    save_json_page("Module:CharacterCafeInteraction/data.json", result)


update_mission_drops()