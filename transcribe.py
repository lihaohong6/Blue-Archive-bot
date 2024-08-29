import sys
from pathlib import Path
import whisper
import pywikibot as pwb
from wikitextparser import parse
from wikitextparser._cell import Cell

sys.stdout.reconfigure(encoding='utf-8')

def main():
    model = whisper.load_model(name="large-v3", download_root="./models")
    print("Model loaded")
    s = pwb.Site()
    page = pwb.Page(s, input())
    parsed = parse(page.text)

    for section in parsed.sections:
        if not section.title or section.title.strip().lower() != "Tactics and growth".lower():
            continue
        table = section.tables[0]
        cells = table.cells()
        for row in cells:
            row: list[Cell]
            voice = parse(row[1].value).wikilinks
            if len(voice) == 0:
                continue
            voice_link = voice[0].target
            download_path = Path("upload/" + voice_link)
            pwb.FilePage(s, voice_link).download(download_path)
            result = model.transcribe(str(download_path), language="ja", patience=2, beam_size=5)
            target = row[2]
            target.value = result['text']
            print(target.value)
            download_path.unlink()
        print(str(section))
        break
    
if __name__ == "__main__":
    main()
    