from __future__ import annotations

import json
import re
import shutil
import unicodedata
from collections import defaultdict, OrderedDict
from datetime import datetime
from pathlib import Path

PROJECT = Path(r"C:\Users\guillaume\Documents\GitHub\soccerfans-miniappv2")
PUBLIC = PROJECT / "public"
PRODUCTS_JSON = PUBLIC / "products.json"

PRICES = {"Fan":35, "Player":45, "Enfant":30}
VERSION_ORDER = ["Fan","Player","Enfant"]

def norm(value):
    value=unicodedata.normalize("NFKD",str(value or ""))
    value="".join(c for c in value if not unicodedata.combining(c))
    value=value.lower()
    value=re.sub(r"[_/\\|–—-]+"," ",value)
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()

def detect_version(p):
    explicit=str(p.get("version") or "").strip().lower()
    name=f"{p.get('name','')} {p.get('source_title','')} {p.get('cat','')}"
    n=norm(name)

    if explicit=="enfant" or norm(p.get("cat",""))=="enfant" or re.search(r"\b(kid|kids|youth|junior|enfant|child|children)\b",n):
        return "Enfant"
    if explicit=="player" or re.search(r"\bplayer\b",n):
        return "Player"
    return "Fan"

def clean_base_name(value):
    s=str(value or "").strip()

    # Enlève seulement les mentions de VERSION, jamais Domicile/Extérieur/Third/Gardien.
    patterns=[
        r"\bPlayer\s+Version\b",
        r"\bFan\s+Version\b",
        r"\bKids?\s+(?:Kit|Version)?\b",
        r"\bYouth\b",
        r"\bJunior\b",
        r"\bEnfant\b",
        r"\bPlayer\b",
        r"\bFan\b",
    ]
    for pat in patterns:
        s=re.sub(pat," ",s,flags=re.I)

    s=re.sub(r"\s+"," ",s).strip(" -")
    return s

def group_key(p):
    team=norm(p.get("team") or p.get("club") or p.get("nation"))
    season=norm(p.get("season"))
    kit=norm(p.get("kit"))
    gender=norm(p.get("gender"))

    # Méthode préférée : métadonnées structurées.
    if team and season and kit:
        return f"meta|{team}|{season}|{kit}|{gender}"

    # Fallback très conservateur : même nom après retrait de Fan/Player/Enfant.
    base=norm(clean_base_name(p.get("name") or p.get("source_title")))
    if base and len(base)>=8:
        return f"name|{base}|{gender}"

    # Sinon : ne pas fusionner.
    return f"unique|{p.get('id')}"

def unique(seq):
    out=[]
    seen=set()
    for x in seq or []:
        if not x:
            continue
        x=str(x)
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ products.json introuvable : {PRODUCTS_JSON}")

products=json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products,list):
    raise SystemExit("❌ products.json doit être une liste.")

stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
backup=PRODUCTS_JSON.with_name(f"products_backup_avant_fusion_versions_{stamp}.json")
shutil.copy2(PRODUCTS_JSON,backup)

groups=defaultdict(list)
for p in products:
    if isinstance(p,dict):
        groups[group_key(p)].append(p)

merged=[]
report=[]
fusion_groups=0
removed_cards=0

for key,items in groups.items():
    versions_present=defaultdict(list)

    for p in items:
        versions_present[detect_version(p)].append(p)

    # On fusionne seulement s'il y a au moins 2 versions différentes.
    if len(versions_present)<2:
        merged.extend(items)
        continue

    fusion_groups+=1
    removed_cards += len(items)-1

    # Master : Fan > Player > Enfant
    master=None
    master_version=None
    for v in VERSION_ORDER:
        if versions_present.get(v):
            master=versions_present[v][0]
            master_version=v
            break

    master=dict(master)

    # Nom propre sans suffixe version.
    master["name"]=clean_base_name(master.get("name") or master.get("source_title"))

    # Catégorie principale : préfère Nations/Clubs/Rétro plutôt que Enfant.
    preferred_cat=None
    for wanted in ["Nations","Clubs","Rétro"]:
        for p in items:
            if p.get("cat")==wanted:
                preferred_cat=wanted
                break
        if preferred_cat:
            break

    if preferred_cat:
        master["cat"]=preferred_cat
    elif master.get("cat")=="Enfant":
        # Si aucune catégorie adulte structurée, garder Enfant.
        master["cat"]="Enfant"

    versions=OrderedDict()
    version_images={}
    version_ids={}
    version_titles={}

    for v in VERSION_ORDER:
        plist=versions_present.get(v) or []
        if not plist:
            continue

        versions[v]=PRICES[v]
        imgs=[]
        ids=[]
        titles=[]

        for p in plist:
            # Priorité à la cover, puis galerie.
            if p.get("image"):
                imgs.append(p["image"])
            imgs.extend(p.get("images") or [])
            if p.get("id"):
                ids.append(str(p["id"]))
            if p.get("source_title"):
                titles.append(str(p["source_title"]))

        version_images[v]=unique(imgs)
        version_ids[v]=ids
        version_titles[v]=titles

    master["versions"]=dict(versions)
    master["versionImages"]=version_images
    master["versionProductIds"]=version_ids
    master["versionSourceTitles"]=version_titles
    master["mergedVersions"]=True
    master["mergedVariantCount"]=sum(len(v) for v in versions_present.values())

    # Cover par défaut : Fan, sinon Player, sinon Enfant.
    default_v="Fan" if "Fan" in version_images else ("Player" if "Player" in version_images else "Enfant")
    default_imgs=version_images.get(default_v) or []

    if default_imgs:
        master["image"]=default_imgs[0]
        master["images"]=default_imgs

    merged.append(master)

    report.append({
        "key":key,
        "kept_id":master.get("id"),
        "name":master.get("name"),
        "versions":list(versions.keys()),
        "merged_ids":[str(p.get("id","")) for p in items],
        "removed_cards":len(items)-1,
    })

# Ordre stable
def sort_key(p):
    return (
        norm(p.get("cat")),
        norm(p.get("league")),
        norm(p.get("team")),
        norm(p.get("season")),
        norm(p.get("kit")),
        norm(p.get("name")),
    )

merged.sort(key=sort_key)

PRODUCTS_JSON.write_text(
    json.dumps(merged,ensure_ascii=False,indent=2),
    encoding="utf-8"
)

report_path=PUBLIC/f"rapport_fusion_versions_{stamp}.json"
report_path.write_text(
    json.dumps({
        "before":len(products),
        "after":len(merged),
        "fusion_groups":fusion_groups,
        "cards_removed":removed_cards,
        "groups":report,
    },ensure_ascii=False,indent=2),
    encoding="utf-8"
)

print("")
print("==========================================================")
print("✅ FUSION FAN / PLAYER / ENFANT TERMINÉE")
print("==========================================================")
print(f"Produits avant       : {len(products)}")
print(f"Produits après       : {len(merged)}")
print(f"Groupes fusionnés    : {fusion_groups}")
print(f"Cartes doublons retirées : {removed_cards}")
print(f"💾 Sauvegarde        : {backup.name}")
print(f"📄 Rapport           : {report_path.name}")
print("🛡️ Aucune photo originale supprimée.")
print("➡️ Fais ensuite Ctrl + F5.")
print("==========================================================")
