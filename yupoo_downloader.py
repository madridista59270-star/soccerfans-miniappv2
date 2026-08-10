from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlparse,
    urlsplit,
    urlunsplit,
)

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


ALBUM_RE = re.compile(r"/albums/(\d+)")
CATEGORY_RE = re.compile(r"/categories/(\d+)")
IMAGE_EXT_RE = re.compile(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", re.I)

DELETED_MARKERS = (
    "该相册已不存在",        # Cet album n'existe plus
    "相册不存在",
    "album does not exist",
    "album doesn't exist",
    "album not found",
    "this album does not exist",
    "page not found",
    "404 not found",
)

PROTECTED_MARKERS = (
    "access code",
    "password incorrect",
    "请输入访问密码",
    "请输入密码",
    "captcha",
    "verification",
)


def clean_name(name: str, fallback: str = "album") -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name)
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name[:120] or fallback


def unique_keep_order(items):
    out, seen = [], set()
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def add_or_replace_query(url: str, **params) -> str:
    """Ajoute/remplace proprement des paramètres de requête."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in params.items():
        query[key] = str(value)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def best_from_srcset(srcset: str) -> str | None:
    if not srcset:
        return None

    candidates = []
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue

        url = bits[0]
        score = 0
        if len(bits) > 1:
            m = re.match(r"(\d+)(w|x)", bits[1])
            if m:
                score = int(m.group(1))

        candidates.append((score, url))

    if not candidates:
        return None

    return max(candidates, key=lambda x: x[0])[1]


def page_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=3000).strip()
    except Exception:
        return ""


def album_state(page) -> str:
    """Retourne: ok / deleted / protected."""
    body = page_text(page).lower()

    if any(marker.lower() in body for marker in DELETED_MARKERS):
        return "deleted"

    if any(marker.lower() in body for marker in PROTECTED_MARKERS):
        return "protected"

    return "ok"


def album_title(page, album_id: str) -> str:
    selectors = [
        ".showalbumheader__gallerytitle",
        ".showalbumheader__title",
        "h1",
        "[class*='showalbum'] [class*='title']",
        "[class*='album'] h1",
    ]

    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count():
                txt = loc.inner_text(timeout=1500).strip()
                if 2 <= len(txt) <= 160 and not any(
                    marker.lower() in txt.lower() for marker in DELETED_MARKERS
                ):
                    return clean_name(txt, f"album-{album_id}")
        except Exception:
            pass

    try:
        title = page.title().strip()
        if title:
            title = re.sub(r"\s*\|\s*Supplier.*$", "", title, flags=re.I)
            if not any(marker.lower() in title.lower() for marker in DELETED_MARKERS):
                return clean_name(title, f"album-{album_id}")
    except Exception:
        pass

    return f"album-{album_id}"


def visible_album_hrefs(page) -> list[str]:
    """
    Récupère uniquement les liens d'albums réellement visibles dans le catalogue.
    Cela évite les vieux liens cachés / éléments de navigation.
    """
    try:
        return page.locator('a[href*="/albums/"]:visible').evaluate_all(
            """els => els
                .map(a => a.href || '')
                .filter(Boolean)"""
        )
    except Exception:
        # Fallback JS si :visible n'est pas disponible pour une raison quelconque.
        return page.locator('a[href*="/albums/"]').evaluate_all(
            """els => els
                .filter(a => !!(a.offsetWidth || a.offsetHeight || a.getClientRects().length))
                .map(a => a.href || '')
                .filter(Boolean)"""
        )


def collect_album_links(
    page,
    base_url: str,
    max_pages: int,
    max_albums: int = 0,
) -> list[str]:
    album_links = []
    seen_ids = set()

    base_host = urlparse(base_url).netloc.lower()
    category_m = CATEGORY_RE.search(base_url)
    category_id = category_m.group(1) if category_m else None

    for page_no in range(1, max_pages + 1):
        url = base_url if page_no == 1 else add_or_replace_query(base_url, page=page_no)
        print(f"[CATALOGUE] page {page_no}: {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                page.wait_for_selector('a[href*="/albums/"]', timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(1800)
        except PlaywrightTimeoutError:
            print("  ⚠️ délai dépassé, tentative de lecture du contenu chargé")

        # Si Yupoo affiche une page protégée/erreur au lieu du catalogue, on stoppe.
        state = album_state(page)
        if state == "protected":
            print("  🔒 catalogue protégé / vérification détectée")
            break
        if state == "deleted":
            print("  ❌ page catalogue invalide")
            break

        hrefs = visible_album_hrefs(page)

        # Ne garder que les albums du même sous-domaine.
        hrefs = [
            h for h in hrefs
            if urlparse(h).netloc.lower() in ("", base_host)
        ]

        # Sur une page de catégorie Yupoo, les vrais produits portent souvent
        # referrercate=<id>. Si ces liens existent, on les privilégie.
        if category_id:
            preferred = [
                h for h in hrefs
                if f"referrercate={category_id}" in h
            ]
            if preferred:
                hrefs = preferred

        new_count = 0

        for href in hrefs:
            m = ALBUM_RE.search(href)
            if not m:
                continue

            album_id = m.group(1)
            if album_id in seen_ids:
                continue

            seen_ids.add(album_id)

            # Conserver l'URL de Yupoo telle qu'elle est fournie par le catalogue
            # (paramètres uid/referrercate inclus si présents).
            normalized = urljoin(base_url, href)
            album_links.append(normalized)
            new_count += 1

            if max_albums > 0 and len(album_links) >= max_albums:
                print(
                    f"  → test limité à {max_albums} album(s), "
                    "arrêt de l'analyse du catalogue"
                )
                return album_links

        print(f"  → {new_count} nouveaux albums visibles")

        # Si aucune nouveauté à partir de la page 2, on considère la pagination finie.
        if page_no > 1 and new_count == 0:
            break

    return album_links


def scroll_album(page):
    """Déclenche le chargement paresseux des images d'un album."""
    try:
        page.evaluate(
            """async () => {
                await new Promise(resolve => {
                    let total = 0;
                    const step = Math.max(500, Math.floor(window.innerHeight * 0.8));
                    const timer = setInterval(() => {
                        window.scrollBy(0, step);
                        total += step;
                        const maxScroll = Math.max(
                            document.body.scrollHeight,
                            document.documentElement.scrollHeight
                        );
                        if (window.scrollY + window.innerHeight >= maxScroll - 50 || total > 50000) {
                            clearInterval(timer);
                            setTimeout(resolve, 500);
                        }
                    }, 120);
                });
            }"""
        )
    except Exception:
        pass

    try:
        page.evaluate("window.scrollTo(0, 0)")
    except Exception:
        pass


def collect_image_urls(page) -> list[str]:
    # On privilégie la zone album, puis fallback sur toutes les images.
    selectors = [
        ".showalbum__children img",
        ".showalbum__image img",
        "[class*='showalbum'] img",
        "main img",
    ]

    locator = None
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                locator = loc
                break
        except Exception:
            pass

    if locator is None:
        locator = page.locator("img")

    data = locator.evaluate_all(
        """imgs => imgs.map(img => ({
            src: img.getAttribute('src') || '',
            currentSrc: img.currentSrc || '',
            dataSrc: img.getAttribute('data-src') || '',
            dataOrigin: img.getAttribute('data-origin') || '',
            dataOriginSrc: img.getAttribute('data-origin-src') || '',
            dataOriginal: img.getAttribute('data-original') || '',
            dataOriginalSrc: img.getAttribute('data-original-src') || '',
            dataLazy: img.getAttribute('data-lazy') || '',
            dataLazySrc: img.getAttribute('data-lazy-src') || '',
            dataUrl: img.getAttribute('data-url') || '',
            srcset: img.getAttribute('srcset') || ''
        }))"""
    )

    urls = []

    preferred_keys = (
        "dataOrigin",
        "dataOriginSrc",
        "dataOriginal",
        "dataOriginalSrc",
        "dataSrc",
        "dataLazy",
        "dataLazySrc",
        "dataUrl",
        "currentSrc",
        "src",
    )

    for item in data:
        for key in preferred_keys:
            u = (item.get(key) or "").strip()

            if u.startswith("//"):
                u = "https:" + u
            elif u.startswith("/"):
                u = urljoin(page.url, u)

            if u.startswith("http") and IMAGE_EXT_RE.search(u):
                urls.append(u)

        ss = best_from_srcset(item.get("srcset", ""))
        if ss:
            if ss.startswith("//"):
                ss = "https:" + ss
            elif ss.startswith("/"):
                ss = urljoin(page.url, ss)

            if ss.startswith("http") and IMAGE_EXT_RE.search(ss):
                urls.append(ss)

    banned = (
        "logo",
        "avatar",
        "qrcode",
        "qr-code",
        "icon",
        "favicon",
        "loading",
        "placeholder",
    )

    result = []
    seen = set()

    for u in urls:
        low = u.lower()

        if any(x in low for x in banned):
            continue

        # Déduplique exactement l'URL sans casser les paramètres CDN nécessaires.
        if u in seen:
            continue

        seen.add(u)
        result.append(u)

    return result


def download_image(
    session: requests.Session,
    url: str,
    dest: Path,
    referer: str,
) -> bool:
    headers = {
        "Referer": referer,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/127.0 Safari/537.36"
        ),
    }

    try:
        with session.get(url, headers=headers, timeout=30, stream=True) as r:
            r.raise_for_status()

            ctype = (r.headers.get("content-type") or "").lower()
            if "image" not in ctype:
                return False

            with dest.open("wb") as f:
                for chunk in r.iter_content(1024 * 128):
                    if chunk:
                        f.write(chunk)

        return dest.stat().st_size > 1000

    except Exception as e:
        print(f"    ❌ {url}: {e}")
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False


def write_manifest(out_root: Path, manifest: list[dict]):
    (out_root / "catalogue.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Télécharge les images d'albums Yupoo publics, "
            "sans contourner mots de passe ni CAPTCHA."
        )
    )

    ap.add_argument(
        "url",
        nargs="?",
        default="https://ezfashion.x.yupoo.com/albums/",
        help="URL de la page albums/catégorie Yupoo",
    )
    ap.add_argument("--out", default="yupoo_images", help="Dossier de sortie")
    ap.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Pages catalogue max",
    )
    ap.add_argument(
        "--max-albums",
        type=int,
        default=0,
        help="0 = tous les albums détectés",
    )
    ap.add_argument(
        "--delay",
        type=float,
        default=1.2,
        help="Pause entre albums (secondes)",
    )

    args = ap.parse_args()

    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    manifest = []
    session = requests.Session()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            viewport={"width": 1365, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/127.0 Safari/537.36"
            ),
            locale="fr-FR",
        )

        page = context.new_page()

        print("Recherche des albums…")
        album_links = collect_album_links(
            page,
            args.url,
            args.max_pages,
            args.max_albums,
        )

        if args.max_albums > 0:
            album_links = album_links[: args.max_albums]

        print(f"\n✅ {len(album_links)} album(s) détecté(s)\n")

        for idx, album_url in enumerate(album_links, 1):
            album_id_m = ALBUM_RE.search(album_url)
            album_id = album_id_m.group(1) if album_id_m else str(idx)

            print(f"[{idx}/{len(album_links)}] {album_url}")

            try:
                page.goto(
                    album_url,
                    wait_until="domcontentloaded",
                    timeout=45000,
                )
                page.wait_for_timeout(1200)
            except PlaywrightTimeoutError:
                print("  ⚠️ délai dépassé, analyse du contenu déjà chargé")

            state = album_state(page)

            if state == "deleted":
                print("  🗑️ album supprimé / inexistant : ignoré")
                continue

            if state == "protected":
                print("  🔒 album protégé / vérification détectée : ignoré")
                continue

            scroll_album(page)
            page.wait_for_timeout(700)

            # Vérification une seconde fois après rendu complet.
            state = album_state(page)
            if state == "deleted":
                print("  🗑️ album supprimé / inexistant : ignoré")
                continue
            if state == "protected":
                print("  🔒 album protégé / vérification détectée : ignoré")
                continue

            title = album_title(page, album_id)

            image_urls = collect_image_urls(page)
            print(f"  → {len(image_urls)} image(s) détectée(s)")

            # Une page d'erreur ou une page non-album peut parfois contenir
            # une image d'interface. On n'enregistre rien si aucun média valable.
            if not image_urls:
                print("  ⚠️ aucune image produit détectée : album ignoré")
                continue

            folder = out_root / f"{album_id}_{title}"
            folder.mkdir(parents=True, exist_ok=True)

            downloaded = []

            for n, image_url in enumerate(image_urls, 1):
                ext = Path(urlparse(image_url).path).suffix.lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                    ext = ".jpg"

                dest = folder / f"{n:03d}{ext}"

                if download_image(session, image_url, dest, page.url):
                    downloaded.append(str(dest.as_posix()))
                    print(f"    ✓ {dest.name}")

            if not downloaded:
                print("  ⚠️ aucune image téléchargée : dossier supprimé")
                try:
                    folder.rmdir()
                except OSError:
                    pass
                continue

            manifest.append(
                {
                    "album_id": album_id,
                    "title": title,
                    "url": page.url,
                    "folder": str(folder.as_posix()),
                    "images": downloaded,
                    "cover": downloaded[0] if downloaded else None,
                }
            )

            write_manifest(out_root, manifest)
            time.sleep(max(0.0, args.delay))

        browser.close()

    # Crée quand même un catalogue vide si aucun album valide n'a été trouvé.
    if not (out_root / "catalogue.json").exists():
        write_manifest(out_root, manifest)

    print("\nTerminé.")
    print(f"Images : {out_root.resolve()}")
    print(f"Catalogue : {(out_root / 'catalogue.json').resolve()}")
    print(
        "\nNote : le script ne contourne ni mot de passe, "
        "ni CAPTCHA, ni album privé."
    )


if __name__ == "__main__":
    main()
