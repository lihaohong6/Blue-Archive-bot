import requests

files = ["LocalizeScenarioExcelTable.json",
         "ScenarioCharacterNameExcelTable.json",
         "AcademyFavorScheduleExcelTable.json"]
files.extend(["ScenarioScriptFavor{}ExcelTable.json".format(i) for i in range (1, 10)])
files.extend(["AcademyMessanger{}ExcelTable.json".format(i) for i in range(1, 10)])
for f in files:
    url = f"https://raw.githubusercontent.com/electricgoat/ba-data/global/Excel/{f}"
    response = requests.get(url)
    if response.status_code != 404:
        text = response.text
        with open("json/" + f, "w", encoding="utf-8") as out_file:
            out_file.write(text)
            print(f"Updated {f}")
