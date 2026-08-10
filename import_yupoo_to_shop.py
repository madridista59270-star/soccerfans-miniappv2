from __future__ import annotations

import argparse
import json
import re
import shutil
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

    # Priorité : Short > Enfant > Rétro > Player > Fan.
    # Exemple : "Argentina retro shorts" = Short 20 €
    # Exemple : "Scotland retro Fan Version" = Rétro 50 €
    if re.search(r"shorts?", low):
        return {"Short": 20}

    if any(k in low for k in ("kid", "kids", "child", "children", "youth", "junior", "enfant")):
        return {"Enfant": 30}

    if any(k in low for k in ("retro", "rétro", "vintage", "classic")):
        return {"Rétro": 50}

    if re.search(r"player", low):
        return {"Player": 45}

    if re.search(r"fan", low):
        return {"Fan": 35}

    # Si aucun type n'est indiqué dans le titre, on laisse les 2 choix.
    return {"Fan": 35, "Player": 45}

def guess_team(title: str) -> str:
    # Retire les termes de saison/version les plus fréquents pour améliorer la recherche.
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
        # Le downloader enregistre typiquement "yupoo_images/album/001.jpg"
        candidates.extend([
            catalogue.parent.parent / p,
            catalogue.parent / p,
            catalogue.parent / p.name,
        ])
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None

def same_file_quick(src: Path, dst: Path) -> bool:
    try:
        return dst.exists() and dst.stat().st_size == src.stat().st_size
    except OSError:
        return False

def main():
    ap = argparse.ArgumentParser(
        description="Importe automatiquement un catalogue Yupoo téléchargé dans la boutique Soccer Fans."
    )
    ap.add_argument("catalogue", help="Chemin vers yupoo_images/catalogue.json")
    ap.add_argument("project", nargs="?", default=".", help="Racine du projet Next.js (défaut: dossier courant)")
    ap.add_argument(
        "--images-per-product", type=int, default=1,
        help="Nombre d'images copiées par produit. 1 = couverture seulement; 0 = toutes."
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

    public.mkdir(parents=True, exist_ok=True)
    products_dir.mkdir(parents=True, exist_ok=True)

    raw = json.loads(catalogue.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("catalogue.json doit contenir une liste de produits.")

    products = []
    skipped = 0
    copied = 0
    reused = 0

    for entry in raw:
        album_id = str(entry.get("album_id") or "").strip()
        title = norm(str(entry.get("title") or ""))
        if not album_id or not title or title.lower() in INVALID_TITLES:
            skipped += 1
            continue

        raw_images = list(entry.get("images") or [])
        if entry.get("cover") and entry["cover"] not in raw_images:
            raw_images.insert(0, entry["cover"])

        if args.images_per_product > 0:
            raw_images = raw_images[:args.images_per_product]

        web_images = []
        album_dest = products_dir / album_id
        album_dest.mkdir(parents=True, exist_ok=True)

        for idx, raw_img in enumerate(raw_images, 1):
            src = resolve_source(str(raw_img), catalogue)
            if not src:
                continue
            ext = src.suffix.lower() if src.suffix else ".jpg"
            dst = album_dest / f"{idx:03d}{ext}"
            if same_file_quick(src, dst):
                reused += 1
            else:
                shutil.copy2(src, dst)
                copied += 1
            web_images.append(f"/products/{album_id}/{dst.name}")

        if not web_images:
            skipped += 1
            continue

        cat = classify(title)
        product = {
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
        }
        products.append(product)

    # Déduplication stable par album_id.
    dedup = {}
    for p in products:
        dedup[str(p["id"])] = p
    products = list(dedup.values())

    output_json.write_text(
        json.dumps(products, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("")
    print("✅ Import terminé")
    print(f"Produits générés : {len(products)}")
    print(f"Entrées ignorées : {skipped}")
    print(f"Images copiées    : {copied}")
    print(f"Images déjà là    : {reused}")
    print(f"Catalogue boutique: {output_json}")
    print("")
    print("Tu peux relancer exactement la même commande après une mise à jour Yupoo :")
    print("les images déjà présentes seront réutilisées et products.json sera régénéré.")

if __name__ == "__main__":
    main()
