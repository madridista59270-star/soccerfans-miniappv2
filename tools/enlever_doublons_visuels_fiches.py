from __future__ import annotations

import argparse
import json
import math
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

PROJECT = Path(r"C:\Users\guillaume\Documents\GitHub\soccerfans-miniappv2")
PUBLIC = PROJECT / "public"
PRODUCTS_JSON = PUBLIC / "products.json"

# Très strict : on veut seulement enlever les photos qui sont presque
# la même vue du même maillot.
SIMILARITY_MIN = 0.985
HIST_DIFF_MAX = 0.020
SIZE = (96, 96)

def public_file(url: str) -> Path | None:
    if not isinstance(url, str) or not url.startswith("/"):
        return None
    p = PUBLIC / url.lstrip("/")
    return p if p.exists() and p.is_file() else None

def prep(path: Path):
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(im, SIZE, method=Image.Resampling.LANCZOS)
        gray = im.convert("L")
        # Normalisation légère pour réduire l'effet exposition/contraste.
        gray = ImageOps.autocontrast(gray, cutoff=1)
        return gray, im

def pixel_similarity(a: Image.Image, b: Image.Image) -> float:
    # Similarité moyenne de pixels, 1 = identique.
    diff = ImageStat.Stat(ImageOps.autocontrast(
        Image.frombytes(
            "L",
            a.size,
            bytes(abs(x-y) for x, y in zip(a.tobytes(), b.tobytes()))
        ),
        cutoff=0
    )).mean[0]
    # ImageStat ci-dessus après autocontrast est trop agressif.
    # On calcule donc directement la MAE vraie :
    pa = a.tobytes()
    pb = b.tobytes()
    mae = sum(abs(x-y) for x, y in zip(pa, pb)) / len(pa)
    return max(0.0, 1.0 - mae/255.0)

def histogram_diff(a_rgb: Image.Image, b_rgb: Image.Image) -> float:
    ha = a_rgb.histogram()
    hb = b_rgb.histogram()
    sa = sum(ha) or 1
    sb = sum(hb) or 1
    # Normalisé par le nombre total de bins/pixels.
    return sum(abs(x/sa - y/sb) for x, y in zip(ha, hb)) / 2.0

def visually_same(path_a: Path, path_b: Path) -> tuple[bool, float, float]:
    try:
        ga, ra = prep(path_a)
        gb, rb = prep(path_b)
    except Exception:
        return False, 0.0, 1.0

    sim = pixel_similarity(ga, gb)
    hdiff = histogram_diff(ra, rb)

    same = sim >= SIMILARITY_MIN and hdiff <= HIST_DIFF_MAX
    return same, sim, hdiff

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ products.json introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ products.json doit être une liste.")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = PRODUCTS_JSON.with_name(f"products_backup_avant_doublons_visuels_{stamp}.json")
shutil.copy2(PRODUCTS_JSON, backup)

report = []
changed_products = 0
removed_refs = 0

print("🔎 Nettoyage TRÈS STRICT des doublons visuels dans chaque fiche...")
print("🛡️ Comparaison uniquement à l'intérieur du même produit.")
print("🛡️ Aucune photo originale Yupoo supprimée.")
print(f"Seuil similarité : {SIMILARITY_MIN:.3f}")

for idx, product in enumerate(products, 1):
    urls = []
    if product.get("image"):
        urls.append(product["image"])
    for u in product.get("images") or []:
        if u and u not in urls:
            urls.append(u)

    if len(urls) <= 1:
        continue

    kept_urls = []
    kept_files = []

    for url in urls:
        path = public_file(url)

        # Si fichier absent, on garde par sécurité.
        if path is None:
            kept_urls.append(url)
            kept_files.append(None)
            continue

        duplicate_of = None
        best_sim = 0.0
        best_hdiff = 1.0

        for kept_url, kept_path in zip(kept_urls, kept_files):
            if kept_path is None:
                continue

            same, sim, hdiff = visually_same(path, kept_path)
            if same:
                duplicate_of = kept_url
                best_sim = sim
                best_hdiff = hdiff
                break

        if duplicate_of:
            removed_refs += 1
            report.append({
                "product_id": product.get("id"),
                "product_name": product.get("name"),
                "removed": url,
                "kept": duplicate_of,
                "similarity": round(best_sim, 4),
                "hist_diff": round(best_hdiff, 4),
            })
        else:
            kept_urls.append(url)
            kept_files.append(path)

    if kept_urls and kept_urls != urls:
        product["image"] = kept_urls[0]
        product["images"] = kept_urls
        changed_products += 1

    if idx % 100 == 0 or idx == len(products):
        print(f"   {idx}/{len(products)} produits vérifiés")

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

report_path = PUBLIC / f"doublons_visuels_retires_{stamp}.json"
report_path.write_text(
    json.dumps({
        "changed_products": changed_products,
        "removed_refs": removed_refs,
        "thresholds": {
            "similarity_min": SIMILARITY_MIN,
            "hist_diff_max": HIST_DIFF_MAX,
        },
        "items": report,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("")
print("==================================================")
print(f"✅ Produits corrigés        : {changed_products}")
print(f"✅ Photos quasi-identiques  : {removed_refs}")
print(f"💾 Backup                   : {backup.name}")
print(f"📄 Rapport                  : {report_path.name}")
print("🛡️ Aucun original Yupoo supprimé.")
print("➡️ Fais ensuite Ctrl + F5.")
print("==================================================")
