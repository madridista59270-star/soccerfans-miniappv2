from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT = Path.cwd()
PUBLIC = PROJECT / "public"
LOGOS_ROOT = PUBLIC / "logos"
LEAGUES_DIR = LOGOS_ROOT / "leagues"
MAPPING_JSON = LOGOS_ROOT / "logos.json"
REPORT_JSON = LOGOS_ROOT / "championships_report.json"

API_BASE = "https://www.thesportsdb.com/api/v1/json/123"
USER_AGENT = "SoccerFansMiniApp/1.0"
REQUEST_DELAY = 2.15  # reste sous 30 requêtes/minute

# On parcourt les principaux pays de football + compétitions mondiales.
# L'API gratuite retourne jusqu'à 10 championnats par pays.
COUNTRIES = [
    "England","France","Spain","Italy","Germany","Portugal","Netherlands","Belgium",
    "Scotland","Turkey","Greece","Austria","Switzerland","Denmark","Sweden","Norway",
    "Poland","Czech Republic","Croatia","Serbia","Ukraine","Romania","Hungary",
    "Brazil","Argentina","Colombia","Uruguay","Chile","Mexico","USA","Canada",
    "Japan","South Korea","China","Saudi Arabia","Australia","South Africa",
    "Morocco","Algeria","Tunisia","Egypt","Nigeria","Ghana","Senegal","Worldwide"
]

def normalize(value: str) -> str:
    value=unicodedata.normalize("NFKD",str(value or ""))
    value="".join(c for c in value if not unicodedata.combining(c))
    value=value.lower().strip()
    value=re.sub(r"[^a-z0-9]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()

def slugify(value: str) -> str:
    return normalize(value).replace(" ","-") or "championship"

_last_request=0.0

def api_json(endpoint: str, params: dict | None=None) -> dict:
    global _last_request

    elapsed=time.time()-_last_request
    if elapsed<REQUEST_DELAY:
        time.sleep(REQUEST_DELAY-elapsed)

    params=params or {}
    url=f"{API_BASE}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})

    for attempt in range(5):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                _last_request=time.time()
                return json.loads(r.read().decode("utf-8",errors="replace"))
        except urllib.error.HTTPError as e:
            _last_request=time.time()
            if e.code==429 and attempt<4:
                print("   ⏳ Limite API : pause 65 secondes...")
                time.sleep(65)
                continue
            raise
        except Exception:
            _last_request=time.time()
            if attempt<4:
                time.sleep(4)
                continue
            raise
    return {}

def records_from(data: dict) -> list[dict]:
    for key in ("countries","countrys","leagues"):
        value=data.get(key)
        if isinstance(value,list):
            return [x for x in value if isinstance(x,dict)]
    return []

def download_image(url: str, dest_base: Path) -> Path | None:
    if not url:
        return None

    clean=url.split("?")[0]
    suffix=Path(urllib.parse.urlparse(clean).path).suffix.lower()
    if suffix not in {".png",".jpg",".jpeg",".webp"}:
        suffix=".png"

    dest=dest_base.with_suffix(suffix)

    if dest.exists() and dest.stat().st_size>100:
        return dest

    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            data=r.read()
        if len(data)<100:
            return None
        dest.write_bytes(data)
        return dest
    except Exception as e:
        print(f"   ⚠️ Logo non téléchargé : {e}")
        return None

LOGOS_ROOT.mkdir(parents=True,exist_ok=True)
LEAGUES_DIR.mkdir(parents=True,exist_ok=True)

# Garde les éventuels logos clubs déjà installés.
existing={"clubs":{},"leagues":{},"leagueItems":[]}
if MAPPING_JSON.exists():
    try:
        loaded=json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
        if isinstance(loaded,dict):
            existing["clubs"]=loaded.get("clubs") or {}
    except Exception:
        pass

league_items={}
errors=[]

print("🏆 Installation des logos de championnats football")
print("================================================")
print("")

for ci,country in enumerate(COUNTRIES,1):
    print(f"[{ci}/{len(COUNTRIES)}] {country}")

    try:
        data=api_json("search_all_leagues.php",{"c":country,"s":"Soccer"})
        leagues=records_from(data)
    except Exception as e:
        print(f"   ❌ API : {e}")
        errors.append({"country":country,"error":str(e)})
        continue

    if not leagues:
        print("   Aucun championnat retourné")
        continue

    for league in leagues:
        league_id=str(league.get("idLeague") or "").strip()
        name=str(league.get("strLeague") or "").strip()
        sport=str(league.get("strSport") or "Soccer").strip()

        if not league_id or not name:
            continue
        if sport and sport.lower() not in {"soccer","football"}:
            continue

        badge=str(
            league.get("strBadge")
            or league.get("strLogo")
            or ""
        ).strip()

        # Si la liste pays ne fournit pas directement le badge, on fait un lookup.
        if not badge:
            try:
                details=api_json("lookupleague.php",{"id":league_id})
                rows=records_from(details)
                if not rows and isinstance(details.get("leagues"),list):
                    rows=details["leagues"]
                if rows:
                    row=rows[0]
                    badge=str(row.get("strBadge") or row.get("strLogo") or "").strip()
                    name=str(row.get("strLeague") or name).strip()
            except Exception as e:
                errors.append({"league":name,"id":league_id,"error":str(e)})

        if not badge:
            print(f"   ⚠️ Pas de logo : {name}")
            continue

        dest=download_image(
            badge,
            LEAGUES_DIR / f"{league_id}-{slugify(name)}"
        )

        if not dest:
            continue

        web_path="/" + dest.relative_to(PUBLIC).as_posix()
        key=f"{league_id}:{normalize(name)}"

        league_items[key]={
            "id":league_id,
            "name":name,
            "country":country,
            "logo":web_path
        }

        print(f"   ✅ {name}")

# Tri propre.
items=sorted(
    league_items.values(),
    key=lambda x:(str(x.get("country") or ""),str(x.get("name") or ""))
)

mapping={
    "clubs":existing["clubs"],
    "leagues":{},
    "leagueItems":items
}

# Mapping texte -> logo pour compatibilité avec le page.js existant.
for item in items:
    mapping["leagues"][normalize(item["name"])]=item["logo"]

MAPPING_JSON.write_text(
    json.dumps(mapping,ensure_ascii=False,indent=2),
    encoding="utf-8"
)

REPORT_JSON.write_text(
    json.dumps({
        "countries_checked":COUNTRIES,
        "championships_installed":len(items),
        "errors":errors,
        "items":items
    },ensure_ascii=False,indent=2),
    encoding="utf-8"
)

print("")
print("================================================")
print("✅ INSTALLATION TERMINÉE")
print(f"Logos de championnats installés : {len(items)}")
print(f"Mapping : {MAPPING_JSON}")
print(f"Rapport : {REPORT_JSON}")
print("================================================")
print("")
print("➡️ Recharge ensuite le site avec Ctrl + F5")
