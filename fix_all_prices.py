from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

def pricing_for(name: str):
    low=(name or "").lower()

    # Priorité : Short > Enfant > Rétro > Player > Fan
    if re.search(r"\bshorts?\b", low):
        return {"Short": 20}
    if re.search(r"\b(kid|kids|child|children|youth|junior|enfant)\b", low):
        return {"Enfant": 30}
    if re.search(r"\b(retro|rétro|vintage|classic)\b", low):
        return {"Rétro": 50}
    if re.search(r"\bplayer\b", low):
        return {"Player": 45}
    if re.search(r"\bfan\b", low):
        return {"Fan": 35}
    return None

def main():
    ap = argparse.ArgumentParser(
        description="Corrige automatiquement les prix Short/Fan/Player/Rétro/Enfant dans products.json."
    )
    ap.add_argument("products_json", help="Chemin vers public/products.json")
    args = ap.parse_args()

    path = Path(args.products_json).expanduser().resolve()
    data = json.loads(path.read_text(encoding="utf-8"))

    counts = {"Short":0, "Enfant":0, "Rétro":0, "Player":0, "Fan":0}
    changed = 0

    for p in data:
        versions = pricing_for(str(p.get("name") or ""))
        if not versions:
            continue

        label = next(iter(versions.keys()))
        counts[label] += 1

        if p.get("versions") != versions:
            p["versions"] = versions
            changed += 1

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("")
    print("✅ Prix automatiques appliqués")
    print(f"Produits modifiés : {changed}")
    print(f"Short  20 € : {counts['Short']}")
    print(f"Fan    35 € : {counts['Fan']}")
    print(f"Player 45 € : {counts['Player']}")
    print(f"Rétro  50 € : {counts['Rétro']}")
    print(f"Enfant 30 € : {counts['Enfant']}")
    print("")
    print(path)

if __name__ == "__main__":
    main()
