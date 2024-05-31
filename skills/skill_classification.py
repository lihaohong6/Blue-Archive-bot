from pathlib import Path

import json
import re

import pywikibot as pwb
from pywikibot.pagegenerators import GeneratorFactory

s = pwb.Site()
skill_file = Path("skills/skill_classifications.json")
f = GeneratorFactory(s)
f.handle_args(['-cat:Characters', '-ns:0'])
gen = f.getCombinedGenerator(preload=True)


def pull():
    result: dict[str, list[str]] = {}
    for page in gen:
        page: pwb.Page
        text = page.text
        classifications = []
        skill_types = re.search(r"\{\{skill types\|([a-zA-Z |-]+)}}", text, re.IGNORECASE)
        if skill_types is not None:
            classifications = skill_types.group(1).split("|")
        result[page.title()] = classifications
    json.dump(result, open(skill_file, "w"), indent=2)


def push():
    result: dict[str, list[str]] = json.load(open(skill_file, "r"))
    for page in gen:
        page: pwb.Page
        title = page.title()
        if title not in result:
            print("ERROR: " + title + " has no corresponding skill type")
            continue
        types = result[title]
        text = page.text
        type_string = "{{skill types | " + " | ".join(types) + " }}"
        text, substitutions = re.subn(r"\{\{skill types *\|[a-zA-Z- |]+}}", type_string, text, flags=re.IGNORECASE)
        assert substitutions < 2
        if substitutions == 0:
            text, substitutions = re.subn(r"^(=+ *Skills *=+)$", r"\1\n" + type_string, text, flags=re.MULTILINE)
            assert substitutions == 1
        if text == page.text:
            print("No update on " + title)
            continue
        setattr(page, "_bot_may_edit", True)
        page.text = text
        page.save(summary="update skill types", minor=False)


def make_categories():
    def make_title(t: str) -> str:
        return f"Characters with {t} skills"

    lines = open("skills/categories.txt", "r").readlines()
    skill_stack = ["" for _ in range(10)]
    for line in lines:
        line = line.rstrip()
        spacing = len(line) - len(line.lstrip())
        line = make_title(line.lstrip())
        skill_stack[spacing] = line
        parents = ["Characters by skill"]
        for i in range(0, spacing):
            parents.append(skill_stack[i])
        title = "Category:" + line
        text = "{{catnav|" + "|".join(parents) + f"|{line}" + "}}\n\n"
        text = text + f"[[Category:{parents[-1]}]]"
        page = pwb.Page(s, title)
        setattr(page, "_bot_may_edit", True)
        if page.text.strip() == text.strip():
            continue
        page.text = text
        page.save(summary="Mass update skill-related categories")


def main():
    from sys import argv
    if argv[1] == "push":
        push()
    elif argv[1] == "pull":
        pull()
    elif argv[1] == "cat":
        make_categories()


if __name__ == "__main__":
    main()
