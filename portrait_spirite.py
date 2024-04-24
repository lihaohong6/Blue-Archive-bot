from pathlib import Path
import subprocess
import requests
import json
import sys

dino_path = Path("../GroundingDINO")
if not dino_path.exists():
    raise Exception("Please ensure GroundingDINO is intalled and that the path points to it.")
sys.path.insert(1, str(dino_path.absolute()))

source_path = Path("../ba-spinecharacters")


# def download():
#     from pywikibot import FilePage, Site
#     from pywikibot.pagegenerators import GeneratorFactory
    
#     def download_file(url):
#         from urllib.parse import unquote
#         local_filename = path.joinpath(unquote(url.split('/')[-1]))
#         # NOTE the stream=True parameter below
#         with requests.get(url, stream=True) as r:
#             r.raise_for_status()
#             with open(local_filename, 'wb') as f:
#                 for chunk in r.iter_content(chunk_size=8192): 
#                     # If you have chunk encoded response uncomment if
#                     # and set chunk_size parameter to None.
#                     #if chunk: 
#                     f.write(chunk)
#         return local_filename
    
#     s = Site()
#     gen = GeneratorFactory(s)
#     gen.handle_args(['-category:Character sprites', '-ns:File', '-titleregex:00'])
#     gen = gen.getCombinedGenerator(preload=True)
#     for file in gen:
#         file: FilePage
#         url = file.get_file_url()
#         download_file(url)


result_file = Path("cache/seg-result.json")

def predict():
    from groundingdino.util.inference import load_model, load_image, predict, annotate
    import cv2
    model = load_model(str(dino_path.joinpath("groundingdino/config/GroundingDINO_SwinT_OGC.py")), str(dino_path.joinpath("weights/groundingdino_swint_ogc.pth")))
    model = model.to('cuda:0')
    TEXT_PROMPT = "face"
    BOX_TRESHOLD = 0.25
    TEXT_TRESHOLD = 0.25
    
    result: dict[str, list[float]] = {}

    for character_path in source_path.iterdir():
        character_name = character_path.name
        image_path = character_path.joinpath(character_name + "_00.png")
        if not image_path.exists():
            image_path = character_path.joinpath(character_name + "_01.png")
        assert image_path.exists(), character_name
        image_source, image = load_image(image_path)
        boxes, logits, phrases = predict(
            model=model,
            image=image,
            caption=TEXT_PROMPT,
            box_threshold=BOX_TRESHOLD,
            text_threshold=TEXT_TRESHOLD
        )
        # annotated_frame = annotate(image_source=image_source, boxes=boxes, logits=logits, phrases=phrases)
        # cv2.imwrite(str(out_path.joinpath(image_path.name)), annotated_frame)
        max_index = logits.argmax().item()
        center_x, center_y, _, _ = boxes[max_index]
        center_x, center_y = center_x.item(), center_y.item()
        height, width, _ = image_source.shape
        # print("|" + file_name + f"={width},{height},{center_x},{center_y}")
        result[character_name] =[width, height, center_x, center_y]
    
    with open(result_file, "w") as f:
        json.dump(result, f)
        
# def process():
#     result: dict = json.load(open(result_file, "r"))
#     for i in range(0, 4):
#         print("{{#switch:{{{2|}}}")
#         for k, v in result.items():
#             print(f"|{k}={v[i]}")
#         print("}}")
        
# def process2():
#     result: dict = json.load(open(result_file, "r"))
#     multiplier = 4.2
#     for k, v in result.items():
#         k: str
#         width, height, x, y = v
#         x = x.item()
#         y = y.item()
#         style = f".story-image-{k.replace('_00.png', '').replace('(', '_').replace(')', '_')} {{ " \
#                 f"margin-left: -{round(max(0, width / multiplier * x - 29), 2)}px; " \
#                 f"margin-top: -{round(max(0, height / multiplier * y - 29), 2)}px " \
#                 "}"
#         print(style)

filter = {}

def crop_batch():
    result: dict = json.load(open(result_file, "r"))
    manual: dict = {}
    for k, v in manual.items():
        result[k] = v
    portrait_width, portrait_height = 300, 300
    for k, v in result.items():
        if len(filter) > 0:
            if k not in filter:
                continue
            print(f"Processing {k}")
        width, height, center_x, center_y = v
        center_x, center_y = width * center_x, height * center_y
        top_left = [int(round(x)) for x in (center_x - portrait_width / 2, center_y - portrait_height / 2)]
        top_left = [f"+{x}" if x >= 0 else f"{x}" for x in top_left]
        print(f'mogrify -crop {portrait_width}x{portrait_height}{top_left[0]}{top_left[1]} "{k}/{k}_??.png"')

def merge_batch():
    out_path = Path("./sprites")
    out_path.mkdir(exist_ok=True)
    sprite_path = Path("../ba-spinecharacters2")
    for character_path in sprite_path.iterdir():
        char_name = character_path.name
        if len(filter) > 0:
            if char_name not in filter:
                continue
            print(f"Processing {char_name}")
        files = [str(p) for p in character_path.glob("*.png")]
        _ = subprocess.run(['magick', *files, '+append', f"{out_path}/{char_name}_Sprite_Sheet.png"], shell=True)
        
merge_batch()
