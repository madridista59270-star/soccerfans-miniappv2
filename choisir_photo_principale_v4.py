from __future__ import annotations

import json
import mimetypes
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
PORT = 8767
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


def shell(title: str, body: str) -> bytes:
    html = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<style>
:root{{--gold:#f4c542;--bg:#08090b;--card:#121318;--muted:#8a8f98}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:white;font-family:Arial,Helvetica,sans-serif}}
.wrap{{max-width:1200px;margin:auto;padding:20px}}
a{{color:inherit;text-decoration:none}}
h1{{margin:8px 0 16px}}
.notice{{padding:13px 15px;border:1px solid #303238;background:#121318;border-radius:14px;margin-bottom:16px;line-height:1.5}}
.gold{{color:var(--gold);font-weight:900}}
.search{{width:100%;padding:14px 16px;border-radius:14px;border:1px solid #333;background:#111;color:#fff;margin-bottom:16px}}
.products{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}}
.prod{{padding:14px;background:var(--card);border:1px solid #292b31;border-radius:15px}}
.prod:hover{{border-color:var(--gold)}}
.prod small{{display:block;color:var(--muted);margin-top:7px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}}
.card{{border:2px solid #292b31;background:#111;border-radius:16px;overflow:hidden}}
.card img{{display:block;width:100%;height:200px;object-fit:cover;background:white}}
.meta{{padding:9px 10px;color:#aaa;font-size:12px}}
.choose{{display:block;width:calc(100% - 18px);margin:0 9px 10px;padding:11px 8px;border:0;border-radius:11px;background:var(--gold);color:#000;font-weight:950;cursor:pointer}}
.current{{border-color:var(--gold);box-shadow:0 0 0 3px rgba(244,197,66,.18)}}
.current .choose{{background:#fff1a8}}
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
                cards.append(
                    f'<a class="prod" href="/product?id={urllib.parse.quote(pid)}">'
                    f'<b>{escape(name)}</b>'
                    f'<small>Clique pour choisir la photo de face</small>'
                    f'</a>'
                )

            body = f"""
            <h1>Soccer Fans — photo principale</h1>
            <div class="notice">
              Ici tu choisis <b>uniquement la photo qui doit apparaître en premier</b>
              sur la carte du catalogue et en <b>1/5</b> dans la fiche produit.
            </div>
            <form method="get">
              <input class="search" name="q" value="{escape(q)}" placeholder="Rechercher Paris, Maroc, France...">
            </form>
            <div class="products">{''.join(cards) or 'Aucun produit trouvé.'}</div>
            """
            self.send_html("Photo principale", body)
            return

        if path == "/product":
            pid = (qd.get("id", [""])[0] or "").strip()
            p = product_by_id.get(pid)
            if not p:
                self.send_error(404)
                return

            imgs = album_images(pid)
            current_source = str(p.get("main_source_name") or "")
            cards = []

            for i, img in enumerate(imgs):
                current = " current" if img.name == current_source else ""
                cards.append(
                    f'<div class="card{current}">'
                    f'<img src="/img?id={urllib.parse.quote(pid)}&n={i}" alt="photo {i+1}">'
                    f'<div class="meta">Photo source : {escape(img.name)}</div>'
                    f'<form method="post" action="/set?id={urllib.parse.quote(pid)}&n={i}">'
                    f'<button class="choose" type="submit">'
                    f'{"✅ PHOTO PRINCIPALE" if current else "⭐ UTILISER EN PREMIER"}'
                    f'</button></form></div>'
                )

            body = f"""
            <a href="/" class="gold">← Retour</a>
            <h1>{escape(str(p.get("name") or pid))}</h1>
            <div class="notice">
              Repère le <b>maillot vu de face</b> puis clique simplement sur
              <b>⭐ UTILISER EN PREMIER</b>.<br>
              Pas besoin de resélectionner les 5 autres photos.
            </div>
            <div class="grid">{''.join(cards) or 'Aucune photo trouvée.'}</div>
            """
            self.send_html("Choisir la couverture", body)
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
        if parsed.path != "/set":
            self.send_error(404)
            return

        qd = urllib.parse.parse_qs(parsed.query)
        pid = (qd.get("id", [""])[0] or "").strip()
        try:
            n = int(qd.get("n", ["-1"])[0])
        except ValueError:
            n = -1

        p = product_by_id.get(pid)
        imgs = album_images(pid)
        if not p or n < 0 or n >= len(imgs):
            self.send_error(404)
            return

        src = imgs[n]
        dest_folder = DEST_ROOT / pid
        dest_folder.mkdir(parents=True, exist_ok=True)

        # Nom UNIQUE à chaque changement : aucun ancien cache navigateur possible.
        stamp = int(time.time() * 1000)
        ext = src.suffix.lower()
        cover_name = f"cover_{stamp}{ext}"
        cover_path = dest_folder / cover_name
        shutil.copy2(src, cover_path)

        cover_web = f"/products/{pid}/{cover_name}"

        # Supprime les anciennes couvertures générées, sauf celle qu'on vient de créer.
        for old in dest_folder.glob("cover_*"):
            if old != cover_path and old.is_file():
                try:
                    old.unlink()
                except OSError:
                    pass

        # La couverture est aussi forcée comme première photo de la galerie.
        old_images = [str(x) for x in (p.get("images") or []) if x]
        old_images = [
            x for x in old_images
            if "/cover_" not in x
            and x != cover_web
        ]
        p["image"] = cover_web
        p["images"] = [cover_web] + old_images[:4]
        p["main_source_name"] = src.name

        # Si V3 avait mémorisé les sources, on remet aussi celle-ci devant.
        source_names = [str(x) for x in (p.get("photo_source_names") or []) if x]
        source_names = [x for x in source_names if x != src.name]
        p["photo_source_names"] = [src.name] + source_names[:4]

        save_products()

        self.send_html(
            "Couverture enregistrée",
            f"""
            <div class="ok">✅ PHOTO PRINCIPALE MODIFIÉE</div>
            <h1>{escape(str(p.get("name") or pid))}</h1>
            <div class="notice">
              La photo <b>{escape(src.name)}</b> est maintenant forcée en premier.<br>
              Elle utilise un nouveau fichier <b>{escape(cover_name)}</b>,
              donc Chrome ne peut pas réutiliser l'ancienne image en cache.
            </div>
            <p><a class="gold" href="/product?id={urllib.parse.quote(pid)}">← Voir les photos de ce produit</a></p>
            <p><a class="gold" href="/">← Choisir un autre produit</a></p>
            <p>Ensuite retourne sur <b>localhost:3000</b> et fais <b>Ctrl + F5</b>.</p>
            """
        )


print("")
print("✅ Sélecteur couverture V4 prêt")
print(f"➡️ Ouvre : http://{HOST}:{PORT}")
print("➡️ Clique sur ⭐ UTILISER EN PREMIER sous le maillot vu de face")
print("")

server = ThreadingHTTPServer((HOST, PORT), Handler)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    print("\nArrêt.")
