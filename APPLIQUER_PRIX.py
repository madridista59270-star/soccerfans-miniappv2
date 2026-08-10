from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
PRODUCTS = PROJECT / "public" / "products.json"
PAGE = PROJECT / "app" / "page.js"

PRICES = {
    "fan": 35,
    "player": 45,
    "retro": 50,
    "rétro": 50,
    "enfant": 25,
    "kid": 25,
    "kids": 25,
}

def normalise(s):
    return str(s or "").strip().lower()

def update_products():
    if not PRODUCTS.exists():
        print(f"⚠ products.json introuvable : {PRODUCTS}")
        return 0

    backup = PRODUCTS.with_name("products.avant_prix.json")
    if not backup.exists():
        backup.write_bytes(PRODUCTS.read_bytes())

    data = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    changed = 0

    for product in data:
        versions = product.get("versions")
        if not isinstance(versions, dict):
            continue

        new_versions = {}
        product_changed = False

        for version, old_price in versions.items():
            key = normalise(version)
            new_price = PRICES.get(key, old_price)
            new_versions[version] = new_price
            if new_price != old_price:
                product_changed = True

        if product_changed:
            product["versions"] = new_versions
            changed += 1

    PRODUCTS.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return changed

def update_page():
    if not PAGE.exists():
        print(f"⚠ page.js introuvable : {PAGE}")
        return False

    text = PAGE.read_text(encoding="utf-8")
    original = text

    # Prix catalogue de secours
    text = re.sub(r'Enfant\s*:\s*30\b', 'Enfant:25', text)
    text = re.sub(r'Enfant\s*:\s*32\b', 'Enfant:25', text)

    # Anciennes valeurs éventuelles de versions
    text = re.sub(r'Fan\s*:\s*29\b', 'Fan:35', text)
    text = re.sub(r'Player\s*:\s*39\b', 'Player:45', text)
    text = re.sub(r'Rétro\s*:\s*34\b', 'Rétro:50', text)
    text = re.sub(r'Retro\s*:\s*34\b', 'Retro:50', text)

    # Fallback du bouton Ajouter
    text = text.replace('(selected.versions?.[version]||29)', '(selected.versions?.[version]||35)')

    # Le flocage reste à +3 €.
    if text != original:
        backup = PAGE.with_name("page.avant_prix.js")
        if not backup.exists():
            backup.write_text(original, encoding="utf-8")
        PAGE.write_text(text, encoding="utf-8")
        return True
    return False

def main():
    print("")
    print("SOCCER FANS — MISE À JOUR DES PRIX")
    print("----------------------------------")
    print("Fan     : 35 €")
    print("Player  : 45 €")
    print("Rétro   : 50 €")
    print("Enfant  : 25 €")
    print("Flocage : +3 €")
    print("")

    changed = update_products()
    page_changed = update_page()

    print(f"✅ Produits mis à jour : {changed}")
    print("✅ page.js vérifié" + (" et corrigé" if page_changed else ""))
    print("")
    print("Maintenant recharge le site avec Ctrl + F5.")
    print("")

if __name__ == "__main__":
    main()
