from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT = Path(r"C:\Users\guillaume\Documents\GitHub\soccerfans-miniappv2")
PUBLIC = PROJECT / "public"
PRODUCTS_JSON = PUBLIC / "products.json"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def public_file(url: str):
    if not isinstance(url, str) or not url.startswith("/"):
        return None
    p = PUBLIC / url.lstrip("/")
    return p if p.exists() and p.is_file() else None

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ products.json introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ products.json doit être une liste.")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = PRODUCTS_JSON.with_name(f"products_backup_avant_doublons_photos_{stamp}.json")
shutil.copy2(PRODUCTS_JSON, backup)

print("🔎 Suppression des photos en doublon dans chaque fiche produit...")
print("🛡️ Comparaison SHA-256 exacte uniquement.")
print("🛡️ Aucune photo originale Yupoo supprimée.")

products_changed = 0
duplicate_refs_removed = 0

for i, product in enumerate(products, 1):
    urls = []

    # Garde l'image principale en premier
    if product.get("image"):
        urls.append(product["image"])

    for u in product.get("images") or []:
        if u and u not in urls:
            urls.append(u)

    seen_hashes = set()
    seen_urls = set()
    keep = []

    for url in urls:
        if url in seen_urls:
            duplicate_refs_removed += 1
            continue

        seen_urls.add(url)
        path = public_file(url)

        # Si le fichier n'existe pas, on garde quand même la référence
        # pour éviter de supprimer par erreur.
        if path is None:
            keep.append(url)
            continue

        try:
            digest = sha256(path)
        except Exception:
            keep.append(url)
            continue

        if digest in seen_hashes:
            duplicate_refs_removed += 1
            continue

        seen_hashes.add(digest)
        keep.append(url)

    if not keep:
        continue

    old_images = product.get("images") or []
    old_main = product.get("image") or ""

    product["image"] = keep[0]
    product["images"] = keep

    if old_main != product["image"] or old_images != keep:
        products_changed += 1

    if i % 100 == 0 or i == len(products):
        print(f"   {i}/{len(products)} produits vérifiés")

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("")
print("==================================================")
print(f"✅ Produits corrigés          : {products_changed}")
print(f"✅ Photos doublons retirées   : {duplicate_refs_removed}")
print(f"💾 Sauvegarde                 : {backup.name}")
print("🛡️ Aucun original Yupoo supprimé.")
print("➡️ Fais ensuite Ctrl + F5.")
print("==================================================")
