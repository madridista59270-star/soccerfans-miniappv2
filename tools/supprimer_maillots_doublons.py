from __future__ import annotations

import json
import re
import shutil
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT = Path(r"C:\Users\guillaume\Documents\GitHub\soccerfans-miniappv2")
PUBLIC = PROJECT / "public"
PRODUCTS_JSON = PUBLIC / "products.json"

def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[_/\\|–—-]+", " ", value)
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def clean_title(value: str) -> str:
    """
    Nettoyage conservateur :
    - espace / ponctuation / casse
    - ne supprime PAS les infos importantes (club, saison, domicile, version...)
    """
    return normalize(value)

def product_key(product: dict) -> str:
    """
    Doublon sûr = même titre source normalisé.
    Si source_title manque, fallback sur name.
    """
    base = product.get("source_title") or product.get("name") or ""
    return clean_title(base)

def merge_unique(base: list, extra: list) -> list:
    out = []
    seen = set()
    for x in [*(base or []), *(extra or [])]:
        if not x:
            continue
        key = str(x).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(x)
    return out

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ products.json introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ products.json doit être une liste.")

print("🔎 Recherche des maillots en doublon...")
print("🛡️ Méthode sûre : même titre produit normalisé uniquement.")
print("🛡️ Les photos des doublons seront fusionnées dans le produit conservé.")

groups = defaultdict(list)
for p in products:
    if not isinstance(p, dict):
        continue
    key = product_key(p)
    if key:
        groups[key].append(p)

duplicate_groups = {
    key: items
    for key, items in groups.items()
    if len(items) > 1
}

print(f"✅ Groupes de doublons détectés : {len(duplicate_groups)}")
print(f"✅ Produits concernés : {sum(len(v) for v in duplicate_groups.values())}")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = PRODUCTS_JSON.with_name(f"products_backup_avant_doublons_{stamp}.json")
shutil.copy2(PRODUCTS_JSON, backup)
print(f"💾 Sauvegarde : {backup.name}")

kept = []
seen_keys = set()
removed = []
merged_photo_count = 0

for p in products:
    key = product_key(p)

    # Produit unique
    if key not in duplicate_groups:
        kept.append(p)
        continue

    # Premier produit du groupe = produit conservé
    if key not in seen_keys:
        group = duplicate_groups[key]
        master = dict(group[0])

        merged_images = []
        merged_source_names = []

        # On conserve la meilleure cover déjà définie sur le premier,
        # puis on fusionne toutes les photos uniques des doublons.
        for item in group:
            merged_images = merge_unique(merged_images, item.get("images") or [])
            merged_source_names = merge_unique(
                merged_source_names,
                item.get("photo_source_names") or []
            )

        if master.get("image"):
            merged_images = merge_unique([master["image"]], merged_images)

        master["images"] = merged_images
        if merged_images:
            master["image"] = merged_images[0]

        if merged_source_names:
            master["photo_source_names"] = merged_source_names
            if not master.get("main_source_name"):
                master["main_source_name"] = merged_source_names[0]

        master["merged_duplicate_count"] = len(group)
        master["merged_duplicate_ids"] = [
            str(x.get("id", "")) for x in group if x.get("id")
        ]

        merged_photo_count += max(0, len(merged_images) - len(group[0].get("images") or []))

        kept.append(master)
        seen_keys.add(key)

        # Tous sauf le master sont retirés du catalogue.
        for dup in group[1:]:
            removed.append({
                "id": dup.get("id"),
                "name": dup.get("name"),
                "source_title": dup.get("source_title"),
                "kept_id": master.get("id"),
            })

    # Les autres membres du groupe ne sont pas ajoutés.

report = {
    "before": len(products),
    "after": len(kept),
    "removed": len(removed),
    "duplicate_groups": len(duplicate_groups),
    "merged_extra_photos": merged_photo_count,
    "removed_products": removed,
}

PRODUCTS_JSON.write_text(
    json.dumps(kept, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

report_path = PUBLIC / f"doublons_supprimes_{stamp}.json"
report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("")
print("==================================================")
print(f"Produits avant          : {len(products)}")
print(f"Produits après          : {len(kept)}")
print(f"✅ Doublons retirés      : {len(removed)}")
print(f"✅ Groupes fusionnés     : {len(duplicate_groups)}")
print(f"✅ Photos uniques ajoutées: {merged_photo_count}")
print(f"💾 Rapport               : {report_path.name}")
print("🛡️ Aucun fichier photo original n'a été supprimé.")
print("➡️ Fais Ctrl + F5 sur le site.")
print("==================================================")
