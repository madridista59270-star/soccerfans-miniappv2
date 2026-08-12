from __future__ import annotations

import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECT = Path(r"C:\Users\guillaume\Documents\GitHub\soccerfans-miniappv2")
PUBLIC = PROJECT / "public"
PRODUCTS_JSON = PUBLIC / "products.json"

# Une image strictement identique dans au moins 5 produits
# est considérée comme commune (très souvent guide/tableau des tailles).
THRESHOLD = 5

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def public_path(url: str) -> Path | None:
    if not url or not isinstance(url, str):
        return None
    if not url.startswith("/"):
        return None
    p = PUBLIC / url.lstrip("/").replace("/", "\\")
    return p if p.exists() and p.is_file() else None

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ products.json introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ products.json doit être une liste.")

print("🔎 Analyse des photos affichées sur le site...")
print("🛡️ Détection SHA-256 exacte uniquement.")
print("🛡️ Les originaux Yupoo ne seront jamais touchés.")

# 1) Hash des images actuellement référencées par le site
hash_products = defaultdict(set)
hash_paths = defaultdict(list)
url_hash = {}

for i, product in enumerate(products, 1):
    pid = str(product.get("id", ""))
    urls = []

    if product.get("image"):
        urls.append(product["image"])

    for u in product.get("images") or []:
        if u not in urls:
            urls.append(u)

    for url in urls:
        path = public_path(url)
        if not path:
            continue
        try:
            digest = sha256(path)
        except Exception:
            continue

        url_hash[(pid, url)] = digest
        hash_products[digest].add(pid)
        hash_paths[digest].append(path)

    if i % 100 == 0 or i == len(products):
        print(f"   {i}/{len(products)} produits analysés")

common_hashes = {
    digest
    for digest, pids in hash_products.items()
    if len(pids) >= THRESHOLD
}

print(f"✅ Images communes exactes détectées : {len(common_hashes)}")

# 2) Sauvegardes
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_json = PRODUCTS_JSON.with_name(f"products_backup_avant_suppression_size_{stamp}.json")
shutil.copy2(PRODUCTS_JSON, backup_json)

quarantine = PROJECT / f"_quarantaine_size_site_{stamp}"
quarantine.mkdir(parents=True, exist_ok=True)

removed_refs = 0
products_changed = 0
moved_files = set()

for product in products:
    pid = str(product.get("id", ""))
    original_urls = []

    if product.get("image"):
        original_urls.append(product["image"])

    for u in product.get("images") or []:
        if u not in original_urls:
            original_urls.append(u)

    keep = []
    removed = []

    for url in original_urls:
        digest = url_hash.get((pid, url))
        if digest and digest in common_hashes:
            removed.append(url)
        else:
            keep.append(url)

    if not removed:
        continue

    # Ne jamais laisser un produit sans photo si toutes ses images sont communes.
    if not keep:
        print(f"⚠️ {pid}: toutes les images sont communes, aucune suppression pour ce produit.")
        continue

    # Image principale = première image restante
    product["image"] = keep[0]
    product["images"] = keep

    removed_refs += len(removed)
    products_changed += 1

    # Déplace uniquement les copies du site hors de public.
    # Les originaux Yupoo sur B: ne sont pas concernés.
    for url in removed:
        path = public_path(url)
        if not path:
            continue
        try:
            resolved = str(path.resolve())
        except Exception:
            resolved = str(path)

        if resolved in moved_files:
            continue

        rel = path.relative_to(PUBLIC)
        dest = quarantine / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Si la même image est encore référencée ailleurs par sécurité, on ne la déplace pas.
        still_referenced = any(
            url == p.get("image") or url in (p.get("images") or [])
            for p in products
        )
        if not still_referenced and path.exists():
            shutil.move(str(path), str(dest))
            moved_files.add(resolved)

PRODUCTS_JSON.write_text(
    json.dumps(products, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("")
print("==================================================")
print(f"✅ Produits nettoyés        : {products_changed}")
print(f"✅ Références size retirées : {removed_refs}")
print(f"📦 Copies déplacées         : {len(moved_files)}")
print(f"💾 Backup products.json     : {backup_json.name}")
print(f"📁 Quarantaine              : {quarantine}")
print("🛡️ Aucun original Yupoo supprimé.")
print("➡️ Fais Ctrl + F5 sur le site.")
print("==================================================")
