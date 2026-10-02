"""Publish exported models to Module:ModelViewer/data.json using pywikibot.

Run from the repository root with ``python -m model_viewer.save_manifest``.
GLBs (including animations) are hosted separately at the model repo's root.
"""

import argparse
import json
from pathlib import Path
from urllib.parse import quote

MODEL_ROOT = Path(__file__).resolve().parent / "models"
MODEL_REPO = "lihaohong6/BlueArchiveModels"
MODEL_REPO_REF = "main"
CDN_BASE = f"https://cdn.jsdelivr.net/gh/{MODEL_REPO}@{MODEL_REPO_REF}/"
DATA_PAGE = "Module:ModelViewer/data.json"


def build_manifest(model_root: Path = MODEL_ROOT, base: str = CDN_BASE) -> dict:
    """Group models.json entries by character, with costumes and alternate rigs.

    Keep the exporter's wiki labels as IDs. File paths are URL-encoded, while
    labels remain readable. Animations and visibility rules live inside the GLB.
    """
    index = json.loads((model_root / "models.json").read_text(encoding="utf-8"))
    if not isinstance(index, dict) or not index:
        raise ValueError("models.json must contain exported models")
    grouped: dict[str, list[dict]] = {}
    for filename in sorted(index):
        if Path(filename).name != filename or not filename.endswith(".glb"):
            raise ValueError(f"Invalid model filename: {filename}")
        if not (model_root / filename).is_file():
            raise FileNotFoundError(model_root / filename)
        label = filename.removesuffix(".glb")
        name, separator, variant = label.partition(" (")
        skin = variant.removesuffix(")").replace(") (", " / ") if separator else ""
        grouped.setdefault(name, []).append({
            "id": label, "label": label, "skin": skin,
            "file": quote(filename, safe=""),
        })
    for models in grouped.values():
        models.sort(key=lambda model: (bool(model["skin"]), model["label"]))
    return {
        "base": base.rstrip("/") + "/",
        "characters": [{"name": name, "models": models}
                       for name, models in sorted(grouped.items())],
    }


def save_manifest(manifest: dict) -> None:
    import pywikibot

    site = pywikibot.Site()
    page = pywikibot.Page(site, DATA_PAGE)
    if not page.text or json.loads(page.text) != manifest:
        page.text = json.dumps(manifest, ensure_ascii=False, indent=4)
        page.save(summary="Update 3D model manifest", contentmodel="json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=MODEL_ROOT)
    parser.add_argument("--base", default=CDN_BASE, help="Public GLB directory URL")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without contacting the wiki")
    args = parser.parse_args()
    manifest = build_manifest(args.models, args.base)
    if args.dry_run:
        print(json.dumps(manifest, ensure_ascii=False, indent=4))
    else:
        save_manifest(manifest)


if __name__ == "__main__":
    main()
