import requests
from pywikibot import FilePage
from pywikibot.pagegenerators import PreloadingGenerator

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


def download_images(url: str, file_name_template: str, pad: int,
                    cat: str,
                    comment: str = "bulk upload images") -> list[tuple[int, str]]:
    data = requests.get(url).json()
    data = data["data"]['comicList']
    table_data = []
    download_requests: list[tuple[str, str]] = []
    for comic in data:
        image_url = comic['comic']
        chapter = str(comic['chapters'])
        extension = image_url.split(".")[-1]
        file_title = file_name_template.format(chapter.rjust(pad, '0'), extension)
        table_data.append((int(chapter), file_title))
        download_requests.append((image_url, file_title))
    existing_pages = dict((p.title(with_ns=False), p)
                         for p in PreloadingGenerator(FilePage(s, file_title)
                                                      for _, file_title in download_requests))
    for url, title in download_requests:
        if title in existing_pages and existing_pages[title].exists():
            continue
        wiki_file = FilePage(s, title)
        wiki_file.upload(source=url, comment=comment,
                         text=f"[[Category:{cat}]]")
    return table_data


def main():
    download_images("https://bluearchive.jp/cms/comic/list?pageIndex=1&pageNum=300&type=1",
                    "Yonkoma JP {}.{}",
                    cat="4-panel manga (JP)",
                    pad=4)
    download_images("https://bluearchive.jp/cms/comic/list?pageIndex=1&pageNum=500&type=2",
                    "Aoharu{}.{}",
                    cat="Aoharu Record images",
                    pad=3)


if __name__ == "__main__":
    main()
