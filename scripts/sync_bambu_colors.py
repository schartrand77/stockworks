"""Sync Bambu Lab color mappings into the local color map file."""
from __future__ import annotations

import argparse
import io
import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, Optional
from urllib.request import Request, urlopen

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional dependency for image decoding
    Image = None


def resolve_data_dir() -> Path:
    configured_dir = os.environ.get("STOCKWORKS_DATA_DIR")
    if configured_dir:
        path = Path(configured_dir)
        if not path.is_absolute():
            return Path(__file__).resolve().parents[1] / path
        return path
    return Path(__file__).resolve().parents[1] / "data"


def resolve_output_path() -> Path:
    configured = os.environ.get("BAMBU_COLOR_MAP_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return (resolve_data_dir() / "bambu-colors.json").resolve()


def fetch_source(source: str) -> object:
    if source.startswith("http://") or source.startswith("https://"):
        request = Request(source, headers={"User-Agent": "StockWorks/1.0"})
        with urlopen(request, timeout=20) as response:
            data = response.read()
        text = data.decode("utf-8", errors="ignore")
        if "productList" in text and "self.__next_f.push" in text:
            return {"_html": text}
        return json.loads(text)
    source_path = Path(source).expanduser().resolve()
    return json.loads(source_path.read_text(encoding="utf-8"))


def extract_items(data: object) -> list[dict]:
    if isinstance(data, dict) and "_html" in data:
        return _extract_colors_from_html(data["_html"])
    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]
    if isinstance(data, dict):
        for key in ("colors", "items", "filaments", "data"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [entry for entry in candidate if isinstance(entry, dict)]
    return []


def build_color_map(entries: list[dict]) -> dict:
    colors = []
    for entry in entries:
        name = _pick_first(entry, ["name", "color", "label", "title", "color_name"])
        real_hex = _pick_first(entry, ["real_hex", "hex", "color_hex", "realHex", "colorHex"])
        bambu_hex = _pick_first(entry, ["bambu_hex", "bambuHex", "bambu_color", "bambuColor"])
        if not name or not real_hex:
            continue
        colors.append(
            {
                "name": name.strip(),
                "real_hex": real_hex.strip(),
                "bambu_hex": bambu_hex.strip() if isinstance(bambu_hex, str) and bambu_hex.strip() else None,
            }
        )
    return {
        "source": "user-supplied",
        "colors": colors,
    }


def _pick_first(entry: dict, keys: list[str]) -> str | None:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _extract_colors_from_html(html: str) -> list[dict]:
    chunk = _find_product_list_chunk(html)
    if not chunk:
        return []
    products = _parse_product_list(chunk)
    return _build_color_entries(products)


def _find_product_list_chunk(html: str) -> Optional[str]:
    chunks = re.findall(r'self.__next_f.push\\(\\[1,\"(.*?)\"\\]\\)', html, re.S)
    for chunk in chunks:
        text = chunk.encode("utf-8").decode("unicode_escape")
        if "productList" in text:
            return text
    return None


def _parse_product_list(text: str) -> list[dict]:
    idx = text.find("productList")
    if idx == -1:
        return []
    start_idx = text.find("[", idx)
    if start_idx == -1:
        return []
    decoder = json.JSONDecoder()
    try:
        products, _ = decoder.raw_decode(text[start_idx:])
    except json.JSONDecodeError:
        return []
    if isinstance(products, list):
        return [item for item in products if isinstance(item, dict)]
    return []


def _build_color_entries(products: Iterable[dict]) -> list[dict]:
    entries: Dict[str, dict] = {}
    for product in products:
        for color in product.get("colorList", []) or []:
            if not isinstance(color, dict):
                continue
            palette_url = color.get("colorPalette")
            media_files = color.get("mediaFiles") or []
            name = _infer_color_name(media_files, palette_url)
            if not name:
                continue
            bambu_hex = _fetch_palette_hex(palette_url)
            real_hex = bambu_hex
            key = name.strip().lower()
            if key not in entries or (not entries[key].get("bambu_hex") and bambu_hex):
                entries[key] = {
                    "name": name.strip(),
                    "bambu_hex": bambu_hex,
                    "real_hex": real_hex,
                    "palette_url": palette_url,
                }
    return list(entries.values())


def _infer_color_name(media_files: list, palette_url: Optional[str]) -> Optional[str]:
    candidates = []
    if isinstance(media_files, list) and media_files:
        candidates.append(media_files[0])
    if palette_url:
        candidates.append(palette_url)
    for url in candidates:
        if not isinstance(url, str):
            continue
        name = url.split("/")[-1].split("?")[0]
        name = os.path.splitext(name)[0]
        name = name.replace("_", " ").replace("-", " ")
        name = re.sub(r"\\s+", " ", name).strip()
        if name and not name.lower().startswith("rectangle"):
            return name
    return None


def _fetch_palette_hex(url: Optional[str]) -> Optional[str]:
    if not url or not isinstance(url, str) or Image is None:
        return None
    try:
        request = Request(url, headers={"User-Agent": "StockWorks/1.0"})
        with urlopen(request, timeout=20) as response:
            data = response.read()
        with Image.open(io.BytesIO(data)) as img:
            img = img.convert("RGBA").resize((1, 1), Image.BOX)
            r, g, b, a = img.getpixel((0, 0))
            if a == 0:
                return None
            return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Bambu Lab color mappings into a local JSON file.")
    parser.add_argument("--source", help="URL or JSON file path containing Bambu color data")
    parser.add_argument("--output", help="Output file path for the normalized color map")
    args = parser.parse_args()

    source = args.source or os.environ.get("BAMBU_COLOR_SOURCE")
    if not source:
        raise SystemExit("Provide --source or set BAMBU_COLOR_SOURCE to a JSON URL/file.")

    output_path = Path(args.output).expanduser().resolve() if args.output else resolve_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_data = fetch_source(source)
    if isinstance(raw_data, dict) and "_html" in raw_data and Image is None:
        raise SystemExit("Pillow is required to extract color hex values from palette images.")
    entries = extract_items(raw_data)
    if not entries:
        raise SystemExit("No color entries found in the provided source.")
    if isinstance(raw_data, dict) and "_html" in raw_data:
        color_map = {
            "source": source,
            "colors": entries,
        }
    else:
        color_map = build_color_map(entries)
    output_path.write_text(json.dumps(color_map, indent=2), encoding="utf-8")
    print(f"Wrote {len(color_map['colors'])} colors to {output_path}")


if __name__ == "__main__":
    main()
