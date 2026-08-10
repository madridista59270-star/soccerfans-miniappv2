from __future__ import annotations

import json
import mimetypes
import re
import shutil
import time
import urllib.parse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT = Path.cwd()
PRODUCTS_JSON = PROJECT / "public" / "products.json"
YUPOO_ROOT = Path(r"B:\yupoo_soccerfans_downloader\yupoo_images")
DEST_ROOT = PROJECT / "public" / "products"

HOST = "127.0.0.1"
PORT = 8770
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

if not PRODUCTS_JSON.exists():
    raise SystemExit(f"❌ Introuvable : {PRODUCTS_JSON}")
if not YUPOO_ROOT.exists():
    raise SystemExit(f"❌ Introuvable : {YUPOO_ROOT}")

products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
if not isinstance(products, list):
    raise SystemExit("❌ public/products.json doit contenir une liste.")

product_by_id = {str(p.get("id")): p for p in products if p.get("id") is not None}


def natural_key(path: Path):
    m = re.search(r"(\d+)", path.stem)
    return (int(m.group(1)) if m else 10**9, path.name.lower())


def find_album_folder(album_id: str) -> Path | None:
    matches = [p for p in YUPOO_ROOT.glob(f"{album_id}_*") if p.is_dir()]
    if matches:
        return matches[0]
    direct = YUPOO_ROOT / album_id
    return direct if direct.is_dir() else None


def album_images(album_id: str) -> list[Path]:
    folder = find_album_folder(album_id)
    if not folder:
        return []
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
        key=natural_key,
    )


def save_products():
    PRODUCTS_JSON.write_text(
        json.dumps(products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def shell(title: str, body: str) -> bytes:
    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<style>
:root{{--gold:#f4c542;--bg:#08090b;--card:#121318;--muted:#8e939d;--green:#55d17c}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:white;font-family:Arial,Helvetica,sans-serif}}
.wrap{{max-width:1250px;margin:auto;padding:18px}}
h1{{margin:8px 0 16px}}
a{{color:inherit;text-decoration:none}}
.notice{{padding:13px 15px;border:1px solid #303238;background:#121318;border-radius:14px;margin-bottom:16px;line-height:1.55}}
.gold{{color:var(--gold);font-weight:900}}
.search{{width:100%;padding:14px 16px;border-radius:14px;border:1px solid #333;background:#111;color:#fff;margin-bottom:16px}}
.products{{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:12px}}
.prod{{padding:14px;background:var(--card);border:1px solid #292b31;border-radius:15px}}
.prod:hover{{border-color:var(--gold)}}
.prod small{{display:block;color:var(--muted);margin-top:7px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}}
.card{{position:relative;border:2px solid #292b31;background:#111;border-radius:16px;overflow:hidden}}
.card.selected{{border-color:var(--gold);box-shadow:0 0 0 3px rgba(244,197,66,.15)}}
.card.primary{{border-color:#fff4b0;box-shadow:0 0 0 4px rgba(244,197,66,.3)}}
.card img{{display:block;width:100%;height:205px;object-fit:cover;background:white;cursor:pointer}}
.num{{position:absolute;top:8px;left:8px;z-index:4;padding:5px 8px;border-radius:999px;background:rgba(0,0,0,.75);font-weight:900}}
.card.selected .num{{background:var(--gold);color:#000}}
.controls{{padding:9px;display:grid;gap:7px}}
.state{{text-align:center;color:var(--muted);font-size:12px}}
.card.selected .state{{color:var(--green);font-weight:900}}
.mainbtn{{padding:9px;border-radius:10px;border:1px solid #555;background:#202126;color:#fff;font-weight:900;cursor:pointer}}
.card.primary .mainbtn{{background:var(--gold);color:#000;border-color:var(--gold)}}
.toolbar{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}}
.toolbtn{{padding:9px 12px;border-radius:10px;border:1px solid #444;background:#17181c;color:white;font-weight:800;cursor:pointer}}
.bar{{position:sticky;bottom:0;z-index:30;margin-top:18px;padding:14px;border-radius:16px;background:rgba(8,9,11,.97);border:1px solid #333;display:flex;gap:12px;align-items:center;justify-content:space-between}}
.save{{padding:13px 18px;border-radius:13px;border:0;background:var(--gold);color:#000;font-weight:950;cursor:pointer}}
.ok{{color:#7ee787;font-weight:950}}
</style>
</head>
<body><div class="wrap">{body}</div></body>
</html>"""
    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_html(self, title, body, status=200):
        data = shell(title, body)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qd = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            q = (qd.get("q", [""])[0] or "").strip().lower()
            cards = []
            for p in products:
                pid = str(p.get("id") or "")
                name = str(p.get("name") or "")
                if q and q not in name.lower():
                    continue
                n = len(album_images(pid))
                cards.append(
                    f'<a class="prod" href="/product?id={urllib.parse.quote(pid)}">'
                    f'<b>{escape(name)}</b>'
                    f'<small>{n} photo(s) disponibles dans Yupoo</small>'
                    f'</a>'
                )

            body = f"""
            <h1>Soccer Fans — sélection manuelle définitive</h1>
            <div class="notice">
              Tu choisis toi-même <b>exactement les photos à garder</b>.<br>
              Tu choisis aussi <b>la photo principale</b> qui apparaîtra sur la carte du catalogue et en photo 1.
            </div>
            <form method="get">
              <input class="search" name="q" value="{escape(q)}" placeholder="Rechercher Paris, Argentine, Maroc...">
            </form>
            <div class="products">{''.join(cards) or 'Aucun produit trouvé.'}</div>
            """
            self.send_html("Sélection photos", body)
            return

        if path == "/product":
            pid = (qd.get("id", [""])[0] or "").strip()
            p = product_by_id.get(pid)
            if not p:
                self.send_error(404)
                return

            imgs = album_images(pid)

            current_sources = [str(x) for x in (p.get("photo_source_names") or []) if x]
            current_main = str(p.get("main_source_name") or "")
            current_set = set(current_sources)

            tiles = []
            for i, img in enumerate(imgs):
                selected = img.name in current_set
                primary = img.name == current_main
                cls = "card" + (" selected" if selected else "") + (" primary" if primary else "")

                tiles.append(f"""
                <div class="{cls}" data-index="{i}">
                  <span class="num">{i+1}</span>
                  <input class="sel" type="checkbox" name="sel" value="{i}" style="display:none" {"checked" if selected else ""}>
                  <img class="photo" src="/img?id={urllib.parse.quote(pid)}&n={i}" alt="photo {i+1}">
                  <div class="controls">
                    <div class="state">{"✓ GARDÉE" if selected else "Cliquer pour garder"}</div>
                    <button type="button" class="mainbtn">⭐ PHOTO PRINCIPALE</button>
                  </div>
                </div>
                """)

            body = f"""
            <a href="/" class="gold">← Retour</a>
            <h1>{escape(str(p.get("name") or pid))}</h1>

            <div class="notice">
              <b>1.</b> Clique sur chaque photo que tu veux garder.<br>
              <b>2.</b> Sur le maillot de face que tu veux afficher en premier, clique sur <b>⭐ PHOTO PRINCIPALE</b>.<br>
              <b>3.</b> Ne sélectionne simplement pas les guides de tailles ou les doublons que tu ne veux pas.
            </div>

            <div class="toolbar">
              <button type="button" class="toolbtn" id="none">Tout désélectionner</button>
              <button type="button" class="toolbtn" id="all">Tout sélectionner</button>
            </div>

            <form method="post" action="/save?id={urllib.parse.quote(pid)}" id="form">
              <input type="hidden" name="main" id="mainInput" value="">
              <div class="grid">{''.join(tiles) or 'Aucune photo trouvée.'}</div>

              <div class="bar">
                <div>
                  <b id="count">0 photo sélectionnée</b><br>
                  <span id="mainStatus" class="gold">Aucune photo principale</span>
                </div>
                <button class="save" type="submit">ENREGISTRER</button>
              </div>
            </form>

            <script>
            const cards=[...document.querySelectorAll('.card')];
            const mainInput=document.getElementById('mainInput');
            const count=document.getElementById('count');
            const mainStatus=document.getElementById('mainStatus');

            const existingMain=cards.find(c=>c.classList.contains('primary'));
            if(existingMain){{
              mainInput.value=existingMain.dataset.index;
              mainStatus.textContent='⭐ Principale : photo '+(Number(existingMain.dataset.index)+1);
            }}

            function refresh(){{
              const selected=cards.filter(c=>c.querySelector('.sel').checked);
              count.textContent=selected.length+' photo(s) sélectionnée(s)';

              cards.forEach(c=>{{
                const on=c.querySelector('.sel').checked;
                c.classList.toggle('selected',on);
                c.querySelector('.state').textContent=on ? '✓ GARDÉE' : 'Cliquer pour garder';
              }});
            }}

            cards.forEach(card=>{{
              const box=card.querySelector('.sel');
              const photo=card.querySelector('.photo');
              const mainBtn=card.querySelector('.mainbtn');

              photo.addEventListener('click',()=>{{
                box.checked=!box.checked;

                if(!box.checked && mainInput.value===card.dataset.index){{
                  mainInput.value='';
                  card.classList.remove('primary');
                  mainStatus.textContent='Aucune photo principale';
                }}
                refresh();
              }});

              mainBtn.addEventListener('click',()=>{{
                box.checked=true;
                cards.forEach(c=>c.classList.remove('primary'));
                card.classList.add('primary');
                mainInput.value=card.dataset.index;
                mainStatus.textContent='⭐ Principale : photo '+(Number(card.dataset.index)+1);
                refresh();
              }});
            }});

            document.getElementById('none').addEventListener('click',()=>{{
              cards.forEach(c=>{{
                c.querySelector('.sel').checked=false;
                c.classList.remove('primary');
              }});
              mainInput.value='';
              mainStatus.textContent='Aucune photo principale';
              refresh();
            }});

            document.getElementById('all').addEventListener('click',()=>{{
              cards.forEach(c=>c.querySelector('.sel').checked=true);
              refresh();
            }});

            document.getElementById('form').addEventListener('submit',e=>{{
              const selected=cards.filter(c=>c.querySelector('.sel').checked);
              if(selected.length===0){{
                e.preventDefault();
                alert('Sélectionne au moins une photo.');
                return;
              }}
              if(mainInput.value===''){{
                e.preventDefault();
                alert('Choisis la photo principale.');
                return;
              }}
              const mainCard=cards.find(c=>c.dataset.index===mainInput.value);
              if(!mainCard || !mainCard.querySelector('.sel').checked){{
                e.preventDefault();
                alert('La photo principale doit être sélectionnée.');
              }}
            }});

            refresh();
            </script>
            """
            self.send_html("Choisir les photos", body)
            return

        if path == "/img":
            pid = (qd.get("id", [""])[0] or "").strip()
            try:
                n = int(qd.get("n", ["-1"])[0])
            except ValueError:
                n = -1

            imgs = album_images(pid)
            if n < 0 or n >= len(imgs):
                self.send_error(404)
                return

            img = imgs[n]
            data = img.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(img.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/save":
            self.send_error(404)
            return

        qd = urllib.parse.parse_qs(parsed.query)
        pid = (qd.get("id", [""])[0] or "").strip()
        p = product_by_id.get(pid)
        if not p:
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        form = urllib.parse.parse_qs(
            self.rfile.read(length).decode("utf-8", errors="replace")
        )

        selected_indices = []
        for raw in form.get("sel", []):
            try:
                selected_indices.append(int(raw))
            except ValueError:
                pass

        try:
            main_index = int((form.get("main", [""])[0] or "").strip())
        except ValueError:
            main_index = -1

        if not selected_indices or main_index not in selected_indices:
            self.send_html(
                "Erreur",
                f'<div class="notice">Sélection ou photo principale invalide.</div>'
                f'<p><a class="gold" href="/product?id={urllib.parse.quote(pid)}">← Retour</a></p>',
                400,
            )
            return

        # La principale est toujours la première, les autres gardent l'ordre Yupoo.
        selected_indices = sorted(set(selected_indices))
        ordered_indices = [main_index] + [i for i in selected_indices if i != main_index]

        imgs = album_images(pid)
        chosen = [imgs[i] for i in ordered_indices if 0 <= i < len(imgs)]

        if not chosen:
            self.send_error(400)
            return

        dest = DEST_ROOT / pid
        dest.mkdir(parents=True, exist_ok=True)

        # Supprime seulement les anciennes COPIES de la boutique pour ce produit.
        for old in dest.iterdir():
            if old.is_file() and old.suffix.lower() in IMAGE_EXTS:
                try:
                    old.unlink()
                except OSError:
                    pass

        stamp = int(time.time() * 1000)
        web_images = []
        source_names = []

        for pos, src in enumerate(chosen, 1):
            ext = src.suffix.lower()
            dst = dest / f"selected_{pos:03d}_{stamp}{ext}"
            shutil.copy2(src, dst)
            web_images.append(f"/products/{pid}/{dst.name}")
            source_names.append(src.name)

        p["image"] = web_images[0]
        p["images"] = web_images
        p["main_source_name"] = source_names[0]
        p["photo_source_names"] = source_names

        save_products()

        self.send_html(
            "Enregistré",
            f"""
            <div class="ok">✅ ENREGISTRÉ</div>
            <h1>{escape(str(p.get("name") or pid))}</h1>
            <div class="notice">
              Photos gardées : <b>{len(web_images)}</b><br>
              Photo principale : <b>{escape(source_names[0])}</b><br>
              Elle apparaîtra sur la carte du catalogue et en photo <b>1/{len(web_images)}</b>.
            </div>
            <p><a class="gold" href="/product?id={urllib.parse.quote(pid)}">← Modifier encore ce produit</a></p>
            <p><a class="gold" href="/">← Choisir un autre produit</a></p>
            <p>Ensuite fais <b>Ctrl + F5</b> sur <b>localhost:3000</b>.</p>
            """
        )


print("")
print("✅ Sélecteur manuel définitif prêt")
print(f"➡️ Ouvre : http://{HOST}:{PORT}")
print("➡️ Tu choisis les photos à garder + la photo principale.")
print("")

server = ThreadingHTTPServer((HOST, PORT), Handler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    print("\nArrêt.")
