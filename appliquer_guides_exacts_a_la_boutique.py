from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

PROJECT = Path.cwd()
PRODUCTS_JSON = PROJECT / "public" / "products.json"
PUBLIC = PROJECT / "public"
PRODUCTS_ROOT = PUBLIC / "products"
QUARANTINE = PROJECT / "guides_quarantine_exact"

# Un guide doit être EXACTEMENT le même fichier dans au moins 5 produits
GUIDE_MIN_PRODUCTS = 5


def clean_web_path(value: str) -> str:
    return urlsplit(str(value or "")).path


def local_path(web: str) -> Path:
    return PUBLIC / clean_web_path(web).lstrip("/")


def sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def looks_like_size_guide(path: Path) -> bool:
    """
    Détection prudente :
    image très claire/neutre + beaucoup de petits contrastes de texte/tableau.
    Le hash exact inter-produits reste la condition principale.
    """
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((300, 300))
            w, h = im.size
            if w < 60 or h < 60:
                return False

            pixels = list(im.getdata())
            total = max(1, len(pixels))

            white = 0
            neutral_bright = 0

            for r, g, b in pixels:
                if r >= 220 and g >= 220 and b >= 220:
                    white += 1
                mx = max(r, g, b)
                mn = min(r, g, b)
                if ((r + g + b) / 3) >= 190 and (mx - mn) <= 35:
                    neutral_bright += 1

            white_ratio = white / total
            neutral_ratio = neutral_bright / total

            gray = im.convert("L")
            edges = 0
            checks = 0

            for y in range(0, h, 3):
                for x in range(3, w, 3):
                    checks += 1
                    if abs(gray.getpixel((x, y)) - gray.getpixel((x - 3, y))) > 45:
                        edges += 1

            for x in range(0, w, 3):
                for y in range(3, h, 3):
                    checks += 1
                    if abs(gray.getpixel((x, y)) - gray.getpixel((x, y - 3))) > 45:
                        edges += 1

            edge_ratio = edges / max(1, checks)

            return (
                (white_ratio >= 0.58 and edge_ratio >= 0.018)
                or
                (neutral_ratio >= 0.68 and edge_ratio >= 0.020)
            )
    except Exception:
        return False


if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ Introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ public/products.json doit contenir une liste.")

backup = PRODUCTS_JSON.with_name("products_avant_suppression_guides_exacts.json")
if not backup.exists():
    shutil.copy2(PRODUCTS_JSON, backup)
    print(f"✅ Sauvegarde créée : {backup}")

# ------------------------------------------------------------
# 1) Recense les hashes EXACTS dans les produits de la boutique
# ------------------------------------------------------------
hash_products = defaultdict(set)
hash_sample = {}

records = []

for pi, p in enumerate(products):
    pid = str(p.get("id") or "")
    images = [str(x) for x in (p.get("images") or []) if x]

    for ii, web in enumerate(images):
        loc = local_path(web)
        if not loc.exists() or not loc.is_file():
            continue

        digest = sha256(loc)
        if not digest:
            continue

        hash_products[digest].add(pid)
        hash_sample.setdefault(digest, loc)
        records.append((pi, ii, web, loc, digest))

print(f"Images boutique analysées : {len(records)}")

# ------------------------------------------------------------
# 2) Guide = même hash exact dans >=5 produits + aspect tableau
# ------------------------------------------------------------
guide_hashes = set()

for digest, product_ids in hash_products.items():
    if len(product_ids) < GUIDE_MIN_PRODUCTS:
        continue

    sample = hash_sample[digest]
    if looks_like_size_guide(sample):
        guide_hashes.add(digest)

print(f"Guides exacts détectés : {len(guide_hashes)}")

# ------------------------------------------------------------
# 3) Retire ces guides du products.json courant
# ------------------------------------------------------------
QUARANTINE.mkdir(parents=True, exist_ok=True)

changed_products = 0
removed_guides = 0
moved_files = 0

for p in products:
    pid = str(p.get("id") or "")
    old_images = [str(x) for x in (p.get("images") or []) if x]
    if not old_images:
        continue

    kept = []
    removed = []

    for web in old_images:
        loc = local_path(web)
        digest = sha256(loc) if loc.exists() else None

        if digest and digest in guide_hashes:
            removed.append((web, loc))
            removed_guides += 1
        else:
            kept.append(web)

    # Sécurité : ne jamais vider complètement une fiche
    if not kept and old_images:
        kept = [old_images[0]]
        removed = [(w, l) for (w, l) in removed if w != old_images[0]]

    if kept != old_images:
        changed_products += 1
        p["images"] = kept

        main = clean_web_path(str(p.get("image") or ""))
        kept_clean = [clean_web_path(x) for x in kept]

        if main not in kept_clean:
            p["image"] = kept[0]

        # Déplace les copies retirées dans une quarantaine
        qdir = QUARANTINE / pid
        qdir.mkdir(parents=True, exist_ok=True)

        for web, loc in removed:
            try:
                if loc.exists() and PRODUCTS_ROOT.resolve() in loc.resolve().parents:
                    dst = qdir / loc.name
                    if dst.exists():
                        dst = qdir / f"{loc.stem}_{moved_files}{loc.suffix}"
                    shutil.move(str(loc), str(dst))
                    moved_files += 1
            except OSError:
                pass

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("")
print("✅ GUIDES EXACTS RETIRÉS DE LA BOUTIQUE")
print(f"Produits modifiés       : {changed_products}")
print(f"Guides retirés          : {removed_guides}")
print(f"Fichiers en quarantaine : {moved_files}")
print(f"Quarantaine             : {QUARANTINE}")
print("")
print("🛡️ Aucune photo originale Yupoo n'a été supprimée.")
print("➡️ Fais Ctrl + F5 sur http://localhost:3000")
