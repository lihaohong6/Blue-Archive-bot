from utils import get_music_dict, save_json_page

d = get_music_dict()
save_json_page("Module:StoryBGM/data.json", d)
