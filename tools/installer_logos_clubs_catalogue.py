from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = Path.cwd()
PUBLIC = PROJECT / "public"
PRODUCTS_JSON = PUBLIC / "products.json"
LOGOS_ROOT = PUBLIC / "logos"
CLUBS_DIR = LOGOS_ROOT / "clubs"
MAPPING_JSON = LOGOS_ROOT / "logos.json"

API_BASE = "https://www.thesportsdb.com/api/v1/json/123"
USER_AGENT = "SoccerFansMiniApp/1.0"
DELAY = 2.1

ALIASES = {
    "Paris Saint-Germain":"Paris SG",
    "Olympique de Marseille":"Marseille",
    "Olympique Lyonnais":"Lyon",
    "FC Barcelona":"Barcelona",
    "Inter Milan":"Internazionale",
    "Bayern Munich":"Bayern Munich",
    "Borussia Dortmund":"Dortmund",
    "Atlético Madrid":"Atletico Madrid",
    "Manchester United":"Manchester United",
    "Manchester City":"Manchester City",
    "Tottenham Hotspur":"Tottenham",
    "Sporting CP":"Sporting Lisbon",
    "Inter Miami":"Inter Miami",
    "Al Nassr":"Al-Nassr",
    "Al Hilal":"Al-Hilal",
    "Al Ittihad":"Al-Ittihad",
}

def normalize(value: str) -> str:
    value=unicodedata.normalize("NFKD",str(value or ""))
    value="".join(c for c in value if not unicodedata.combining(c))
    value=value.lower().strip()
    value=re.sub(r"[^a-z0-9]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()

def slug(value: str) -> str:
    return normalize(value).replace(" ","-") or "club"

def api_search(team: str):
    url=API_BASE+"/searchteams.php?"+urllib.parse.urlencode({"t":team})
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.loads(r.read().decode("utf-8",errors="replace"))

def download(url: str, dest_base: Path):
    ext=Path(urllib.parse.urlparse(url.split("?")[0]).path).suffix.lower()
    if ext not in {".png",".jpg",".jpeg",".webp"}:
        ext=".png"
    dest=dest_base.with_suffix(ext)

    if dest.exists() and dest.stat().st_size>200:
        return dest

    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})
    with urllib.request.urlopen(req,timeout=30) as r:
        data=r.read()
    if len(data)<200:
        return None
    dest.write_bytes(data)
    return dest

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ products.json introuvable : {PRODUCTS_JSON}")

products=json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
clubs=sorted({
    str(p.get("team") or p.get("club") or "").strip()
    for p in products
    if isinstance(p,dict)
    and str(p.get("league") or "").strip()
    and str(p.get("team") or p.get("club") or "").strip()
})

LOGOS_ROOT.mkdir(parents=True,exist_ok=True)
CLUBS_DIR.mkdir(parents=True,exist_ok=True)

mapping={"clubs":{},"leagues":{},"leagueItems":[],"nationItems":[]}
if MAPPING_JSON.exists():
    try:
        old=json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
        if isinstance(old,dict):
            mapping.update(old)
            mapping["clubs"]=dict(old.get("clubs") or {})
    except Exception:
        pass

print(f"⚽ Clubs à traiter : {len(clubs)}")

for i,club in enumerate(clubs,1):
    key=normalize(club)

    # Déjà installé
    current=mapping["clubs"].get(key)
    if current:
        local=PUBLIC/current.lstrip("/")
        if local.exists():
            print(f"[{i}/{len(clubs)}] ✅ déjà présent : {club}")
            continue

    query=ALIASES.get(club,club)
    print(f"[{i}/{len(clubs)}] 🔎 {club}")

    try:
        data=api_search(query)
        teams=data.get("teams") or []
    except Exception as e:
        print(f"   ⚠️ API : {e}")
        time.sleep(DELAY)
        continue

    best=None
    wanted=normalize(club)

    for team in teams:
        if str(team.get("strSport") or "").lower() not in {"soccer","football"}:
            continue

        tname=normalize(team.get("strTeam") or "")
        talt=normalize(team.get("strTeamAlternate") or "")

        score=0
        if tname==wanted: score+=100
        if wanted in tname or tname in wanted: score+=55
        if talt and (wanted in talt or talt in wanted): score+=35

        badge=team.get("strBadge") or team.get("strLogo") or ""
        if not badge:
            continue

        if best is None or score>best[0]:
            best=(score,team,badge)

    if not best:
        print("   ❌ logo non trouvé")
        time.sleep(DELAY)
        continue

    try:
        dest=download(best[2],CLUBS_DIR/slug(club))
    except Exception as e:
        print(f"   ⚠️ téléchargement : {e}")
        dest=None

    if dest:
        web="/"+dest.relative_to(PUBLIC).as_posix()
        mapping["clubs"][key]=web
        print(f"   ✅ {web}")

    MAPPING_JSON.write_text(
        json.dumps(mapping,ensure_ascii=False,indent=2),
        encoding="utf-8"
    )
    time.sleep(DELAY)

print("")
print("✅ Logos clubs terminés.")
print(f"Mapping : {MAPPING_JSON}")
print("➡️ Fais Ctrl + F5 ensuite.")
