import re
import webbrowser
from pathlib import Path
from time import sleep

import bs4

import requests

cache_dir = Path("cache")
cache_dir.mkdir(exist_ok=True)


def get_thread(tid: str):
    cache_file = cache_dir / f"forum{tid}.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return f.read()
    content = requests.get(f"https://forum.nexon.com/api/v1/thread/{tid}?alias=bluearchive-en").json()['content']
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(content)
        return content


def DownloadFile(url: str, name: str | Path):
    counter = 0
    ext = url.split('.')[-1]
    while True:
        if counter == 0:
            p = Path(f"{name}.{ext}")
        else:
            p = Path(f"{name}_{counter}.{ext}")
        if not p.exists():
            break
        counter += 1
    r = requests.get(url)
    f = open(p, 'wb')
    for chunk in r.iter_content(chunk_size=512 * 1024):
        if chunk:  # filter out keep-alive new chunks
            f.write(chunk)
    f.close()
    return


def main():
    search_url = ("https://forum.nexon.com/api/v1/board/3217/threads?alias=bluearchive-en&pageNo=1&paginationType"
                  "=PAGING&pageSize=100&blockSize=5&hideType=WEB&searchKeywordType=THREAD_TITLE&keywords=Patch%20Notes")

    threads = requests.get(search_url).json()['threads']
    for t in threads:
        tid = t['threadId']
        content = get_thread(tid)
        image_counter = 0
        char_name: str | None = None
        children = bs4.BeautifulSoup(content, features="html.parser").find_all(recursive=False)
        if len(children) == 1:
            children = children[0].find_all(recursive=False)
        for child in children:
            text = child.text
            if re.search(r"\d+/\d+ ?\([MTWFS]", text) is not None:
                char_name_regex = re.search(r"([a-zA-Z ]+)\(\d★([^)]+)?\)", text)
                if char_name_regex is not None:
                    char_name = (char_name_regex.group(1) +
                                 (f"({char_name_regex.group(2)})" if len(char_name_regex.groups()) > 2 else ""))
                    char_name = char_name.strip()
                    image_counter = 4
            images = child.find_all('img')
            if len(images) > 0:
                if image_counter <= 0:
                    continue
                if char_name is not None:
                    if char_name == "":
                        char_name = "unknown"
                    DownloadFile(images[0]['src'], char_name)
            image_counter -= 1


main()
