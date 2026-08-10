from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

PROJECT = Path.cwd()
PRODUCTS_JSON = PROJECT / "public" / "products.json"
PUBLIC = PROJECT / "public"
PRODUCTS_DIR = PUBLIC / "products"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def clean_web_path(value: str) -> str:
    """Retire ?v=... et retourne un chemin web propre."""
    return urlsplit(str(value or "")).path


def local_path_from_web(web_path: str) -> Path | None:
    p = clean_web_path(web_path)
    if not p.startswith("/"):
        return None
    local = PUBLIC / p.lstrip("/")
    return local


def sha1(path: Path) -> str | None:
    try:
        h = hashlib.sha1()
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ Introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ public/products.json doit contenir une liste.")

backup = PRODUCTS_JSON.with_name("products_avant_suppression_doublons.json")
if not backup.exists():
    backup.write_text(
        json.dumps(products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✅ Sauvegarde créée : {backup}")

total_products = 0
products_changed = 0
duplicates_removed = 0
files_deleted = 0
missing_files = 0

for p in products:
    total_products += 1
    pid = str(p.get("id") or "").strip()

    # La photo principale doit rester prioritaire.
    candidates = []
    if p.get("image"):
        candidates.append(str(p["image"]))
    candidates.extend(str(x) for x in (p.get("images") or []) if x)

    # Déduplication stable des chemins avant même de calculer le hash.
    seen_paths = set()
    ordered = []
    for web in candidates:
        clean = clean_web_path(web)
        if not clean or clean in seen_paths:
            continue
        seen_paths.add(clean)
        ordered.append(web)

    kept = []
    seen_hashes = {}
    duplicate_files_to_delete = []

    for web in ordered:
        local = local_path_from_web(web)

        # Si le fichier n'existe plus, on ne le garde pas dans products.json.
        if not local or not local.exists() or not local.is_file():
            missing_files += 1
            continue

        digest = sha1(local)
        if digest is None:
            missing_files += 1
            continue

        if digest in seen_hashes:
            duplicates_removed += 1

            # Ne supprime que les copies de la boutique.
            try:
                if PRODUCTS_DIR in local.parents and local != seen_hashes[digest]:
                    duplicate_files_to_delete.append(local)
            except Exception:
                pass
            continue

        seen_hashes[digest] = local
        kept.append(clean_web_path(web))

    if not kept:
        continue

    old_images = [clean_web_path(str(x)) for x in (p.get("images") or []) if x]
    old_main = clean_web_path(str(p.get("image") or ""))

    # La première conservée devient couverture + première image.
    p["image"] = kept[0]
    p["images"] = kept

    # Déduplique aussi les noms de sources mémorisés, sans toucher aux originaux Yupoo.
    source_names = []
    seen_source_names = set()
    for name in (p.get("photo_source_names") or []):
        name = str(name)
        if name and name not in seen_source_names:
            seen_source_names.add(name)
            source_names.append(name)
    if source_names:
        p["photo_source_names"] = source_names

    if old_images != kept or old_main != kept[0]:
        products_changed += 1

    # Suppression physique seulement après mise à jour logique.
    for f in duplicate_files_to_delete:
        try:
            if f.exists():
                f.unlink()
                files_deleted += 1
        except OSError:
            pass

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("")
print("✅ DOUBLONS SUPPRIMÉS")
print(f"Produits analysés              : {total_products}")
print(f"Produits modifiés              : {products_changed}")
print(f"Photos doublons retirées       : {duplicates_removed}")
print(f"Fichiers doublons supprimés    : {files_deleted}")
print(f"Références introuvables retirées: {missing_files}")
print("")
print("🛡️ Les photos originales dans B:\\yupoo_soccerfans_downloader\\yupoo_images n'ont PAS été touchées.")
print("➡️ Ensuite fais Ctrl + F5 sur http://localhost:3000")
