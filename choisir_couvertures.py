from __future__ import annotations

import json
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from PIL import Image, ImageTk

CATALOGUE = Path(r"B:\yupoo_soccerfans_downloader\yupoo_images\catalogue.json")
PROJECT = Path(r"C:\Users\guillaume\Documents\GitHub\soccerfans-miniappv2")
PRODUCTS_JSON = PROJECT / "public" / "products.json"
PRODUCTS_DIR = PROJECT / "public" / "products"
BACKUP_JSON = PROJECT / "public" / "products.before_manual_covers.json"

THUMBS_PER_PAGE = 12
THUMB_SIZE = (155, 155)
PREVIEW_SIZE = (430, 430)

def resolve_source(raw: str, catalogue: Path) -> Path | None:
    if not raw:
        return None
    p = Path(raw)
    candidates = []
    if p.is_absolute():
        candidates.append(p)
    else:
        candidates.extend([
            catalogue.parent.parent / p,
            catalogue.parent / p,
            catalogue.parent / p.name,
        ])
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None

def fit_image(path: Path, size: tuple[int, int], bg="white") -> Image.Image:
    with Image.open(path) as im0:
        im = im0.convert("RGB")
        im.thumbnail(size, Image.LANCZOS)
        canvas = Image.new("RGB", size, bg)
        x = (size[0] - im.width) // 2
        y = (size[1] - im.height) // 2
        canvas.paste(im, (x, y))
        return canvas

class CoverSelector:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Soccer Fans — Choisir les photos de couverture")
        self.root.geometry("1260x820")
        self.root.minsize(1100, 720)

        if not CATALOGUE.exists():
            messagebox.showerror("Erreur", f"Catalogue introuvable :\n{CATALOGUE}")
            root.destroy()
            return
        if not PRODUCTS_JSON.exists():
            messagebox.showerror("Erreur", f"products.json introuvable :\n{PRODUCTS_JSON}")
            root.destroy()
            return

        self.catalogue = json.loads(CATALOGUE.read_text(encoding="utf-8"))
        self.products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))

        # Sauvegarde de sécurité une seule fois.
        if not BACKUP_JSON.exists():
            shutil.copy2(PRODUCTS_JSON, BACKUP_JSON)

        self.product_by_id = {str(p.get("id")): p for p in self.products}
        self.entries = []
        seen = set()

        for e in self.catalogue:
            album_id = str(e.get("album_id") or "").strip()
            if not album_id or album_id in seen or album_id not in self.product_by_id:
                continue
            seen.add(album_id)

            raws = list(e.get("images") or [])
            if e.get("cover") and e["cover"] not in raws:
                raws.insert(0, e["cover"])

            imgs = []
            used = set()
            for raw in raws:
                src = resolve_source(str(raw), CATALOGUE)
                if src:
                    key = str(src).lower()
                    if key not in used:
                        used.add(key)
                        imgs.append(src)

            if imgs:
                self.entries.append({
                    "id": album_id,
                    "title": str(e.get("title") or album_id),
                    "images": imgs,
                })

        if not self.entries:
            messagebox.showerror("Erreur", "Aucun album exploitable trouvé.")
            root.destroy()
            return

        self.product_index = 0
        self.image_page = 0
        self.selected_path: Path | None = None
        self.thumb_refs = []
        self.preview_ref = None

        self.build_ui()
        self.show_product()

    def build_ui(self):
        top = tk.Frame(self.root, padx=12, pady=10)
        top.pack(fill="x")

        self.progress = tk.Label(top, font=("Segoe UI", 11, "bold"))
        self.progress.pack(side="left")

        self.title_label = tk.Label(
            self.root, text="", font=("Segoe UI", 18, "bold"),
            anchor="w", padx=14, pady=8
        )
        self.title_label.pack(fill="x")

        body = tk.Frame(self.root, padx=12, pady=6)
        body.pack(fill="both", expand=True)

        # Galerie gauche
        left = tk.Frame(body)
        left.pack(side="left", fill="both", expand=True)

        gallery_nav = tk.Frame(left)
        gallery_nav.pack(fill="x", pady=(0, 8))

        tk.Button(
            gallery_nav, text="◀ Photos précédentes",
            command=self.prev_image_page, padx=12, pady=7
        ).pack(side="left")

        self.page_label = tk.Label(gallery_nav, font=("Segoe UI", 10, "bold"))
        self.page_label.pack(side="left", padx=16)

        tk.Button(
            gallery_nav, text="Photos suivantes ▶",
            command=self.next_image_page, padx=12, pady=7
        ).pack(side="left")

        self.gallery = tk.Frame(left)
        self.gallery.pack(fill="both", expand=True)

        # Aperçu droite
        right = tk.Frame(body, width=460, padx=15)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right, text="APERÇU", font=("Segoe UI", 12, "bold")
        ).pack(pady=(4, 8))

        self.preview_label = tk.Label(
            right, text="Clique sur une photo",
            width=54, height=27, relief="groove", bd=1
        )
        self.preview_label.pack()

        self.selected_info = tk.Label(
            right, text="", wraplength=420,
            font=("Segoe UI", 10), pady=8
        )
        self.selected_info.pack(fill="x")

        self.validate_btn = tk.Button(
            right,
            text="✅ VALIDER CETTE PHOTO",
            command=self.validate_cover,
            state="disabled",
            font=("Segoe UI", 12, "bold"),
            padx=12, pady=13
        )
        self.validate_btn.pack(fill="x", pady=(8, 10))

        tk.Button(
            right,
            text="Ouvrir le dossier de cet album",
            command=self.open_album_folder,
            padx=10, pady=8
        ).pack(fill="x", pady=4)

        # Navigation produits
        bottom = tk.Frame(self.root, padx=12, pady=12)
        bottom.pack(fill="x")

        tk.Button(
            bottom, text="◀ Produit précédent",
            command=self.prev_product, padx=14, pady=9
        ).pack(side="left")

        tk.Button(
            bottom, text="Passer sans modifier",
            command=self.skip_product, padx=14, pady=9
        ).pack(side="left", padx=10)

        tk.Button(
            bottom, text="Produit suivant ▶",
            command=self.next_product, padx=14, pady=9
        ).pack(side="right")

        tk.Label(
            bottom,
            text="Astuce : choisis une vue de face complète, pas un logo, une étiquette ou un gros plan.",
            font=("Segoe UI", 10)
        ).pack(side="right", padx=18)

    def current_entry(self):
        return self.entries[self.product_index]

    def show_product(self):
        entry = self.current_entry()
        self.selected_path = None
        self.image_page = 0
        self.validate_btn.config(state="disabled")
        self.preview_label.config(image="", text="Clique sur une photo")
        self.preview_ref = None
        self.selected_info.config(text="")

        self.progress.config(
            text=f"Produit {self.product_index + 1} / {len(self.entries)}"
        )
        self.title_label.config(text=entry["title"])
        self.render_gallery()

    def render_gallery(self):
        for w in self.gallery.winfo_children():
            w.destroy()
        self.thumb_refs.clear()

        imgs = self.current_entry()["images"]
        total_pages = max(1, (len(imgs) + THUMBS_PER_PAGE - 1) // THUMBS_PER_PAGE)
        self.image_page = max(0, min(self.image_page, total_pages - 1))
        start = self.image_page * THUMBS_PER_PAGE
        batch = imgs[start:start + THUMBS_PER_PAGE]

        self.page_label.config(
            text=f"Photos {start + 1}–{min(start + len(batch), len(imgs))} / {len(imgs)}"
        )

        for idx, path in enumerate(batch):
            absolute_index = start + idx
            cell = tk.Frame(self.gallery, padx=5, pady=5)
            cell.grid(row=idx // 4, column=idx % 4, sticky="nsew")
            self.gallery.grid_columnconfigure(idx % 4, weight=1)

            try:
                img = fit_image(path, THUMB_SIZE)
                photo = ImageTk.PhotoImage(img)
                self.thumb_refs.append(photo)
                btn = tk.Button(
                    cell, image=photo,
                    command=lambda p=path, i=absolute_index: self.select_image(p, i),
                    bd=2, relief="raised"
                )
                btn.pack()
            except Exception:
                tk.Button(
                    cell, text="Image illisible", width=20, height=8,
                    command=lambda p=path, i=absolute_index: self.select_image(p, i)
                ).pack()

            tk.Label(
                cell, text=f"{absolute_index + 1:03d} — {path.name}",
                font=("Segoe UI", 9)
            ).pack(pady=(3, 0))

    def select_image(self, path: Path, index: int):
        self.selected_path = path
        try:
            img = fit_image(path, PREVIEW_SIZE)
            self.preview_ref = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.preview_ref, text="")
        except Exception as e:
            self.preview_label.config(image="", text=f"Impossible d'afficher : {e}")

        self.selected_info.config(
            text=f"Photo choisie : {index + 1:03d}\n{path.name}"
        )
        self.validate_btn.config(state="normal")

    def validate_cover(self):
        if not self.selected_path:
            return

        entry = self.current_entry()
        album_id = entry["id"]
        product = self.product_by_id.get(album_id)
        if not product:
            messagebox.showerror("Erreur", f"Produit {album_id} absent de products.json")
            return

        dest_dir = PRODUCTS_DIR / album_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Couverture dédiée : on ne détruit pas les anciennes images.
        for old in dest_dir.glob("cover.*"):
            try:
                old.unlink()
            except OSError:
                pass

        ext = self.selected_path.suffix.lower() or ".jpg"
        dest = dest_dir / f"cover{ext}"
        shutil.copy2(self.selected_path, dest)

        web_path = f"/products/{album_id}/{dest.name}"
        product["image"] = web_path

        old_images = list(product.get("images") or [])
        product["images"] = [web_path] + [x for x in old_images if x != web_path]

        # Sauvegarde après CHAQUE choix.
        PRODUCTS_JSON.write_text(
            json.dumps(self.products, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        if self.product_index < len(self.entries) - 1:
            self.product_index += 1
            self.show_product()
        else:
            messagebox.showinfo(
                "Terminé",
                "Toutes les couvertures ont été parcourues.\n\n"
                "Recharge maintenant http://localhost:3000 avec Ctrl + F5."
            )

    def prev_image_page(self):
        if self.image_page > 0:
            self.image_page -= 1
            self.render_gallery()

    def next_image_page(self):
        imgs = self.current_entry()["images"]
        max_page = max(0, (len(imgs) - 1) // THUMBS_PER_PAGE)
        if self.image_page < max_page:
            self.image_page += 1
            self.render_gallery()

    def prev_product(self):
        if self.product_index > 0:
            self.product_index -= 1
            self.show_product()

    def next_product(self):
        if self.product_index < len(self.entries) - 1:
            self.product_index += 1
            self.show_product()

    def skip_product(self):
        self.next_product()

    def open_album_folder(self):
        entry = self.current_entry()
        if entry["images"]:
            folder = entry["images"][0].parent
            try:
                import os
                os.startfile(folder)
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

if __name__ == "__main__":
    app_root = tk.Tk()
    CoverSelector(app_root)
    app_root.mainloop()
