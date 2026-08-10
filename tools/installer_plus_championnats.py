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
USER_AGENT = "SoccerFansMiniApp/1.1"
REQUEST_DELAY = 2.10

COUNTRIES = [
    "England","France","Spain","Italy","Germany","Portugal","Netherlands","Belgium",
    "Scotland","Turkey","Greece","Austria","Switzerland","Denmark","Sweden","Norway",
    "Poland","Czech Republic","Croatia","Serbia","Ukraine","Romania","Hungary",
    "Brazil","Argentina","Colombia","Uruguay","Chile","Mexico","USA","Canada",
    "Japan","South Korea","China","Saudi Arabia","Australia","South Africa",
    "Morocco","Algeria","Tunisia","Egypt","Nigeria","Ghana","Senegal"
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

def get_rows(data: dict) -> list[dict]:
    for key in ("countries","countrys","leagues"):
        rows=data.get(key)
        if isinstance(rows,list):
            return [x for x in rows if isinstance(x,dict)]
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
        print(f"      ⚠️ Logo : {e}")
        return None

LOGOS_ROOT.mkdir(parents=True,exist_ok=True)
LEAGUES_DIR.mkdir(parents=True,exist_ok=True)

clubs={}
if MAPPING_JSON.exists():
    try:
        previous=json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
        if isinstance(previous,dict):
            clubs=previous.get("clubs") or {}
    except Exception:
        pass

found={}
errors=[]

print("🏆 Recherche élargie des championnats de football")
print("=================================================")

for i,country in enumerate(COUNTRIES,1):
    print(f"[{i}/{len(COUNTRIES)}] {country}")

    merged=[]

    # 1) Requête Soccer.
    try:
        merged += get_rows(api_json(
            "search_all_leagues.php",
            {"c":country,"s":"Soccer"}
        ))
    except Exception as e:
        errors.append({"country":country,"mode":"soccer","error":str(e)})

    # 2) Requête sans filtre sport : elle peut retourner des ligues
    # absentes du premier résultat. On filtre Soccer localement.
    try:
        merged += get_rows(api_json(
            "search_all_leagues.php",
            {"c":country}
        ))
    except Exception as e:
        errors.append({"country":country,"mode":"all","error":str(e)})

    unique={}
    for row in merged:
        if not isinstance(row,dict):
            continue

        sport=normalize(row.get("strSport") or "")
        if sport and sport not in {"soccer","football"}:
            continue

        league_id=str(row.get("idLeague") or "").strip()
        name=str(row.get("strLeague") or "").strip()

        if not league_id or not name:
            continue

        unique[league_id]=row

    print(f"   → {len(unique)} championnat(s) football trouvé(s)")

    for league_id,row in unique.items():
        name=str(row.get("strLeague") or "").strip()
        badge=str(row.get("strBadge") or row.get("strLogo") or "").strip()

        # Si le logo n'est pas dans la liste, détail de la ligue.
        if not badge:
            try:
                details=api_json("lookupleague.php",{"id":league_id})
                rows=get_rows(details)
                if rows:
                    detail=rows[0]
                    name=str(detail.get("strLeague") or name).strip()
                    badge=str(
                        detail.get("strBadge")
                        or detail.get("strLogo")
                        or ""
                    ).strip()
            except Exception as e:
                errors.append({
                    "country":country,
                    "league":name,
                    "id":league_id,
                    "error":str(e)
                })

        if not badge:
            continue

        dest=download_image(
            badge,
            LEAGUES_DIR / f"{league_id}-{slugify(name)}"
        )
        if not dest:
            continue

        web_path="/" + dest.relative_to(PUBLIC).as_posix()

        found[league_id]={
            "id":league_id,
            "name":name,
            "country":country,
            "logo":web_path
        }

items=sorted(
    found.values(),
    key=lambda x:(normalize(x.get("country")),normalize(x.get("name")))
)

mapping={
    "clubs":clubs,
    "leagues":{},
    "leagueItems":items
}

for item in items:
    mapping["leagues"][normalize(item["name"])]=item["logo"]

MAPPING_JSON.write_text(
    json.dumps(mapping,ensure_ascii=False,indent=2),
    encoding="utf-8"
)

REPORT_JSON.write_text(
    json.dumps({
        "championships_installed":len(items),
        "countries_checked":COUNTRIES,
        "errors":errors,
        "items":items
    },ensure_ascii=False,indent=2),
    encoding="utf-8"
)

print("")
print("=================================================")
print(f"✅ Logos de championnats installés : {len(items)}")
print(f"✅ {MAPPING_JSON}")
print("➡️ Fais ensuite Ctrl + F5")
print("=================================================")
