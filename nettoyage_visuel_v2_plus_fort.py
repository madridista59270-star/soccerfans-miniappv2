from __future__ import annotations

import json
import shutil
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image
import imagehash

PROJECT = Path.cwd()
PRODUCTS_JSON = PROJECT / "public" / "products.json"
PUBLIC = PROJECT / "public"
PRODUCTS_ROOT = PUBLIC / "products"
QUARANTINE = PROJECT / "photo_quarantine_v2"

# Détection renforcée mais limitée à la fiche d'un même produit.
DUPLICATE_DISTANCE = 7

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ Introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ public/products.json doit contenir une liste.")

backup = PRODUCTS_JSON.with_name("products_avant_nettoyage_v2.json")
if not backup.exists():
    shutil.copy2(PRODUCTS_JSON, backup)

QUARANTINE.mkdir(parents=True, exist_ok=True)


def clean_web_path(v: str) -> str:
    return urlsplit(str(v or "")).path


def local_path(web: str) -> Path:
    return PUBLIC / clean_web_path(web).lstrip("/")


def hashes(path: Path):
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            return imagehash.phash(im), imagehash.dhash(im)
    except Exception:
        return None


def dist(a, b) -> int:
    if a is None or b is None:
        return 999
    return max(a[0] - b[0], a[1] - b[1])


def is_size_chart(path: Path) -> bool:
    """
    Détection renforcée d'un guide/tableau de tailles :
    beaucoup de pixels très clairs/neutres + nombreux petits contrastes de texte/tableau.
    """
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((300, 300))
            w, h = im.size
            if w < 50 or h < 50:
                return False

            pixels = list(im.getdata())
            n = len(pixels)

            near_white = 0
            bright_neutral = 0
            for r, g, b in pixels:
                mx = max(r, g, b)
                mn = min(r, g, b)
                if r >= 220 and g >= 220 and b >= 220:
                    near_white += 1
                if (r + g + b) / 3 >= 195 and (mx - mn) <= 35:
                    bright_neutral += 1

            white_ratio = near_white / n
            neutral_ratio = bright_neutral / n

            # Mesure de densité de petits contrastes (texte + lignes de tableau)
            gray = im.convert("L")
            edges = 0
            checks = 0

            for y in range(0, h, 2):
                for x in range(2, w, 2):
                    checks += 1
                    if abs(gray.getpixel((x, y)) - gray.getpixel((x - 2, y))) > 45:
                        edges += 1

            for x in range(0, w, 2):
                for y in range(2, h, 2):
                    checks += 1
                    if abs(gray.getpixel((x, y)) - gray.getpixel((x, y - 2))) > 45:
                        edges += 1

            edge_ratio = edges / max(1, checks)

            # Cas typiques des charts visibles dans ta boutique.
            return (
                white_ratio >= 0.52
                or neutral_ratio >= 0.64
                or (neutral_ratio >= 0.42 and edge_ratio >= 0.025)
            )
    except Exception:
        return False


def quarantine_file(path: Path, pid: str):
    """Déplace seulement la copie de la boutique, jamais l'original Yupoo."""
    try:
        root = PRODUCTS_ROOT.resolve()
        target = path.resolve()
        if root not in target.parents or not path.exists():
            return
        qdir = QUARANTINE / pid
        qdir.mkdir(parents=True, exist_ok=True)
        dst = qdir / path.name
        if dst.exists():
            dst = qdir / f"{path.stem}_{len(list(qdir.iterdir()))}{path.suffix}"
        shutil.move(str(path), str(dst))
    except OSError:
        pass


modified = 0
removed_charts = 0
removed_duplicates = 0
report = []

for p in products:
    pid = str(p.get("id") or "").strip()
    name = str(p.get("name") or "")
    old_images = [str(x) for x in (p.get("images") or []) if x]

    if not old_images:
        continue

    # Photo principale en tête.
    main = clean_web_path(str(p.get("image") or old_images[0]))
    ordered = sorted(old_images, key=lambda x: 0 if clean_web_path(x) == main else 1)

    kept = []
    kept_hashes = []
    removed = []

    for web in ordered:
        loc = local_path(web)
        if not loc.exists():
            continue

        # 1) Guide/tableau de tailles : on l'enlève même s'il était principal.
        if is_size_chart(loc):
            removed.append((web, "guide/tableau de tailles"))
            removed_charts += 1
            continue

        h = hashes(loc)

        # 2) Doublon visuel du même maillot dans LA MÊME fiche.
        if any(kh is not None and dist(h, kh) <= DUPLICATE_DISTANCE for kh in kept_hashes):
            removed.append((web, "doublon visuel"))
            removed_duplicates += 1
            continue

        kept.append(web)
        kept_hashes.append(h)

    # Sécurité : toujours garder au moins 1 image.
    if not kept:
        # Prend la première image qui existe, même si le filtre l'a classée suspecte.
        for web in ordered:
            if local_path(web).exists():
                kept = [web]
                removed = [(w, r) for (w, r) in removed if w != web]
                break

    if not kept:
        continue

    old_clean = [clean_web_path(x) for x in old_images]
    new_clean = [clean_web_path(x) for x in kept]

    if old_clean != new_clean:
        modified += 1
        p["images"] = kept
        p["image"] = kept[0]

        removed_final = []
        keep_set = set(new_clean)

        for web, reason in removed:
            if clean_web_path(web) in keep_set:
                continue
            quarantine_file(local_path(web), pid)
            removed_final.append({"image": clean_web_path(web), "reason": reason})

        report.append({
            "id": pid,
            "name": name,
            "avant": len(old_images),
            "apres": len(kept),
            "supprimees": removed_final,
        })

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

report_path = PROJECT / "nettoyage_visuel_v2_rapport.json"
report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("")
print("✅ NETTOYAGE VISUEL V2 TERMINÉ")
print(f"Produits modifiés              : {modified}")
print(f"Guides/tableaux retirés        : {removed_charts}")
print(f"Doublons visuels retirés       : {removed_duplicates}")
print(f"Rapport                        : {report_path}")
print(f"Quarantaine                    : {QUARANTINE}")
print("")
print("🛡️ Les photos originales Yupoo sur B: restent intactes.")
print("➡️ Fais ensuite Ctrl + F5 sur http://localhost:3000")
