from pywikibot.pagegenerators import GeneratorFactory
import wikitextparser as wtp

from utils import find_template, save_json_page

gen = GeneratorFactory()
gen.handle_args(['-cat:Missions', '-ns:0'])
gen = gen.getCombinedGenerator(preload=True)

result: dict[str, list[tuple[str, str]]] = {}
for page in gen:
    parsed = wtp.parse(page.text)
    t = find_template(parsed, "MissionRewards")
    drops = []
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
        drops.append((item_name, item_prob.value.strip()))
    result[page.title()] = drops

save_json_page("Module:MissionDrops/data.json", result)
