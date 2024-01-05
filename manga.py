from pathlib import Path
import re
from bs4 import BeautifulSoup
import requests
import pywikibot as pwb

dir = Path("./manga")

def process_files() -> dict:
    # episode to intro, tweet url, and image url
    result: dict[int, tuple[str, str, str]] = {}
    for f in dir.glob("*.txt"):
        html_text = open(f, "r", encoding="utf-8").read()
        soup = BeautifulSoup(html_text, features="html.parser")
        articles = soup.find_all("article", attrs={"data-testid": "tweet"})
        text_list: list[str] = []
        image_list: list[str] = []
        url_list: list[str] = []
        for article in articles:
            tweet_text = article.find("div", attrs={"lang": "en", "data-testid": "tweetText"})
            tweet_image = article.find("div", attrs={"data-testid": "tweetPhoto"})
            tweet_url = article.find_all("a", attrs={"role": "link"})
            if tweet_text is not None and tweet_image is not None and tweet_url is not None and len(tweet_url) > 8:
                text_list.append(tweet_text.text)
                image_list.append(tweet_image.find("img")['src'])
                url_list.append(tweet_url[7]['href'])
        for i in range(len(text_list)):
            text = text_list[i]
            url = "https://twitter.com" + url_list[i].replace("/photo/1", "")
            img = image_list[i].replace("name=medium", "name=large")
            ep_search = re.search(r"Ep\. (\d+)", text)
            if ep_search is None:
                continue
            ep = int(ep_search.group(1))
            intro = re.search(r"@.*\n([^#]+)\#Blue", text).group(1).strip()
            result[ep] = (intro, url, img)
    return result

def download_images(table: dict):
    def download_file(url, file_name):
        # NOTE the stream=True parameter below
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
    
    download_dir = Path("./manga_images")
    download_dir.mkdir(exist_ok=True)
    for ep, (_, _, img) in table.items():
        download_file(img, download_dir.joinpath(f"yonkoma{ep}.jpg"))

def make_table(result):
    table = ['{| class="wikitable"', '|-', '! Episode !! Description from official tweet !! Link']
    for ep in sorted(result):
        text, link, _ = result[ep]
        table.append('|-')
        text = text.replace("\n\n", "\n").replace("\n", "<br/>")
        table.append(f'| {ep} || {text} || [{link} link]')
    table.append('|}')
    with open("result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(table))

p = pwb.Page(pwb.Site(), "4-Panel_Manga")
for regex_match in re.findall(r"\[(http[^ ]+)", p.text):
    from selenium import webdriver
    from time import sleep
    driver = webdriver.Chrome()
    driver.get(regex_match)
    sleep(1)
    open("r.html", "w", encoding="utf-8").write(driver.page_source)
    break