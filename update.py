from pathlib import Path
import requests


def download(base: str, files: list[str]):
    for f in files:
        url = base + f
        response = requests.get(url)
        f_name = f.split("/")[-1]
        if response.status_code != 404:
            text = response.text
            with open("json/" + f_name, "w", encoding="utf-8") as out_file:
                out_file.write(text)
                print(f"Updated {f_name}")
        else:
            print(f"Skipped {f}")


def data_download():
    files = ["AcademyFavorScheduleExcelTable.json",
             "CampaignStageExcelTable.json",
             "MissionExcelTable.json",
             "CampaignStageRewardExcelTable.json"]
    files.extend(["AcademyMessanger{}ExcelTable.json".format(i) for i in range(1, 10)])
    download("https://raw.githubusercontent.com/electricgoat/ba-data/global/Excel/", files)


def db_download():
    files = ["ScenarioBGNameExcelTable.json",
             "ScenarioBGName_GlobalExcelTable.json",
             "BGMExcelTable.json",
             "LocalizeExcelTable.json",
             "ScenarioCharacterNameExcelTable.json",
             "ScenarioModeExcelTable.json",
             ]
    files.extend(["ScenarioScriptExcelTable{}.json".format(i) for i in range(1, 5)])
    download("https://raw.githubusercontent.com/electricgoat/ba-data/global/DB/", files)


def wiki_repo_download():
    files = ["translation/" + s for s in ["LocalizeCharProfile.json", "devname_map.json", "devname_map_aux.json"]]
    download("https://raw.githubusercontent.com/electricgoat/bluearchivewiki/master/", files)


Path("json").mkdir(exist_ok=True)
data_download()
db_download()
wiki_repo_download()
