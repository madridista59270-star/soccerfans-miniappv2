from __future__ import annotations

import json
import mimetypes
import shutil
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from html import escape

PROJECT = Path.cwd()
PRODUCTS_JSON = PROJECT / "public" / "products.json"
YUPOO_ROOT = Path(r"B:\yupoo_soccerfans_downloader\yupoo_images")
DEST_ROOT = PROJECT / "public" / "products"
HOST = "127.0.0.1"
PORT = 8765
MAX_SELECT = 5
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
    try:
        return (0, int(path.stem))
    except ValueError:
        return (1, path.name.lower())


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


def page_shell(title: str, body: str) -> bytes:
    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<style>
:root{{--gold:#f4c542;--bg:#08090b;--card:#121318;--text:#fff;--muted:#8b9099}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:Arial,Helvetica,sans-serif}}
.wrap{{max-width:1200px;margin:auto;padding:20px}}
h1,h2{{margin:0 0 16px}}
a{{color:inherit;text-decoration:none}}
.top{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px}}
.badge{{color:var(--gold);font-weight:900}}
.search{{width:100%;padding:14px 16px;border-radius:14px;border:1px solid #333;background:#111;color:#fff;margin-bottom:16px}}
.products{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}}
.prod{{border:1px solid #282a30;background:var(--card);padding:14px;border-radius:16px}}
.prod:hover{{border-color:var(--gold)}}
.prod small{{display:block;color:var(--muted);margin-top:8px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}}
.photo{{position:relative;border:2px solid #282a30;border-radius:16px;background:#111;overflow:hidden;cursor:pointer}}
.photo.selected{{border-color:var(--gold);box-shadow:0 0 0 3px rgba(244,197,66,.18)}}
.photo img{{display:block;width:100%;height:180px;object-fit:cover;background:#fff}}
.photo .num{{position:absolute;top:8px;left:8px;background:rgba(0,0,0,.75);color:#fff;border-radius:999px;padding:5px 8px;font-weight:900}}
.photo.selected .num{{background:var(--gold);color:#000}}
.bar{{position:sticky;bottom:0;margin-top:18px;padding:14px;border-radius:16px;background:rgba(8,9,11,.96);border:1px solid #333;display:flex;gap:10px;align-items:center;justify-content:space-between}}
button{{padding:13px 18px;border-radius:13px;border:0;font-weight:900;cursor:pointer}}
.save{{background:var(--gold);color:#000}}
.back{{background:#202126;color:#fff}}
.notice{{padding:12px 14px;border-radius:12px;background:#121318;border:1px solid #2b2d33;margin-bottom:16px;color:#ddd}}
.ok{{color:#7ee787;font-weight:900}}
.err{{color:#ff7b72;font-weight:900}}
</style>
</head>
<body>
<div class="wrap">{body}</div>
</body>
</html>"""
    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_html(self, title: str, body: str, status=200):
        data = page_shell(title, body)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            q = (query.get("q", [""])[0] or "").strip().lower()
            cards = []
            for p in products:
                pid = str(p.get("id") or "")
                name = str(p.get("name") or "")
                if q and q not in name.lower():
                    continue
                imgs = album_images(pid)
                cards.append(
                    f'<a class="prod" href="/product?id={urllib.parse.quote(pid)}">'
                    f'<b>{escape(name)}</b>'
                    f'<small>ID {escape(pid)} • {len(imgs)} photo(s) disponibles</small>'
                    f'</a>'
                )

            body = f"""
            <div class="top">
              <div><h1>Soccer Fans — sélection manuelle</h1><div class="badge">Choisis jusqu'à 5 photos par produit</div></div>
            </div>
            <form method="get">
              <input class="search" name="q" value="{escape(q)}" placeholder="Rechercher un produit...">
            </form>
            <div class="products">{''.join(cards) or '<div>Aucun produit trouvé.</div>'}</div>
            """
            self.send_html("Sélection photos", body)
            return

        if path == "/product":
            pid = (query.get("id", [""])[0] or "").strip()
            p = product_by_id.get(pid)
            if not p:
                self.send_html("Introuvable", '<div class="err">Produit introuvable.</div>', 404)
                return

            imgs = album_images(pid)
            current = set()
            for webp in p.get("images") or []:
                current.add(Path(str(webp)).name)

            tiles = []
            for i, img in enumerate(imgs):
                img_url = f"/img?id={urllib.parse.quote(pid)}&n={i}"
                selected = " selected" if img.name in current else ""
                tiles.append(
                    f'<label class="photo{selected}" data-index="{i}">'
                    f'<input type="checkbox" name="sel" value="{i}" style="display:none" {"checked" if selected else ""}>'
                    f'<span class="num">{i+1}</span>'
                    f'<img src="{img_url}" alt="photo {i+1}">'
                    f'</label>'
                )

            body = f"""
            <div class="top">
              <div>
                <a href="/" class="badge">← Retour aux produits</a>
                <h1 style="margin-top:8px">{escape(str(p.get("name") or pid))}</h1>
              </div>
            </div>
            <div class="notice">
              Clique sur les photos que tu veux garder. Maximum <b>5</b>.
              La première sélectionnée deviendra la photo principale.
            </div>
            <form method="post" action="/save?id={urllib.parse.quote(pid)}" id="f">
              <div class="grid">{''.join(tiles) or '<div class="err">Aucune image trouvée dans cet album.</div>'}</div>
              <div class="bar">
                <span id="count">0 / 5 sélectionnées</span>
                <div>
                  <a href="/"><button type="button" class="back">Annuler</button></a>
                  <button class="save" type="submit">Enregistrer les 5 photos</button>
                </div>
              </div>
            </form>
            <script>
            const boxes=[...document.querySelectorAll('input[name="sel"]')];
            const count=document.getElementById('count');
            function refresh(){{
              let n=boxes.filter(b=>b.checked).length;
              count.textContent=n+' / 5 sélectionnées';
              boxes.forEach(b=>b.closest('.photo').classList.toggle('selected',b.checked));
            }}
            boxes.forEach(b=>{{
              b.addEventListener('change',e=>{{
                if(boxes.filter(x=>x.checked).length>5){{
                  b.checked=false;
                  alert('Maximum 5 photos.');
                }}
                refresh();
              }});
            }});
            document.querySelectorAll('.photo').forEach(l=>{{
              l.addEventListener('click',e=>{{
                if(e.target.tagName==='INPUT') return;
              }});
            }});
            refresh();
            </script>
            """
            self.send_html("Choisir les photos", body)
            return

        if path == "/img":
            pid = (query.get("id", [""])[0] or "").strip()
            try:
                n = int(query.get("n", ["-1"])[0])
            except ValueError:
                n = -1

            imgs = album_images(pid)
            if n < 0 or n >= len(imgs):
                self.send_error(404)
                return

            img = imgs[n]
            data = img.read_bytes()
            ctype = mimetypes.guess_type(img.name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
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

        query = urllib.parse.parse_qs(parsed.query)
        pid = (query.get("id", [""])[0] or "").strip()
        p = product_by_id.get(pid)
        if not p:
            self.send_html("Introuvable", '<div class="err">Produit introuvable.</div>', 404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        form = urllib.parse.parse_qs(body)
        raw_sel = form.get("sel", [])

        indices = []
        for x in raw_sel:
            try:
                indices.append(int(x))
            except ValueError:
                pass

        indices = indices[:MAX_SELECT]
        imgs = album_images(pid)

        chosen = [imgs[i] for i in indices if 0 <= i < len(imgs)]
        if not chosen:
            self.send_html(
                "Erreur",
                f'<div class="err">Tu dois sélectionner au moins une photo.</div><p><a href="/product?id={urllib.parse.quote(pid)}">← Retour</a></p>',
                400,
            )
            return

        dest_folder = DEST_ROOT / pid
        dest_folder.mkdir(parents=True, exist_ok=True)

        # Nettoie uniquement les copies de la boutique pour ce produit.
        for old in dest_folder.iterdir():
            if old.is_file() and old.suffix.lower() in IMAGE_EXTS:
                old.unlink()

        web_images = []
        for n, src in enumerate(chosen, 1):
            ext = src.suffix.lower()
            dst = dest_folder / f"{n:03d}{ext}"
            shutil.copy2(src, dst)
            web_images.append(f"/products/{pid}/{dst.name}")

        p["image"] = web_images[0]
        p["images"] = web_images
        save_products()

        self.send_html(
            "Enregistré",
            f"""
            <div class="ok">✅ Photos enregistrées pour :</div>
            <h1>{escape(str(p.get("name") or pid))}</h1>
            <p>{len(web_images)} photo(s) sélectionnée(s).</p>
            <p><a class="badge" href="/product?id={urllib.parse.quote(pid)}">← Modifier encore</a></p>
            <p><a class="badge" href="/">← Choisir un autre produit</a></p>
            """
        )


print("")
print("✅ Sélecteur manuel prêt")
print(f"➡️ Ouvre dans ton navigateur : http://{HOST}:{PORT}")
print("➡️ Pour arrêter : Ctrl + C dans PowerShell")
print("")

server = ThreadingHTTPServer((HOST, PORT), Handler)

try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    print("\nArrêt du sélecteur.")
