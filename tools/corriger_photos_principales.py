from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT = Path(r"C:\Users\guillaume\Documents\GitHub\soccerfans-miniappv2")
YUPOO_ROOT = Path(r"B:\yupoo_soccerfans_downloader\yupoo_images")

PRODUCTS_JSON = PROJECT / "public" / "products.json"
PUBLIC = PROJECT / "public"
COMMON_ALBUM_THRESHOLD = 5
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def all_sources_for_product(product: dict) -> list[Path]:
    aid = str(product.get("id") or product.get("source_album_id") or "").strip()
    found = []

    if aid:
        for d in YUPOO_ROOT.glob(f"{aid}_*"):
            if d.is_dir():
                found.extend(sorted(
                    [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
                    key=lambda x: x.name.lower()
                ))

    out = []
    seen = set()
    for p in found:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ products.json introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ products.json doit être une liste.")

print("🔎 Recherche des images communes EXACTES...")
print("🛡️ Aucun pHash/dHash, aucune suppression des originaux.")

product_sources = {}
hash_albums = defaultdict(set)
hash_cache = {}

for i, p in enumerate(products, 1):
    pid = str(p.get("id", ""))
    sources = all_sources_for_product(p)
    product_sources[pid] = sources

    for src in sources:
        try:
            digest = hash_cache.get(src)
            if not digest:
                digest = sha256(src)
                hash_cache[src] = digest
        except Exception:
            continue
        hash_albums[digest].add(pid)

    if i % 100 == 0 or i == len(products):
        print(f"   {i}/{len(products)} produits analysés")

common_hashes = {
    digest for digest, albums in hash_albums.items()
    if len(albums) >= COMMON_ALBUM_THRESHOLD
}

print(f"✅ Images communes exactes détectées : {len(common_hashes)}")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = PRODUCTS_JSON.with_name(f"products_backup_avant_covers_{stamp}.json")
shutil.copy2(PRODUCTS_JSON, backup)
print(f"💾 Sauvegarde : {backup}")

changed = 0
unchanged = 0
no_candidate = 0

for p in products:
    pid = str(p.get("id", ""))
    sources = product_sources.get(pid, [])
    chosen = None

    for src in sources:
        try:
            digest = hash_cache.get(src)
            if not digest:
                digest = sha256(src)
                hash_cache[src] = digest
        except Exception:
            continue

        if digest not in common_hashes:
            chosen = src
            break

    if chosen is None:
        no_candidate += 1
        continue

    dest_dir = PUBLIC / "products" / pid
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = chosen.suffix.lower() or ".jpg"
    dest = dest_dir / f"cover_auto{suffix}"

    if not dest.exists() or dest.stat().st_size != chosen.stat().st_size:
        shutil.copy2(chosen, dest)

    web = "/" + dest.relative_to(PUBLIC).as_posix()

    old_image = p.get("image", "")
    if old_image != web:
        p["image"] = web
        imgs = [x for x in (p.get("images") or []) if x != web]
        p["images"] = [web] + imgs
        p["main_source_name"] = chosen.name
        changed += 1
    else:
        unchanged += 1

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("")
print("=================================================")
print(f"✅ Covers corrigées : {changed}")
print(f"= Déjà correctes   : {unchanged}")
print(f"⚠️ Sans candidat    : {no_candidate}")
print("🛡️ Aucune photo originale Yupoo supprimée.")
print("➡️ Fais ensuite Ctrl + F5.")
print("=================================================")
