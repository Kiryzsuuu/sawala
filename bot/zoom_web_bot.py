"""Headless-browser bot that joins a Zoom meeting via the Zoom Web Client
and feeds SAWALA real per-participant video frames + real names, instead of
guessing from a screenshot of someone's shared screen (Skenario B).

Why this exists: Zoom's official raw-media path (RTMS) is gated behind
paid Zoom plans and Marketplace app review, which isn't available for every
deployment. This bot sidesteps that entirely by controlling its own Chromium
browser: it joins the meeting like a regular guest, forces gallery view,
then reads participant names straight from the page DOM (exact, not OCR)
and screenshots each participant's video tile by its actual on-page
bounding box (exact, not a guessed grid split). Each tile is POSTed to the
existing /api/ingest/frame endpoint, which already supports named-frame
ingestion (see src/api/routes.py) - no backend changes needed.

Caveat: Zoom's web client DOM structure changes across releases without
notice. The selectors below are current best-effort guesses; if Zoom ships
a redesign, `_find_tiles()` is the one place to update.

Usage:
    pip install -r bot/requirements-bot.txt
    playwright install chromium

    python bot/zoom_web_bot.py \
        --join-url "https://us02web.zoom.us/wc/join/1234567890" \
        --display-name "SAWALA Monitor" \
        --api-base "https://sawala.inspiratekno.com" \
        --ingest-token "<bot_ingest.token dari config.yaml>"

A monitoring session must already be active (start it from the dashboard,
or POST /api/session/start) before frames will be accepted.
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time

import requests
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("zoom_web_bot")

# Kandidat selector untuk elemen per-tile peserta. Dicoba berurutan karena
# Zoom sering ganti nama class antar rilis web client. Class exact (bukan
# `[class*=...]` yang lebar) sengaja dipakai untuk container tile-nya -
# versi wildcard sebelumnya ikut match child element seperti
# `video-avatar__avatar-title` / `-footer` / `-name` (semuanya mengandung
# substring "video-avatar__avatar"), jadi 1 peserta asli kehitung beberapa
# tile palsu. Dikonfirmasi lewat inspeksi DOM live: ".speaker-bar-container__
# video-frame" adalah strip thumbnail peserta yang muncul saat ada yang
# screen-share (kasus paling umum di kelas/rapat kerja); ".gallery-video-
# container__video-tile" untuk gallery view biasa (belum diverifikasi live,
# nama class dari dokumentasi Zoom).
TILE_SELECTOR_CANDIDATES = [
    ".speaker-bar-container__video-frame",
    ".gallery-video-container__video-tile",
]
# Masing-masing dicoba sebagai teks (.text_content()) DULU, lalu sebagai
# atribut `alt` kalau elemennya <img> (avatar placeholder pakai foto
# profil, teksnya kosong tapi alt="Nama Peserta").
NAME_SELECTOR_CANDIDATES = [
    ".video-avatar__avatar-footer span",
    "img.video-avatar__avatar-img",
    ".video-avatar__avatar-name",
]


def _dismiss_if_present(page: Page, selector: str, timeout_ms: int = 3000) -> None:
    try:
        page.locator(selector).first.click(timeout=timeout_ms)
        logger.info("Dismissed dialog: %s", selector)
    except PlaywrightTimeoutError:
        pass


_MEETING_ID_URL_RE = re.compile(r"^(https?://[^/]+)/j/(\d+)(\?.*)?$")


def _normalize_join_url(join_url: str) -> str:
    """A plain meeting invite link (`.../j/<id>?pwd=...`) opens Zoom's
    "Launching..." app-redirect page, not the web client join form - the
    web client form only loads directly at `.../wc/join/<id>?pwd=...`.
    Rewrite proactively so the bot doesn't depend on clicking through the
    launch page (see _click_join_from_browser for the fallback when a URL
    doesn't match this shape, e.g. personal meeting room links)."""
    match = _MEETING_ID_URL_RE.match(join_url)
    if not match:
        return join_url
    host, meeting_id, query = match.groups()
    normalized = f"{host}/wc/join/{meeting_id}{query or ''}"
    logger.info("URL diubah ke join langsung web client: %s", normalized)
    return normalized


def _click_join_from_browser(page: Page) -> bool:
    """Fallback for join URLs _normalize_join_url() couldn't rewrite: the
    "Launching..." page has a small "Join from Your Browser" link, usually
    revealed after clicking a "click here" prompt first."""
    _dismiss_if_present(page, "a:has-text('click here')", timeout_ms=5000)
    for selector in [
        "a:has-text('Join from Your Browser')",
        "a#joinBtn",
        "a.joinBtn",
    ]:
        try:
            page.locator(selector).first.click(timeout=5000)
            logger.info("Klik '%s' untuk masuk ke web client", selector)
            return True
        except PlaywrightTimeoutError:
            continue
    return False


_WAITING_ROOM_TEXT = "Host has joined. We've let them know you're here."


def _wait_for_waiting_room(page: Page, timeout_seconds: float = 300.0) -> None:
    """If the meeting has Waiting Room enabled, Zoom shows this exact
    message instead of dropping the bot into the gallery. Poll until the
    host admits it (or bail with a clear error after `timeout_seconds`),
    instead of barreling ahead and confusingly reporting 'no participant
    tiles found' when the bot was never actually let into the meeting."""
    if page.locator(f"text={_WAITING_ROOM_TEXT}").count() == 0:
        return

    logger.info(
        "Meeting ini pakai Waiting Room - bot 'SAWALA' menunggu di-admit oleh host. "
        "Buka Zoom, panel Participants, admit 'SAWALA' dari waiting room."
    )
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if page.locator(f"text={_WAITING_ROOM_TEXT}").count() == 0:
            logger.info("Sudah di-admit, lanjut masuk meeting")
            return
        time.sleep(3)

    raise RuntimeError(
        f"Tidak di-admit dari waiting room dalam {timeout_seconds:.0f} detik. "
        "Admit 'SAWALA' dari panel Participants, atau matikan Waiting Room di pengaturan meeting."
    )


def join_meeting(page: Page, join_url: str, display_name: str, passcode: str | None) -> None:
    join_url = _normalize_join_url(join_url)
    logger.info("Membuka %s", join_url)
    page.goto(join_url, wait_until="domcontentloaded")

    _dismiss_if_present(page, "button:has-text('I Agree')")
    _dismiss_if_present(page, "button:has-text('Accept Cookies')")

    name_input = page.locator("input#input-for-name, input[placeholder*='Your Name' i]").first
    try:
        name_input.wait_for(timeout=8000)
    except PlaywrightTimeoutError:
        logger.info("Form nama belum kelihatan, coba cari link 'Join from Your Browser'...")
        if not _click_join_from_browser(page):
            raise RuntimeError(
                "Tidak menemukan form join web client maupun link 'Join from Your Browser'. "
                "Cek manual: buka join_url ini di browser biasa, lihat halaman apa yang muncul."
            )
        name_input.wait_for(timeout=20000)
    name_input.fill(display_name)

    if passcode:
        pass_input = page.locator("input#input-for-pwd, input[placeholder*='passcode' i]").first
        if pass_input.count() > 0:
            pass_input.fill(passcode)

    join_button = page.locator("button:has-text('Join')").first
    join_button.click(timeout=10000)
    logger.info("Klik join, menunggu masuk ke meeting...")

    _wait_for_waiting_room(page)

    # PENTING: bot ini cuma butuh baca video peserta lain, tidak pernah
    # boleh join audio. Chromium diberi --use-fake-device-for-media-stream
    # (supaya tidak butuh mic asli) yang nada beep-nya akan ikut terkirim ke
    # semua peserta lain kalau sampai audio ke-join - jangan pernah klik
    # "Join Audio by Computer", tutup dialognya saja.
    time.sleep(5)
    _dismiss_if_present(page, "button:has-text(\"Don't Join Audio\")", timeout_ms=5000)
    _dismiss_if_present(page, "button:has-text('Continue without microphone')", timeout_ms=5000)
    _dismiss_if_present(page, "[aria-label='Close']")

    # Jaga-jaga kalau audio ternyata tetap ke-join (mis. dialognya keburu
    # auto-dismiss dengan opsi computer audio default aktif) - mute paksa.
    for selector in ["[aria-label*='mute my microphone' i]", "button[aria-label^='Mute' i]"]:
        try:
            page.locator(selector).first.click(timeout=3000)
            logger.info("Mic dipastikan mute via %s", selector)
            break
        except PlaywrightTimeoutError:
            continue

    _switch_to_gallery_view(page)


def _switch_to_gallery_view(page: Page) -> None:
    """Best-effort: Zoom biasanya default ke gallery view untuk web client,
    tapi kalau tidak, coba klik tombol switch-view."""
    for selector in [
        "button[aria-label*='Gallery' i]",
        "[class*='view-switch'] button",
    ]:
        try:
            page.locator(selector).first.click(timeout=3000)
            logger.info("Beralih ke gallery view via %s", selector)
            return
        except PlaywrightTimeoutError:
            continue
    logger.info("Tombol switch-view tidak ditemukan, asumsi sudah gallery view")


def _find_tiles(page: Page):
    for selector in TILE_SELECTOR_CANDIDATES:
        tiles = page.locator(selector)
        count = tiles.count()
        if count > 0:
            return tiles
    return None


def _extract_name(page: Page, tile) -> str | None:
    for selector in NAME_SELECTOR_CANDIDATES:
        el = tile.locator(selector).first
        if el.count() == 0:
            continue
        text = (el.text_content() or "").strip()
        if text:
            return text
        # Avatar dengan foto profil: <img class="video-avatar__avatar-img"
        # alt="Nama Peserta"> tidak punya text content, namanya di `alt`.
        alt = el.get_attribute("alt")
        if alt:
            return alt.strip()
    return None


_INVALID_FILENAME_CHARS = re.compile(r"[^\w .'-]")


def capture_and_send(page: Page, api_base: str, ingest_token: str) -> int:
    """One monitoring tick: screenshot every visible participant tile and
    POST it to /api/ingest/frame. Returns how many tiles were sent."""
    tiles = _find_tiles(page)
    if tiles is None:
        logger.warning("Tidak ada tile peserta ditemukan - selector mungkin sudah usang, lihat _find_tiles()")
        return 0

    sent = 0
    for i in range(tiles.count()):
        tile = tiles.nth(i)
        try:
            box = tile.bounding_box()
            if box is None or box["width"] < 20 or box["height"] < 20:
                continue

            name = _extract_name(page, tile) or f"Peserta {i + 1}"
            png_bytes = tile.screenshot(type="png")

            resp = requests.post(
                f"{api_base}/api/ingest/frame",
                params={"participant_name": name},
                files={"file": (f"{_INVALID_FILENAME_CHARS.sub('_', name)}.png", png_bytes, "image/png")},
                headers={"X-Ingest-Token": ingest_token},
                timeout=10,
            )
            if resp.ok:
                sent += 1
            else:
                logger.warning("Ingest ditolak untuk %r: %s %s", name, resp.status_code, resp.text[:200])
        except Exception:
            logger.exception("Gagal capture/kirim tile #%d", i)

    return sent


def run(args: argparse.Namespace) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
        )
        # Cuma "camera" - Zoom web client butuh izin ini untuk memuat UI
        # gallery dengan benar walau bot tidak pernah mengirim video sendiri.
        # "microphone" sengaja TIDAK diberi supaya tidak ada jalan bot
        # ke-auto-join audio dan mengirim nada beep dari fake audio device
        # Chromium ke semua peserta lain.
        context = browser.new_context(permissions=["camera"], viewport={"width": 1600, "height": 900})
        page = context.new_page()

        join_meeting(page, args.join_url, args.display_name, args.passcode)

        logger.info("Mulai monitoring loop, interval %.1fs (Ctrl+C untuk berhenti)", args.interval)
        try:
            while True:
                sent = capture_and_send(page, args.api_base, args.ingest_token)
                logger.info("Tick selesai: %d frame terkirim", sent)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Dihentikan oleh user")
        finally:
            context.close()
            browser.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--join-url", required=True, help="Link 'Join from Browser' Zoom Web Client")
    parser.add_argument("--display-name", default="SAWALA")
    parser.add_argument("--passcode", default=None)
    parser.add_argument("--api-base", required=True, help="Base URL backend SAWALA, mis. https://sawala.inspiratekno.com")
    parser.add_argument("--ingest-token", required=True, help="Sama dengan bot_ingest.token di config.yaml (jangan 'change-me')")
    parser.add_argument("--interval", type=float, default=3.0, help="Detik antar capture tick")
    return parser.parse_args(argv)


if __name__ == "__main__":
    run(parse_args(sys.argv[1:]))
