from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

INVALID_TITLES = {
    "该相册已不存在",
    "album does not exist",
    "this album does not exist",
}

COUNTRIES = {
    "france","brazil","brasil","argentina","argentine","england","italy","italia","spain","espana","españa",
    "germany","deutschland","belgium","belgique","portugal","netherlands","holland","croatia","croatie",
    "morocco","maroc","algeria","algérie","tunisia","tunisie","senegal","sénégal","cameroon","cameroun",
    "nigeria","mexico","mexique","usa","united states","japan","japon","korea","corée","uruguay","colombia",
    "colombie","chile","chili","ecuador","switzerland","suisse","austria","autriche","denmark","danemark",
    "sweden","suède","norway","norvège","poland","pologne","turkey","turquie","greece","grèce","serbia",
    "serbie","ghana","egypt","égypte","ivory coast","côte d'ivoire","cote d'ivoire"
}

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def classify(title: str) -> str:
    low = title.lower()
    if any(k in low for k in ("kid", "kids", "child", "children", "youth", "junior", "enfant")):
        return "Enfant"
    if any(k in low for k in ("retro", "rétro", "vintage", "classic")):
        return "Rétro"
    if any(country in low for country in COUNTRIES):
        return "Nations"
    return "Clubs"

def versions_for(title: str, cat: str) -> dict[str, int]:
    low = title.lower()
    if cat == "Enfant":
        return {"Enfant": 32}
    if cat == "Rétro":
        return {"Rétro": 34}
    if "player" in low:
        return {"Player": 39}
    if "fan" in low:
        return {"Fan": 29}
    return {"Fan": 29, "Player": 39}

def guess_team(title: str) -> str:
    s = re.sub(r"\b(?:19|20)\d{2}(?:/\d{2})?\b", " ", title, flags=re.I)
    s = re.sub(r"\bseason\b", " ", s, flags=re.I)
    s = re.sub(r"\b(?:home|away|third|fourth|goalkeeper|training)\b", " ", s, flags=re.I)
    s = re.sub(r"\b(?:retro|vintage|classic|fan|player|version|jersey|shirt|kit)\b", " ", s, flags=re.I)
    s = norm(s)
    return s[:80] or title[:80]

def resolve_source(raw: str, catalogue: Path) -> Path | None:
    if not raw:
        return None
    p = Path(raw)
    candidates = []
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.extend([
            catalogue.parent.parent / p,
            catalogue.parent / p,
            catalogue.parent / p.name,
        ])
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None

def file_hash(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def same_file_quick(src: Path, dst: Path) -> bool:
    try:
        return dst.exists() and dst.stat().st_size == src.stat().st_size
    except OSError:
        return False

def main():
    ap = argparse.ArgumentParser(
        description="Import intelligent Yupoo -> Soccer Fans : évite les images communes (ex: guides des tailles)."
    )
    ap.add_argument("catalogue", help="Chemin vers yupoo_images/catalogue.json")
    ap.add_argument("project", nargs="?", default=".", help="Racine du projet Next.js")
    ap.add_argument(
        "--shared-threshold",
        type=int,
        default=3,
        help="Une image identique présente dans au moins N albums est considérée comme image commune à éviter."
    )
    ap.add_argument(
        "--images-per-product",
        type=int,
        default=1,
        help="Nombre d'images produit copiées. 1 = couverture seulement; 0 = toutes les images non communes."
    )
    args = ap.parse_args()

    catalogue = Path(args.catalogue).expanduser().resolve()
    project = Path(args.project).expanduser().resolve()
    public = project / "public"
    products_dir = public / "products"
    output_json = public / "products.json"

    if not catalogue.exists():
        raise SystemExit(f"Catalogue introuvable : {catalogue}")
    if not project.exists():
        raise SystemExit(f"Projet introuvable : {project}")

    raw = json.loads(catalogue.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("catalogue.json doit contenir une liste de produits.")

    # 1) Résoudre toutes les images et compter celles qui sont identiques entre plusieurs albums.
    entries = []
    hash_album_count = Counter()

    for entry in raw:
        album_id = str(entry.get("album_id") or "").strip()
        title = norm(str(entry.get("title") or ""))
        if not album_id or not title or title.lower() in INVALID_TITLES:
            continue

        raw_images = list(entry.get("images") or [])
        if entry.get("cover") and entry["cover"] not in raw_images:
            raw_images.insert(0, entry["cover"])

        resolved = []
        seen_hashes_this_album = set()

        for raw_img in raw_images:
            src = resolve_source(str(raw_img), catalogue)
            if not src:
                continue
            try:
                digest = file_hash(src)
            except OSError:
                continue
            resolved.append((src, digest))
            seen_hashes_this_album.add(digest)

        for digest in seen_hashes_this_album:
            hash_album_count[digest] += 1

        entries.append((entry, album_id, title, resolved))

    shared_hashes = {
        digest for digest, count in hash_album_count.items()
        if count >= max(2, args.shared_threshold)
    }

    public.mkdir(parents=True, exist_ok=True)
    products_dir.mkdir(parents=True, exist_ok=True)

    products = []
    copied = 0
    reused = 0
    skipped = 0
    shared_skipped = 0

    for entry, album_id, title, resolved in entries:
        if not resolved:
            skipped += 1
            continue

        # 2) Priorité aux images uniques de l'album.
        unique_candidates = [(src, dig) for src, dig in resolved if dig not in shared_hashes]
        shared_skipped += len(resolved) - len(unique_candidates)

        # Si toutes les images sont communes, on garde quand même la première disponible.
        candidates = unique_candidates or resolved

        # Dédupliquer par hash en gardant l'ordre du catalogue.
        dedup_candidates = []
        seen = set()
        for src, dig in candidates:
            if dig in seen:
                continue
            seen.add(dig)
            dedup_candidates.append((src, dig))

        if args.images_per_product > 0:
            dedup_candidates = dedup_candidates[:args.images_per_product]

        if not dedup_candidates:
            skipped += 1
            continue

        album_dest = products_dir / album_id
        album_dest.mkdir(parents=True, exist_ok=True)

        # Supprime les anciennes couvertures de cet album pour éviter de garder le guide des tailles.
        for old in album_dest.glob("*"):
            if old.is_file():
                try:
                    old.unlink()
                except OSError:
                    pass

        web_images = []
        for idx, (src, _dig) in enumerate(dedup_candidates, 1):
            ext = src.suffix.lower() if src.suffix else ".jpg"
            dst = album_dest / f"{idx:03d}{ext}"
            if same_file_quick(src, dst):
                reused += 1
            else:
                shutil.copy2(src, dst)
                copied += 1
            web_images.append(f"/products/{album_id}/{dst.name}")

        cat = classify(title)
        products.append({
            "id": album_id,
            "name": title,
            "team": guess_team(title),
            "cat": cat,
            "versions": versions_for(title, cat),
            "emoji": "🎽",
            "hot": False,
            "image": web_images[0],
            "images": web_images,
            "source": entry.get("url") or "",
        })

    dedup = {}
    for p in products:
        dedup[str(p["id"])] = p
    products = list(dedup.values())

    output_json.write_text(
        json.dumps(products, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("")
    print("✅ Import intelligent terminé")
    print(f"Produits générés        : {len(products)}")
    print(f"Entrées ignorées        : {skipped}")
    print(f"Images communes évitées : {shared_skipped}")
    print(f"Images copiées          : {copied}")
    print(f"Images déjà là          : {reused}")
    print(f"Catalogue boutique      : {output_json}")
    print("")
    print("Recharge ensuite le site avec Ctrl + F5.")

if __name__ == "__main__":
    main()
