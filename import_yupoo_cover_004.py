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
    s = re.sub(r"\b(?:retro|rétro|vintage|classic|fan|player|version|jersey|shirt|kit)\b", " ", s, flags=re.I)
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

def main():
    ap = argparse.ArgumentParser(
        description="Soccer Fans: prend la 4e image Yupoo comme couverture (001-003 = guides des tailles)."
    )
    ap.add_argument("catalogue", help="Chemin vers yupoo_images/catalogue.json")
    ap.add_argument("project", nargs="?", default=".", help="Racine du projet Next.js")
    ap.add_argument("--skip", type=int, default=3, help="Nombre d'images à ignorer au début de chaque album")
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

    public.mkdir(parents=True, exist_ok=True)
    products_dir.mkdir(parents=True, exist_ok=True)

    products = []
    copied = 0
    skipped_entries = 0
    fallback_count = 0

    for entry in raw:
        album_id = str(entry.get("album_id") or "").strip()
        title = norm(str(entry.get("title") or ""))

        if not album_id or not title or title.lower() in INVALID_TITLES:
            skipped_entries += 1
            continue

        raw_images = list(entry.get("images") or [])
        if entry.get("cover") and entry["cover"] not in raw_images:
            raw_images.insert(0, entry["cover"])

        resolved = []
        for raw_img in raw_images:
            src = resolve_source(str(raw_img), catalogue)
            if src:
                resolved.append(src)

        if not resolved:
            skipped_entries += 1
            continue

        # 001, 002, 003 = guides des tailles ; 004 = première photo produit.
        if len(resolved) > args.skip:
            chosen = resolved[args.skip]
        else:
            chosen = resolved[0]
            fallback_count += 1

        album_dest = products_dir / album_id
        album_dest.mkdir(parents=True, exist_ok=True)

        # Nettoie l'ancienne couverture (tableau des tailles).
        for old in album_dest.iterdir():
            if old.is_file():
                try:
                    old.unlink()
                except OSError:
                    pass

        ext = chosen.suffix.lower() if chosen.suffix else ".jpg"
        dst = album_dest / f"001{ext}"
        shutil.copy2(chosen, dst)
        copied += 1

        web_image = f"/products/{album_id}/{dst.name}"
        cat = classify(title)

        products.append({
            "id": album_id,
            "name": title,
            "team": guess_team(title),
            "cat": cat,
            "versions": versions_for(title, cat),
            "emoji": "🎽",
            "hot": False,
            "image": web_image,
            "images": [web_image],
            "source": entry.get("url") or "",
        })

    # Déduplication stable.
    dedup = {}
    for p in products:
        dedup[str(p["id"])] = p
    products = list(dedup.values())

    output_json.write_text(
        json.dumps(products, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("")
    print("✅ Import couverture maillot terminé")
    print(f"Produits générés : {len(products)}")
    print(f"Images copiées   : {copied}")
    print(f"Fallback image 1 : {fallback_count}")
    print(f"Entrées ignorées : {skipped_entries}")
    print(f"Catalogue        : {output_json}")
    print("")
    print("Recharge ensuite http://localhost:3000 avec Ctrl + F5.")

if __name__ == "__main__":
    main()
