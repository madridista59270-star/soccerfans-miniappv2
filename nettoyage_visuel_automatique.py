from __future__ import annotations

import json
import math
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

try:
    from PIL import Image
    import imagehash
except ImportError:
    raise SystemExit(
        "Modules manquants.\n"
        "Lance d'abord : python -m pip install pillow ImageHash"
    )

PROJECT = Path.cwd()
PRODUCTS_JSON = PROJECT / "public" / "products.json"
PUBLIC = PROJECT / "public"
PRODUCTS_ROOT = PUBLIC / "products"

# Réglages prudents
DUPLICATE_DISTANCE = 6       # 0 = identique ; <=6 = visuellement très proche
COMMON_DISTANCE = 5          # proximité pour modèles répétés (guides de tailles)
COMMON_MIN_PRODUCTS = 4      # même visuel présent dans au moins 4 produits = suspect
MIN_KEEP = 2                 # ne jamais laisser une fiche sans assez de photos

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ Introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ public/products.json doit contenir une liste.")


def clean_web_path(value: str) -> str:
    return urlsplit(str(value or "")).path


def local_path(web: str) -> Path:
    return PUBLIC / clean_web_path(web).lstrip("/")


def visual_hash(path: Path):
    """Combine pHash + dHash pour une comparaison visuelle robuste."""
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            return imagehash.phash(im), imagehash.dhash(im)
    except Exception:
        return None


def distance(a, b) -> int:
    if a is None or b is None:
        return 999
    # On combine les 2 distances et on garde la plus sévère.
    return max(a[0] - b[0], a[1] - b[1])


def likely_size_chart(path: Path) -> bool:
    """
    Heuristique visuelle légère :
    - beaucoup de fond blanc / clair
    - beaucoup de lignes horizontales/verticales
    Cela aide à repérer tableaux de tailles / guides.
    """
    try:
        with Image.open(path) as im:
            im = im.convert("L")
            im.thumbnail((320, 320))
            w, h = im.size
            if w < 40 or h < 40:
                return False

            px = list(im.getdata())
            bright_ratio = sum(1 for p in px if p >= 220) / len(px)

            # Différences entre pixels voisins : les tableaux ont souvent beaucoup de lignes.
            hor = 0
            ver = 0
            total_h = 0
            total_v = 0

            for y in range(h):
                row = [im.getpixel((x, y)) for x in range(w)]
                for x in range(1, w):
                    total_h += 1
                    if abs(row[x] - row[x-1]) > 65:
                        hor += 1

            for x in range(w):
                col = [im.getpixel((x, y)) for y in range(h)]
                for y in range(1, h):
                    total_v += 1
                    if abs(col[y] - col[y-1]) > 65:
                        ver += 1

            edge_ratio = (hor + ver) / max(1, total_h + total_v)

            # Réglage volontairement prudent.
            return bright_ratio > 0.50 and edge_ratio > 0.055
    except Exception:
        return False


# -------------------------------------------------------------------
# 1) Charge toutes les images réellement utilisées dans products.json
# -------------------------------------------------------------------
records = []
for pi, p in enumerate(products):
    pid = str(p.get("id") or "")
    name = str(p.get("name") or "")
    imgs = [str(x) for x in (p.get("images") or []) if x]

    for ii, web in enumerate(imgs):
        loc = local_path(web)
        if loc.exists() and loc.is_file():
            records.append({
                "product_index": pi,
                "product_id": pid,
                "product_name": name,
                "image_index": ii,
                "web": web,
                "local": loc,
                "hash": None,
            })

print(f"Analyse visuelle de {len(records)} photo(s)…")

for i, rec in enumerate(records, 1):
    rec["hash"] = visual_hash(rec["local"])
    if i % 200 == 0:
        print(f"  {i}/{len(records)} analysées")

# -------------------------------------------------------------------
# 2) Détecte les visuels communs entre plusieurs produits
#    (guides de tailles, tableaux, logos répétitifs)
# -------------------------------------------------------------------
common_suspects = set()

# Regroupement approché : on utilise des représentants.
clusters = []
for rec in records:
    h = rec["hash"]
    if h is None:
        continue

    placed = False
    for cluster in clusters:
        if distance(h, cluster["rep"]) <= COMMON_DISTANCE:
            cluster["items"].append(rec)
            placed = True
            break
    if not placed:
        clusters.append({"rep": h, "items": [rec]})

for cluster in clusters:
    product_ids = {x["product_id"] for x in cluster["items"]}
    if len(product_ids) >= COMMON_MIN_PRODUCTS:
        for rec in cluster["items"]:
            common_suspects.add((rec["product_index"], rec["image_index"]))

# -------------------------------------------------------------------
# 3) Nettoyage par produit
#    - garde la couverture en priorité
#    - enlève doublons visuels dans la même fiche
#    - enlève guides/tables visuels répétés
# -------------------------------------------------------------------
removed_total = 0
duplicate_total = 0
chart_total = 0
changed_products = 0
deleted_files = 0
report = []

for pi, p in enumerate(products):
    old_images = [str(x) for x in (p.get("images") or []) if x]
    if not old_images:
        continue

    main_clean = clean_web_path(str(p.get("image") or old_images[0]))

    # Met la principale en tête avant toute comparaison.
    ordered = sorted(
        old_images,
        key=lambda w: 0 if clean_web_path(w) == main_clean else 1
    )

    kept = []
    kept_hashes = []
    removed = []

    for web in ordered:
        loc = local_path(web)
        if not loc.exists():
            removed.append((web, "fichier introuvable"))
            continue

        h = visual_hash(loc)
        if h is None:
            kept.append(web)
            kept_hashes.append(None)
            continue

        # Doublon visuel dans la même fiche.
        is_dup = any(
            kh is not None and distance(h, kh) <= DUPLICATE_DISTANCE
            for kh in kept_hashes
        )

        if is_dup:
            removed.append((web, "doublon visuel"))
            duplicate_total += 1
            continue

        # Cherche index original pour savoir si c'est un visuel commun.
        try:
            original_index = old_images.index(web)
        except ValueError:
            original_index = -1

        is_common = (pi, original_index) in common_suspects
        is_chart = likely_size_chart(loc)

        # On retire un guide de taille si :
        # - il ressemble visuellement à un modèle répété entre plusieurs produits
        # OU
        # - l'heuristique visuelle le reconnaît comme tableau clair/textuel.
        # Mais on protège la photo principale.
        if clean_web_path(web) != main_clean and (is_common or is_chart):
            reason = "guide/tableau répété" if is_common else "guide/tableau détecté"
            removed.append((web, reason))
            chart_total += 1
            continue

        kept.append(web)
        kept_hashes.append(h)

    # Sécurité : si trop agressif, remet des images retirées jusqu'à MIN_KEEP.
    if len(kept) < MIN_KEEP:
        for web, _reason in removed[:]:
            if len(kept) >= MIN_KEEP:
                break
            if web not in kept and local_path(web).exists():
                kept.append(web)

    if not kept:
        kept = old_images[:1]

    # La première devient couverture.
    p["images"] = kept
    p["image"] = kept[0]

    if kept != old_images:
        changed_products += 1
        removed_total += len(old_images) - len(kept)

        report.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "before": len(old_images),
            "after": len(kept),
            "removed": [
                {"image": web, "reason": reason}
                for web, reason in removed
                if web not in kept
            ],
        })

        # Supprime seulement les copies de la boutique retirées.
        kept_clean = {clean_web_path(x) for x in kept}
        for web, _reason in removed:
            clean = clean_web_path(web)
            if clean in kept_clean:
                continue
            loc = local_path(web)
            try:
                root = PRODUCTS_ROOT.resolve()
                target = loc.resolve()
                if root in target.parents and target.exists():
                    target.unlink()
                    deleted_files += 1
            except OSError:
                pass

backup = PRODUCTS_JSON.with_name("products_avant_nettoyage_visuel.json")
if not backup.exists():
    shutil.copy2(PRODUCTS_JSON, backup)

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

report_path = PROJECT / "nettoyage_visuel_rapport.json"
report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("")
print("✅ NETTOYAGE VISUEL TERMINÉ")
print(f"Produits modifiés          : {changed_products}")
print(f"Photos retirées            : {removed_total}")
print(f"Doublons de maillot retirés: {duplicate_total}")
print(f"Guides/tableaux retirés    : {chart_total}")
print(f"Fichiers boutique supprimés: {deleted_files}")
print("")
print(f"Rapport : {report_path}")
print("🛡️ Les images originales Yupoo ne sont jamais supprimées.")
print("➡️ Ensuite fais Ctrl + F5 sur http://localhost:3000")
