from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

ROOT = Path(r"B:\yupoo_soccerfans_downloader")
YUPOO = ROOT / "yupoo_images"
CATALOGUE = YUPOO / "catalogue.json"

OUTPUT = YUPOO / "catalogue_propre_exact.json"
REPORT = YUPOO / "rapport_nettoyage_exact.json"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Un guide de taille doit être EXACTEMENT le même fichier dans au moins
# ce nombre d'albums différents avant d'être considéré comme "guide commun".
GUIDE_MIN_ALBUMS = 5


def natural_key(path: Path):
    m = re.search(r"(\d+)", path.stem)
    return (int(m.group(1)) if m else 10**9, path.name.lower())


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
    Filtre volontairement prudent :
    l'image doit être très claire/neutre et avoir beaucoup de petits contrastes,
    comme un tableau de tailles / guide textuel.
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

            # Très prudent : ne suffit pas d'être clair.
            return (
                (white_ratio >= 0.58 and edge_ratio >= 0.018)
                or
                (neutral_ratio >= 0.68 and edge_ratio >= 0.020)
            )

    except Exception:
        return False


def find_album_folder(album_id: str, entry: dict) -> Path | None:
    raw_folder = str(entry.get("folder") or "").strip()

    if raw_folder:
        p = Path(raw_folder)
        candidates = []

        if p.is_absolute():
            candidates.append(p)
        else:
            candidates.extend([
                ROOT / p,
                YUPOO / p.name,
            ])

        for c in candidates:
            if c.exists() and c.is_dir():
                return c

    matches = [p for p in YUPOO.glob(f"{album_id}_*") if p.is_dir()]
    if matches:
        return matches[0]

    direct = YUPOO / album_id
    if direct.is_dir():
        return direct

    return None


def rel_for_catalogue(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


if not CATALOGUE.exists():
    raise SystemExit(f"❌ Catalogue introuvable : {CATALOGUE}")

data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
if not isinstance(data, list):
    raise SystemExit("❌ catalogue.json doit contenir une liste.")

backup = YUPOO / "catalogue_sauvegarde_avant_exact.json"
if not backup.exists():
    shutil.copy2(CATALOGUE, backup)
    print(f"✅ Sauvegarde créée : {backup}")

print("")
print(f"🔎 Analyse sûre de {len(data)} produit(s)")
print("Règles :")
print("  1) doublon = fichier EXACTEMENT identique (SHA-256)")
print(f"  2) guide = fichier EXACT identique dans ≥ {GUIDE_MIN_ALBUMS} albums + aspect tableau")
print("  3) aucune photo originale n'est supprimée")
print("")

album_infos = []
hash_to_albums = defaultdict(set)
hash_to_sample = {}

# ----------------------------------------------------------
# PASSAGE 1 : recense toutes les images + hashes exacts
# ----------------------------------------------------------
for idx, entry in enumerate(data, 1):
    album_id = str(entry.get("album_id") or "").strip()
    title = str(entry.get("title") or "").strip()

    folder = find_album_folder(album_id, entry) if album_id else None

    if not folder:
        album_infos.append({
            "entry": entry,
            "album_id": album_id,
            "title": title,
            "folder": None,
            "files": [],
        })
        continue

    files = sorted(
        [
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS
        ],
        key=natural_key,
    )

    rows = []
    for img in files:
        digest = sha256(img)
        rows.append((img, digest))
        if digest:
            hash_to_albums[digest].add(album_id)
            hash_to_sample.setdefault(digest, img)

    album_infos.append({
        "entry": entry,
        "album_id": album_id,
        "title": title,
        "folder": folder,
        "files": rows,
    })

    if idx % 100 == 0 or idx == len(data):
        print(f"Analyse fichiers : {idx}/{len(data)}")

# ----------------------------------------------------------
# Identifie uniquement les guides communs très sûrs
# ----------------------------------------------------------
guide_hashes = set()

for digest, albums in hash_to_albums.items():
    if len(albums) < GUIDE_MIN_ALBUMS:
        continue

    sample = hash_to_sample.get(digest)
    if sample and looks_like_size_guide(sample):
        guide_hashes.add(digest)

print("")
print(f"Guides communs exacts détectés : {len(guide_hashes)}")
print("")

# ----------------------------------------------------------
# PASSAGE 2 : crée un NOUVEAU catalogue sans toucher aux originaux
# ----------------------------------------------------------
cleaned = []
report = []

albums_found = 0
albums_missing = 0
photos_total = 0
photos_kept = 0
exact_duplicates_removed = 0
guides_removed = 0

for idx, info in enumerate(album_infos, 1):
    entry = info["entry"]
    album_id = info["album_id"]
    title = info["title"]
    folder = info["folder"]
    rows = info["files"]

    if not folder:
        albums_missing += 1
        cleaned.append(dict(entry))
        continue

    albums_found += 1
    photos_total += len(rows)

    seen_hashes = set()
    kept_paths = []
    removed = []

    for img, digest in rows:
        if not digest:
            # Si on ne peut pas calculer le hash, on garde l'image par sécurité.
            kept_paths.append(img)
            continue

        # 1) Doublon EXACT dans le même album.
        if digest in seen_hashes:
            exact_duplicates_removed += 1
            removed.append({
                "file": img.name,
                "reason": "doublon exact"
            })
            continue

        seen_hashes.add(digest)

        # 2) Guide commun EXACT et confirmé visuellement comme tableau.
        if digest in guide_hashes:
            guides_removed += 1
            removed.append({
                "file": img.name,
                "reason": "guide/tableau commun exact"
            })
            continue

        kept_paths.append(img)

    # Sécurité absolue : ne jamais vider un produit.
    if not kept_paths and rows:
        kept_paths = [rows[0][0]]

    new_entry = dict(entry)

    if kept_paths:
        web_images = [rel_for_catalogue(p) for p in kept_paths]
        new_entry["folder"] = folder.relative_to(ROOT).as_posix()
        new_entry["images"] = web_images
        new_entry["cover"] = web_images[0]
        photos_kept += len(kept_paths)

    cleaned.append(new_entry)

    if removed:
        report.append({
            "album_id": album_id,
            "title": title,
            "before": len(rows),
            "after": len(kept_paths),
            "removed": removed,
        })

    if idx % 100 == 0 or idx == len(album_infos):
        OUTPUT.write_text(
            json.dumps(cleaned + [x["entry"] for x in album_infos[idx:]],
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        REPORT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(
            f"Nettoyage : {idx}/{len(album_infos)} | "
            f"doublons exacts={exact_duplicates_removed} | "
            f"guides={guides_removed}"
        )

OUTPUT.write_text(
    json.dumps(cleaned, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

REPORT.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("")
print("✅ NETTOYAGE SÛR TERMINÉ")
print(f"Produits catalogue            : {len(data)}")
print(f"Albums trouvés                : {albums_found}")
print(f"Albums introuvables           : {albums_missing}")
print(f"Photos analysées              : {photos_total}")
print(f"Photos conservées             : {photos_kept}")
print(f"Doublons EXACTS retirés       : {exact_duplicates_removed}")
print(f"Guides communs EXACTS retirés : {guides_removed}")
print("")
print(f"Catalogue propre : {OUTPUT}")
print(f"Rapport          : {REPORT}")
print(f"Sauvegarde       : {backup}")
print("")
print("🛡️ AUCUNE photo originale n'a été supprimée.")
print("➡️ Le prochain import doit utiliser catalogue_propre_exact.json")
