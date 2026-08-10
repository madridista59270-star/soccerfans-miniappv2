from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

PROJECT = Path.cwd()
PRODUCTS_JSON = PROJECT / "public" / "products.json"
YUPOO_ROOT = Path(r"B:\yupoo_soccerfans_downloader\yupoo_images")
DEST_ROOT = PROJECT / "public" / "products"

MAX_IMAGES = 5
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
BAD_WORDS = ("size", "chart", "guide", "table", "taille", "measurement", "measure")


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def natural_key(path: Path):
    stem = path.stem
    try:
        return (0, int(stem))
    except ValueError:
        return (1, stem.lower())


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

backup = PRODUCTS_JSON.with_name("products_avant_selection_photos.json")
if not backup.exists():
    shutil.copy2(PRODUCTS_JSON, backup)
    print(f"✅ Sauvegarde créée : {backup}")

# 1) Recense les photos des albums réellement présents dans products.json.
albums: dict[str, tuple[Path, list[Path]]] = {}
all_files: list[Path] = []

for p in products:
    album_id = str(p.get("id") or "").strip()
    if not album_id:
        continue
    folder = find_album_folder(album_id)
    if not folder:
        continue
    files = sorted(
        [x for x in folder.iterdir() if x.is_file() and x.suffix.lower() in IMAGE_EXTS],
        key=natural_key,
    )
    if files:
        albums[album_id] = (folder, files)
        all_files.extend(files)

# 2) Détecte les images répétées entre plusieurs albums.
# Les guides de tailles sont généralement les mêmes fichiers dans beaucoup d'albums.
print(f"Analyse de {len(all_files)} image(s) pour éliminer les guides de tailles…")
hashes: dict[Path, str] = {}
counts = Counter()

for i, f in enumerate(all_files, 1):
    try:
        fp = sha1(f)
        hashes[f] = fp
        counts[fp] += 1
    except OSError:
        pass
    if i % 250 == 0:
        print(f"  {i}/{len(all_files)} analysées")

updated = 0
with_five = 0
missing = 0
copied = 0
filtered_common = 0

for idx, p in enumerate(products, 1):
    album_id = str(p.get("id") or "").strip()
    if album_id not in albums:
        missing += 1
        continue

    folder, files = albums[album_id]

    def is_bad_name(f: Path) -> bool:
        low = f.name.lower()
        return any(word in low for word in BAD_WORDS)

    # Priorité 1 : images non répétées et sans mot-clé de guide.
    good = [
        f for f in files
        if not is_bad_name(f)
        and counts.get(hashes.get(f, ""), 0) <= 2
    ]

    # Si pas assez, complète avec les images non répétées, même si le nom est bizarre.
    if len(good) < MAX_IMAGES:
        for f in files:
            if f in good:
                continue
            if counts.get(hashes.get(f, ""), 0) <= 2:
                good.append(f)
            if len(good) >= MAX_IMAGES:
                break

    # Dernier recours : prend des images vers la fin de l'album plutôt que les premières,
    # car les premières sont souvent les tableaux de tailles.
    if len(good) < MAX_IMAGES:
        for f in reversed(files):
            if f not in good:
                good.append(f)
            if len(good) >= MAX_IMAGES:
                break

    selected = good[:MAX_IMAGES]

    # Si on a filtré des images communes, on le compte.
    filtered_common += sum(
        1 for f in files[:MAX_IMAGES]
        if counts.get(hashes.get(f, ""), 0) > 2
    )

    if not selected:
        missing += 1
        continue

    dest_folder = DEST_ROOT / album_id
    dest_folder.mkdir(parents=True, exist_ok=True)

    # Supprime uniquement les anciennes copies de la boutique pour ce produit.
    # Les images originales Yupoo ne sont jamais touchées.
    for old in dest_folder.iterdir():
        if old.is_file() and old.suffix.lower() in IMAGE_EXTS:
            old.unlink()

    web_images = []
    for n, src in enumerate(selected, 1):
        ext = src.suffix.lower()
        dst = dest_folder / f"{n:03d}{ext}"
        shutil.copy2(src, dst)
        copied += 1
        web_images.append(f"/products/{album_id}/{dst.name}")

    p["image"] = web_images[0]
    p["images"] = web_images
    updated += 1
    if len(web_images) >= 5:
        with_five += 1

    print(f"[{idx}/{len(products)}] {p.get('name','')[:55]}")
    print("   → " + ", ".join(x.name for x in selected))

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("")
print("✅ TERMINÉ")
print(f"Produits mis à jour        : {updated}")
print(f"Produits avec 5 photos     : {with_five}")
print(f"Produits sans album trouvé : {missing}")
print(f"Photos copiées             : {copied}")
print(f"Guides/répétitions évités  : {filtered_common}")
print("")
print("➡️ Fais Ctrl + F5 sur localhost:3000 puis rouvre un produit.")
