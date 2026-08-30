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

# Kandidat selector untuk elemen per-tile peserta di gallery view. Dicoba
# berurutan karena Zoom sering ganti nama class antar rilis web client.
TILE_SELECTOR_CANDIDATES = [
    "[class*='video-avatar__avatar']",
    "[class*='gallery-video-container__video-tile']",
    "[class*='participants-item']",
]
NAME_SELECTOR_CANDIDATES = [
    "[class*='video-avatar__avatar-title']",
    "[class*='display-name']",
    "[class*='participants-item__display-name']",
]


def _dismiss_if_present(page: Page, selector: str, timeout_ms: int = 3000) -> None:
    try:
        page.locator(selector).first.click(timeout=timeout_ms)
        logger.info("Dismissed dialog: %s", selector)
    except PlaywrightTimeoutError:
        pass


def join_meeting(page: Page, join_url: str, display_name: str, passcode: str | None) -> None:
    logger.info("Membuka %s", join_url)
    page.goto(join_url, wait_until="domcontentloaded")

    _dismiss_if_present(page, "button:has-text('I Agree')")
    _dismiss_if_present(page, "button:has-text('Accept Cookies')")

    name_input = page.locator("input#input-for-name, input[placeholder*='Your Name' i]").first
    name_input.wait_for(timeout=20000)
    name_input.fill(display_name)

    if passcode:
        pass_input = page.locator("input#input-for-pwd, input[placeholder*='passcode' i]").first
        if pass_input.count() > 0:
            pass_input.fill(passcode)

    join_button = page.locator("button:has-text('Join')").first
    join_button.click(timeout=10000)
    logger.info("Klik join, menunggu masuk ke meeting...")

    # Dialog "Join Audio" / minta izin device muncul setelah masuk - kita
    # skip audio sepenuhnya, bot ini cuma butuh video peserta lain.
    time.sleep(5)
    _dismiss_if_present(page, "button:has-text('Join Audio by Computer')", timeout_ms=8000)
    _dismiss_if_present(page, "[aria-label='Close']")

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
        if el.count() > 0:
            text = (el.text_content() or "").strip()
            if text:
                return text
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
        context = browser.new_context(permissions=["camera", "microphone"], viewport={"width": 1600, "height": 900})
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
