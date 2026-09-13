"""Local caches for LLM-assisted character introduction writing.

Produces two artifacts under cache/:
- cache/story/*.txt: clean `Speaker: text` transcripts of story pages (one per episode).
- cache/character_story_index.json: character name -> list of {page, type, lines},
  letting a later drafting step look up which stories to read for a given character
  without rescanning the whole story corpus.

`pair_story_pages()` reads those caches back to answer the follow-up question a
Relationships section needs: which episodes are about *these two* characters together.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from pywikibot.pagegenerators import GeneratorFactory
from wikitextparser import parse

from story.story_parser import story_type_to_cat
from story.story_utils import StoryType
from utils import s, find_template

STORY_TYPE_LABELS = {
    StoryType.MAIN: "main",
    StoryType.EVENT: "event",
    StoryType.GROUP: "club",
    StoryType.RELATIONSHIP: "relationship",
}
CATEGORY_LABELS = {story_type_to_cat(t): label for t, label in STORY_TYPE_LABELS.items()}


def _fetch_story_pages(category: str) -> list[tuple[str, str]]:
    gen = GeneratorFactory(s)
    gen.handle_args([f"-cat:{category}"])
    gen = gen.getCombinedGenerator(preload=True)
    pages = list((page.title(), page.text) for page in gen)
    pages.sort(key=lambda p: p[0])
    return pages


def _dialogue_lines(text: str) -> list[str]:
    """Extract `Speaker: text` entries from a story page's `student-text` rows."""
    lines: list[str] = []
    whitelist: set[str] = set()
    for line in text.splitlines():
        m = re.search(r"\|(\d+)=(student-text)", line)
        if m:
            whitelist.add(m.group(1))
            continue
        m = re.search(r"\|(?P<type>text|name)(?P<num>\d+)=(?P<text>.+)", line)
        if m is not None and m.group("num") in whitelist:
            if m.group("type") == "text":
                if lines:
                    lines[-1] += m.group("text")
            else:
                lines.append(m.group("text") + ": ")
    return lines


def _story_title(text: str) -> str:
    parsed = parse(text)
    top = find_template(parsed, "Story/StoryTop")
    if top is None:
        return ""
    title_arg = top.get_arg("title")
    return title_arg.value if title_arg is not None else ""


def story_llm(categories: list[str] | None = None) -> None:
    """Dump `Speaker: text` transcripts for story pages into cache/story/*.txt."""
    if categories is None:
        categories = list(CATEGORY_LABELS)
    out_dir = Path("cache/story")
    out_dir.mkdir(parents=True, exist_ok=True)
    for category in categories:
        for title, text in _fetch_story_pages(category):
            content = [f"Page: {title}\nTitle: {_story_title(text)}", *_dialogue_lines(text), "\n"]
            with open(out_dir / f"{title.replace('/', ' ')}.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(content))


def build_character_story_index(categories: dict[str, str] | None = None) -> dict[str, list[dict]]:
    """Map character name -> [{page, type, lines}], sorted by lines descending, and
    persist to cache/character_story_index.json."""
    if categories is None:
        categories = CATEGORY_LABELS
    index: dict[str, list[dict]] = defaultdict(list)
    for category, label in categories.items():
        for title, text in _fetch_story_pages(category):
            counts: dict[str, int] = {}
            for entry in _dialogue_lines(text):
                m = re.match(r"^([^:]+): ", entry)
                if m:
                    counts[m.group(1)] = counts.get(m.group(1), 0) + 1
            for speaker, lines in counts.items():
                index[speaker].append({"page": title, "type": label, "lines": lines})
    for entries in index.values():
        entries.sort(key=lambda e: e["lines"], reverse=True)
    out_index = dict(sorted(index.items()))
    with open("cache/character_story_index.json", "w", encoding="utf-8") as f:
        json.dump(out_index, f, ensure_ascii=False, indent=2)
    return out_index


def pair_story_pages(a: str, b: str) -> list[dict]:
    """Episodes worth reading for the `a`-`b` relationship, most relevant first.

    Scans the cache/story/*.txt transcripts for every episode where both names show up,
    either as a speaker or inside someone's dialogue. Returns
    [{page, title, a_lines, b_lines, a_mentions, b_mentions}], where `*_lines` counts
    spoken lines and `*_mentions` counts how often the name is said out loud — an episode
    where one of the two never appears on screen but is talked about at length is still
    part of the relationship, and the per-character story index can't surface those.

    Ordering puts episodes where both speak first (by combined line count), then
    episodes where only one is present, since those are usually a character explaining
    the relationship to someone else.
    """
    results: list[dict] = []
    for path in sorted(Path("cache/story").glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        if a not in text or b not in text:
            continue
        lines = text.splitlines()
        page = lines[0].removeprefix("Page: ") if lines else path.stem
        title = lines[1].removeprefix("Title: ") if len(lines) > 1 else ""
        entry = {"page": page, "title": title}
        for name, key in ((a, "a"), (b, "b")):
            spoken = [line for line in lines[2:] if line.startswith(f"{name}: ")]
            entry[f"{key}_lines"] = len(spoken)
            entry[f"{key}_mentions"] = sum(
                line.partition(": ")[2].count(name) for line in lines[2:]
            )
        results.append(entry)
    results.sort(
        key=lambda e: (
            bool(e["a_lines"]) and bool(e["b_lines"]),
            e["a_lines"] + e["b_lines"],
            e["a_mentions"] + e["b_mentions"],
        ),
        reverse=True,
    )
    return results


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "pair":
        for e in pair_story_pages(sys.argv[2], sys.argv[3]):
            print(
                f"{e['a_lines']:4d} {e['b_lines']:4d} lines | "
                f"{e['a_mentions']:3d} {e['b_mentions']:3d} mentions | "
                f"{e['page']} ({e['title']})"
            )
    else:
        story_llm()
        build_character_story_index()
