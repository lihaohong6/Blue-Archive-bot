import cohere
import pywikibot as pwb
from wikitextparser import parse
from wikitextparser._cell import Cell

PREAMBLE = ("You are translating Japanese text into English. "
            "Note that 先生 is a proper noun that should be translated to Sensei. 身共 is a first person pronoun that should be translated to I or me.")

co = cohere.Client(open("keys/cohere.txt", "r").read())  # This is your trial API key
s = pwb.Site()
page = pwb.Page(s, input())
parsed = parse(page.text)

for section in parsed.sections:
    if not section.title or section.title.strip().lower() != "Tactics and growth".lower():
        continue
    table = section.tables[0]
    rows = table.data(column=2)
    target_cells = table.cells(column=3)
    for row_number, original in enumerate(rows):
        cell: Cell = target_cells[row_number]
        if original.strip() == "" or row_number <= 1:
            continue
        # controls whether existing translations are overwritten or skipped
        # if cell.value.strip() != "":
        #     continue
        response = co.chat(
            model='command-r-plus',
            preamble=PREAMBLE,
            message=original,
            temperature=0.3,
            chat_history=[],
            prompt_truncation='AUTO',
            connectors=[{"id": "web-search"}]
        )
        cell.value = response.text
    print(str(section))
