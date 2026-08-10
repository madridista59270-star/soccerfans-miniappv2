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
PRODUCTS_JSON = PROJECT / "public" / "products.json"
LOGOS_ROOT = PROJECT / "public" / "logos"
CLUBS_DIR = LOGOS_ROOT / "clubs"
LEAGUES_DIR = LOGOS_ROOT / "leagues"
MAPPING_JSON = LOGOS_ROOT / "logos.json"
REPORT_JSON = LOGOS_ROOT / "logos_report.json"

API_BASE = "https://www.thesportsdb.com/api/v1/json/123"
REQUEST_DELAY = 2.15  # free API: 30 requests/minute
USER_AGENT = "SoccerFansMiniApp/1.0"

# IDs verified for the 5 championships already used by the shop.
KNOWN_LEAGUES = {
    "Ligue 1": 4334,
    "Premier League": 4328,
    "La Liga": 4335,
    "Serie A": 4332,
    "Bundesliga": 4331,
}

ALIASES = {
    "paris": "Paris SG",
    "psg": "Paris SG",
    "paris saint germain": "Paris SG",
    "barcelone": "Barcelona",
    "fc barcelone": "Barcelona",
    "milan": "AC Milan",
    "ac milan": "AC Milan",
    "inter": "Inter Milan",
    "inter milan": "Inter Milan",
    "bayern": "Bayern Munich",
    "bayern munich": "Bayern Munich",
    "dortmund": "Borussia Dortmund",
    "man united": "Manchester United",
    "manchester united": "Manchester United",
    "man city": "Manchester City",
    "manchester city": "Manchester City",
    "atletico": "Atletico Madrid",
    "atlético": "Atletico Madrid",
    "real": "Real Madrid",
    "real madrid": "Real Madrid",
    "marseille": "Marseille",
    "om": "Marseille",
    "lyon": "Lyon",
    "monaco": "Monaco",
    "juve": "Juventus",
    "juventus": "Juventus",
}


def normalize_key(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def slugify(value: str) -> str:
    return normalize_key(value).replace(" ", "-") or "logo"


def clean_team_guess(value: str) -> str:
    s = str(value or "").strip()

    # Remove leading season/year noise: "18 Paris", "1998 Morocco", "2025 season ..."
    s = re.sub(
        r"^\s*(?:\d{2,4}(?:\s*[-/]\s*\d{2,4})?)\s*(?:season)?\s*",
        "",
        s,
        flags=re.I,
    )

    # Remove common merchandise descriptors accidentally included in team field.
    s = re.sub(
        r"\b(?:season|home|away|third|fourth|goalkeeper|gk|retro|rétro|fan|player|version|shirt|jersey|kids?|youth|shorts?)\b.*$",
        "",
        s,
        flags=re.I,
    ).strip(" -_")

    key = normalize_key(s)
    return ALIASES.get(key, s)


def guess_from_product_name(name: str) -> str:
    s = str(name or "").strip()

    patterns = [
        r"\bseason\s+(.+?)\s+(?:home|away|third|fourth|goalkeeper|gk|retro|rétro|fan|player|kids?|youth|shorts?)\b",
        r"^\s*(?:\d{2,4}(?:\s*[-/]\s*\d{2,4})?)?\s*(.+?)\s+(?:home|away|third|fourth|goalkeeper|gk|retro|rétro|fan|player|kids?|youth|shorts?)\b",
    ]

    for pat in patterns:
        m = re.search(pat, s, flags=re.I)
        if m:
            candidate = clean_team_guess(m.group(1))
            if candidate:
                return candidate
    return ""


_last_request = 0.0


def api_json(endpoint: str, params: dict[str, str | int]) -> dict:
    global _last_request

    elapsed = time.time() - _last_request
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)

    url = f"{API_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                _last_request = time.time()
                return json.loads(r.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            _last_request = time.time()
            if e.code == 429 and attempt < 3:
                print("   ⏳ Limite API atteinte, pause 15 s...")
                time.sleep(15)
                continue
            raise
        except Exception:
            _last_request = time.time()
            if attempt < 3:
                time.sleep(3)
                continue
            raise

    return {}


def download_image(url: str, dest_base: Path) -> Path | None:
    if not url:
        return None

    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"

    dest = dest_base.with_suffix(suffix)
    if dest.exists() and dest.stat().st_size > 100:
        return dest

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) < 100:
            return None
        dest.write_bytes(data)
        return dest
    except Exception as e:
        print(f"   ⚠️ Image non téléchargée: {e}")
        return None


def choose_soccer_team(data: dict) -> dict | None:
    teams = data.get("teams") or []
    if not isinstance(teams, list):
        return None

    soccer = [
        t for t in teams
        if isinstance(t, dict)
        and str(t.get("strSport") or "").lower() in {"soccer", "football"}
    ]
    return soccer[0] if soccer else (teams[0] if teams else None)


if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ Introuvable : {PRODUCTS_JSON}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ public/products.json doit contenir une liste.")

CLUBS_DIR.mkdir(parents=True, exist_ok=True)
LEAGUES_DIR.mkdir(parents=True, exist_ok=True)

mapping = {"clubs": {}, "leagues": {}}
resolved_clubs = []
unresolved_clubs = []
league_ids: dict[int, set[str]] = {}

# Unique club labels exactly as used by products.json
club_entries: dict[str, list[dict]] = {}
for p in products:
    if str(p.get("cat") or "").lower() != "clubs":
        continue

    raw_team = str(p.get("team") or "").strip()
    if not raw_team:
        continue

    club_entries.setdefault(raw_team, []).append(p)

print(f"🔎 Clubs uniques détectés : {len(club_entries)}")
print("")

query_cache: dict[str, dict | None] = {}

for index, (raw_team, team_products) in enumerate(sorted(club_entries.items()), 1):
    candidates = []

    cleaned = clean_team_guess(raw_team)
    if cleaned:
        candidates.append(cleaned)

    for p in team_products[:4]:
        by_name = guess_from_product_name(p.get("name") or "")
        if by_name:
            candidates.append(by_name)

    candidates.append(raw_team)

    # Unique candidates, best first.
    seen = set()
    candidates = [
        c for c in candidates
        if c and not (normalize_key(c) in seen or seen.add(normalize_key(c)))
    ]

    team = None
    used_query = ""

    print(f"[{index}/{len(club_entries)}] {raw_team}")

    for query in candidates:
        qkey = normalize_key(query)
        if qkey in query_cache:
            candidate_team = query_cache[qkey]
        else:
            try:
                data = api_json("searchteams.php", {"t": query})
                candidate_team = choose_soccer_team(data)
            except Exception as e:
                print(f"   ⚠️ API: {e}")
                candidate_team = None
            query_cache[qkey] = candidate_team

        if candidate_team and candidate_team.get("strBadge"):
            team = candidate_team
            used_query = query
            break

    if not team:
        print("   ❌ Logo introuvable")
        unresolved_clubs.append({
            "product_team": raw_team,
            "queries_tested": candidates,
        })
        continue

    official_name = str(team.get("strTeam") or used_query or raw_team)
    badge = str(team.get("strBadge") or "")

    path = download_image(
        badge,
        CLUBS_DIR / slugify(official_name),
    )

    if not path:
        print("   ❌ Badge introuvable")
        unresolved_clubs.append({
            "product_team": raw_team,
            "queries_tested": candidates,
            "api_team": official_name,
        })
        continue

    web_path = "/" + path.relative_to(PROJECT / "public").as_posix()

    # Map the original shop label AND API official label.
    mapping["clubs"][normalize_key(raw_team)] = web_path
    mapping["clubs"][normalize_key(cleaned)] = web_path
    mapping["clubs"][normalize_key(official_name)] = web_path

    league_id = str(team.get("idLeague") or "").strip()
    league_name = str(team.get("strLeague") or "").strip()
    if league_id.isdigit():
        league_ids.setdefault(int(league_id), set()).update(
            x for x in [league_name] if x
        )

    resolved_clubs.append({
        "product_team": raw_team,
        "search": used_query,
        "api_team": official_name,
        "logo": web_path,
        "league": league_name,
        "league_id": league_id,
    })
    print(f"   ✅ {official_name} -> {web_path}")


# Always install the five championship logos already used by the shop.
for site_name, league_id in KNOWN_LEAGUES.items():
    league_ids.setdefault(league_id, set()).add(site_name)

print("")
print(f"🏆 Championnats à installer : {len(league_ids)}")

resolved_leagues = []
unresolved_leagues = []

for index, (league_id, names) in enumerate(sorted(league_ids.items()), 1):
    print(f"[{index}/{len(league_ids)}] League ID {league_id}")
    try:
        data = api_json("lookupleague.php", {"id": league_id})
        leagues = data.get("leagues") or []
        league = leagues[0] if leagues else None
    except Exception as e:
        print(f"   ⚠️ API: {e}")
        league = None

    if not league:
        unresolved_leagues.append({"league_id": league_id, "names": sorted(names)})
        continue

    official_name = str(league.get("strLeague") or next(iter(names), league_id))
    badge = str(
        league.get("strBadge")
        or league.get("strLogo")
        or ""
    )

    path = download_image(
        badge,
        LEAGUES_DIR / slugify(official_name),
    )

    if not path:
        print(f"   ❌ Logo championnat introuvable : {official_name}")
        unresolved_leagues.append({
            "league_id": league_id,
            "names": sorted(names),
            "api_league": official_name,
        })
        continue

    web_path = "/" + path.relative_to(PROJECT / "public").as_posix()

    # API name
    mapping["leagues"][normalize_key(official_name)] = web_path

    # Names discovered from teams
    for name in names:
        mapping["leagues"][normalize_key(name)] = web_path

    # Site aliases
    for site_name, known_id in KNOWN_LEAGUES.items():
        if known_id == league_id:
            mapping["leagues"][normalize_key(site_name)] = web_path

    resolved_leagues.append({
        "league_id": league_id,
        "api_league": official_name,
        "names": sorted(names),
        "logo": web_path,
    })
    print(f"   ✅ {official_name} -> {web_path}")


MAPPING_JSON.write_text(
    json.dumps(mapping, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

report = {
    "products_count": len(products),
    "club_labels_count": len(club_entries),
    "clubs_installed": len(resolved_clubs),
    "clubs_unresolved": unresolved_clubs,
    "leagues_installed": len(resolved_leagues),
    "leagues_unresolved": unresolved_leagues,
    "resolved_clubs": resolved_clubs,
    "resolved_leagues": resolved_leagues,
}

REPORT_JSON.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("")
print("==============================================")
print("✅ INSTALLATION DES LOGOS TERMINÉE")
print(f"Clubs installés        : {len(resolved_clubs)}")
print(f"Clubs non trouvés      : {len(unresolved_clubs)}")
print(f"Championnats installés : {len(resolved_leagues)}")
print(f"Mapping                : {MAPPING_JSON}")
print(f"Rapport                : {REPORT_JSON}")
print("==============================================")
print("")
print("➡️ Ensuite fais Ctrl + F5 sur http://localhost:3000")
