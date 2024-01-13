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


def data_download():
    files = ["LocalizeScenarioExcelTable.json",
            "ScenarioCharacterNameExcelTable.json",
            "AcademyFavorScheduleExcelTable.json",
            "ScenarioBGNameExcelTable.json",
            "BGMExcelTable.json",
            "ScenarioModeExcelTable.json"]
    files.extend(["ScenarioScriptFavor{}ExcelTable.json".format(i) for i in range (1, 10)])
    files.extend(["ScenarioScriptEvent{}ExcelTable.json".format(i) for i in range (1, 10)])
    files.extend(["ScenarioScriptMain{}ExcelTable.json".format(i) for i in range (1, 10)])
    files.extend(["AcademyMessanger{}ExcelTable.json".format(i) for i in range(1, 10)])
    download("https://raw.githubusercontent.com/electricgoat/ba-data/global/Excel/", files)


def wiki_repo_download():
    files = ["translation/LocalizeCharProfile.json"]
    download("https://raw.githubusercontent.com/electricgoat/bluearchivewiki/master/", files)
    
data_download()
wiki_repo_download()