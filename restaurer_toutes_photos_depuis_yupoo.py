from __future__ import annotations

import json
import re
import shutil
import time
from pathlib import Path

PROJECT = Path.cwd()
PRODUCTS_JSON = PROJECT / "public" / "products.json"
YUPOO_ROOT = Path(r"B:\yupoo_soccerfans_downloader\yupoo_images")
DEST_ROOT = PROJECT / "public" / "products"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def natural_key(path: Path):
    m = re.search(r"(\d+)", path.stem)
    return (int(m.group(1)) if m else 10**9, path.name.lower())


def find_album_folder(album_id: str) -> Path | None:
    matches = [p for p in YUPOO_ROOT.glob(f"{album_id}_*") if p.is_dir()]
    if matches:
        return matches[0]
    direct = YUPOO_ROOT / album_id
    return direct if direct.is_dir() else None


if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ Introuvable : {PRODUCTS_JSON}")

if not YUPOO_ROOT.exists():
    raise SystemExit(f"❌ Introuvable : {YUPOO_ROOT}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ public/products.json doit contenir une liste.")

backup = PRODUCTS_JSON.with_name("products_avant_restauration_photos.json")
if not backup.exists():
    shutil.copy2(PRODUCTS_JSON, backup)
    print(f"✅ Sauvegarde créée : {backup}")

restored_products = 0
restored_images = 0
missing_albums = 0

stamp = int(time.time())

for i, p in enumerate(products, 1):
    pid = str(p.get("id") or "").strip()
    if not pid:
        continue

    folder = find_album_folder(pid)
    if not folder:
        missing_albums += 1
        continue

    files = sorted(
        [x for x in folder.iterdir() if x.is_file() and x.suffix.lower() in IMAGE_EXTS],
        key=natural_key,
    )

    if not files:
        missing_albums += 1
        continue

    # Garde la photo principale choisie manuellement si son nom source existe encore.
    main_source = str(p.get("main_source_name") or "").strip()
    if main_source:
        matching = [x for x in files if x.name == main_source]
        if matching:
            main = matching[0]
            files = [main] + [x for x in files if x != main]

    dest = DEST_ROOT / pid
    dest.mkdir(parents=True, exist_ok=True)

    # On recrée proprement les copies de la boutique.
    for old in dest.iterdir():
        if old.is_file() and old.suffix.lower() in IMAGE_EXTS:
            try:
                old.unlink()
            except OSError:
                pass

    web_images = []
    source_names = []

    for n, src in enumerate(files, 1):
        ext = src.suffix.lower()
        dst = dest / f"photo_{n:03d}_{stamp}{ext}"
        shutil.copy2(src, dst)
        web_images.append(f"/products/{pid}/{dst.name}")
        source_names.append(src.name)
        restored_images += 1

    p["image"] = web_images[0]
    p["images"] = web_images
    p["photo_source_names"] = source_names
    if source_names:
        p["main_source_name"] = source_names[0]

    restored_products += 1

    if i % 20 == 0 or i == len(products):
        print(f"[{i}/{len(products)}] produits restaurés={restored_products} | images={restored_images}")

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("")
print("✅ RESTAURATION TERMINÉE")
print(f"Produits restaurés : {restored_products}")
print(f"Photos restaurées  : {restored_images}")
print(f"Albums introuvables: {missing_albums}")
print("")
print("🛡️ Les originaux Yupoo n'ont pas été modifiés.")
print("➡️ Fais ensuite Ctrl + F5 sur http://localhost:3000")
