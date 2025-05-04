import requests
from pywikibot import FilePage

from utils import s


def make_table(chapters: list[tuple[int, str]]):
    lines = [
        """{| class="wikitable"
|+
!Episode
!Caption from official tweet
!Link
!Image"""
    ]
    chapters.sort(key=lambda x: x[0])
    for c in chapters:
        lines.append("|-")
        lines.append(f"| {c[0]} || || || [[File:{c[1]}|50px]]")
    lines.append("|}")
    print("\n".join(lines))


def main():
    data = requests.get("https://bluearchive.jp/cms/comic/list?pageIndex=1&pageNum=300&type=1").json()
    data = data["data"]['comicList']
    table_data = []
    for comic in data:
        image_url = comic['comic']
        chapter = str(comic['chapters'])
        extension = "jpg"
        if image_url.endswith('png'):
            extension = "png"
        file_title = f"Yonkoma JP {chapter.rjust(4, '0')}.{extension}"
        table_data.append((int(chapter), file_title))
        # wiki_file = FilePage(s, file_title)
        # if not wiki_file.exists():
        #     wiki_file.upload(source=image_url, comment='bulk upload JP 4-panel manga', text="[[Category:4-panel manga (JP)]]")
    make_table(table_data)


if __name__ == "__main__":
    main()