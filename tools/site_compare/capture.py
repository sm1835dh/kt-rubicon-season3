"""Capture orchestrator: select each combo through a site driver, verify it, screenshot it, record values."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from .config import expand_combos, map_section, slug
from .model import Combo, ComboResult, Context, Product, RunData, Shot, TextBox
from .prices import extract_offers, money_tokens, parse_money, price_matches
from .sites import Box, OptionUnavailable, SiteDriver, get_driver

KST = timezone(timedelta(hours=9))
VIEWPORT = {"width": 1440, "height": 1000}
AXES = ("storage", "color", "carrier")
REGIONS = {"CA-ON": {"ontario"}, "CA-QC": {"quebec", "québec"}}

_TEXT_BOXES_JS = r"""
([x, y, w, h]) => {
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (!el.childNodes.length) continue;
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) continue;
    const t = (el.innerText || '').trim().replace(/\s+/g, ' ');
    if (!t || t.length > 120) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const ex = r.left + scrollX, ey = r.top + scrollY;
    if (ex + r.width < x || ex > x + w || ey + r.height < y || ey > y + h) continue;
    out.push([t, ex - x, ey - y, r.width, r.height]);
  }
  return out;
}
"""


def now_kst() -> datetime:
    return datetime.now(KST)


def _norm(v: str | None) -> str:
    return re.sub(r"\s+", "", (v or "").split("｜")[0]).lower()


def norm_region(v: str | None) -> str:
    if not v:
        return ""
    t = v.strip()
    if t.upper() in REGIONS:
        return t.upper()
    for code, names in REGIONS.items():
        if t.lower() in names:
            return code
    return t


def collect_text_boxes(page, box: Box) -> list[TextBox]:
    return [TextBox(*row) for row in page.evaluate(_TEXT_BOXES_JS, list(box))]


def scroll_through(page, step: int = 800, pause_ms: int = 250, limit: int = 20000) -> None:
    height = min(page.evaluate("document.body.scrollHeight"), limit)
    for y in range(0, height, step):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(pause_ms)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(pause_ms)


def _shot(page, run_dir: Path, name: str, title: str, section_id: str | None, order: int, box: Box) -> Shot:
    x, y, w, h = (max(0.0, box[0]), max(0.0, box[1]), box[2], box[3])
    rel = f"shots/{name}.png"
    page.screenshot(path=str(run_dir / rel), clip={"x": x, "y": y, "width": w, "height": h}, full_page=True)
    return Shot(title, section_id, order, rel, round(w), round(h), collect_text_boxes(page, (x, y, w, h)))


def _has_price(text: str | None, locale: str) -> bool:
    return bool(money_tokens(text or "", locale))


def _site_prefix(url: str) -> str:
    u = urlparse(url)
    first = u.path.strip("/").split("/")[0]
    return f"{u.scheme}://{u.netloc}/{first}/"


def capture_combo(page, driver: SiteDriver, product: Product, ctx: Context, combo: Combo, run_dir: Path,
                  wait_ms: int, with_extras: bool) -> ComboResult:
    warnings: list[str] = []
    status = "ok"
    got = base = offer = match = full = url_final = None
    sections: list[Shot] = []
    extras: list[Shot] = []
    try:
        # Try every axis; a step the site refuses is evidence, but the final state decides the status.
        refused: list[str] = []
        for axis in AXES:
            if axis in combo.want:
                try:
                    driver.select(page, axis, combo.want[axis], product)
                except OptionUnavailable as e:
                    refused.append(f"unavailable: {e}")
                page.wait_for_timeout(wait_ms)

        got = driver.read_state(page, ctx, product)
        if not _has_price(got.prices.base, ctx.locale):
            page.wait_for_timeout(wait_ms)
            got = driver.read_state(page, ctx, product)
            if not _has_price(got.prices.base, ctx.locale):
                warnings.append("price not rendered")

        off = [f"selection mismatch: {axis} want={combo.want[axis]} got={getattr(got, axis)}"
               for axis in AXES if axis in combo.want and _norm(combo.want[axis]) != _norm(getattr(got, axis))]
        if off:
            status = "unavailable" if refused else "mismatch"
            warnings += refused + off
        elif refused:
            warnings += [f"{w} (but the final state matches)" for w in refused]
        if ctx.region and norm_region(got.region) != ctx.region:
            warnings.append(f"region mismatch: want={ctx.region} got={got.region}")
            if status == "ok":
                status = "mismatch"  # prices shown belong to another province

        scroll_through(page)
        for order, (title, box) in enumerate(driver.section_boxes(page), 1):
            sid = map_section(title, product.sections)
            sections.append(_shot(page, run_dir, f"{combo.id}__{order:02d}-{slug(title)[:40]}", title, sid, order, box))
        if not sections:
            warnings.append("no sections found")
        if with_extras:
            try:
                for n, (title, box) in enumerate(driver.extra_shots(page), 1):
                    extras.append(_shot(page, run_dir, f"{combo.id}__extra-{n}", title, None, n, box))
            finally:
                driver.close_extras(page)

        base = parse_money(got.prices.base, ctx.locale, ctx.currency)
        offer = extract_offers(page.content()).get((got.sku or "").upper())
        match = price_matches(base, offer)
    except Exception as e:  # keep the run going; the report shows the error
        status = "error"
        warnings.append(f"error: {type(e).__name__}: {e}")
    try:
        url_final = page.url
        if not url_final.startswith(_site_prefix(ctx.url)):
            warnings.append(f"redirected: {url_final}")
        full = f"shots/{combo.id}__full.png"
        page.screenshot(path=str(run_dir / full), full_page=True)
    except Exception as e:
        full = None
        warnings.append(f"full screenshot failed: {e}")
    return ComboResult(combo.id, ctx.id, combo.kind, combo.want, got, url_final, status, base, offer, match,
                       sections, extras, full, warnings, now_kst().isoformat(timespec="seconds"))


def capture_context(browser, driver: SiteDriver, product: Product, ctx: Context, combos: list[Combo],
                    run_dir: Path, wait_ms: int) -> list[ComboResult]:
    page = browser.new_context(viewport=VIEWPORT).new_page()

    def open_page() -> list[str]:
        page.goto(ctx.url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(wait_ms)
        return [f"prepare: {w}" for w in driver.prepare(page, ctx)]

    def failed(c: Combo, e: Exception) -> ComboResult:
        msg = f"error: page load/prepare failed: {type(e).__name__}: {e}"
        return ComboResult(c.id, ctx.id, c.kind, c.want, None, None, "error", None, None, None, [], [], None,
                           [msg], now_kst().isoformat(timespec="seconds"))

    try:
        prep = open_page()
    except Exception as e:
        return [failed(c, e) for c in combos]
    # Drivers whose page state drifts between selections (US) start every combo from a fresh load.
    fresh = getattr(driver, "fresh_page_per_combo", False)
    results = []
    first_main = next((c.id for c in combos if c.kind == "main"), None)
    for i, combo in enumerate(combos):
        if fresh and i:
            try:
                prep = open_page()
            except Exception as e:
                results.append(failed(combo, e))
                continue
        r = capture_combo(page, driver, product, ctx, combo, run_dir, wait_ms, with_extras=combo.id == first_main)
        r.warnings[:0] = prep
        results.append(r)
        print(f"  {combo.id}: {r.status} base={r.got.prices.base if r.got else None} "
              f"warnings={len(r.warnings)}", flush=True)
    page.context.close()
    return results


def run_capture(product: Product, out_root: Path, only: set[str] | None, headed: bool, wait_ms: int) -> Path:
    started = now_kst()
    run_dir = Path(out_root) / product.id / started.strftime("%Y%m%d-%H%M%S")
    (run_dir / "shots").mkdir(parents=True, exist_ok=True)
    combos = expand_combos(product)
    run = RunData(product.id, product.title, run_dir.name, started.isoformat(timespec="seconds"),
                  [VIEWPORT["width"], VIEWPORT["height"]], wait_ms, product.contexts, [])
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=not headed)
        for ctx in product.contexts:
            if only and ctx.id not in only:
                continue
            print(f"[{ctx.id}] {ctx.url}", flush=True)
            mine = [c for c in combos if c.context_id == ctx.id]
            run.results += capture_context(browser, get_driver(ctx.driver), product, ctx, mine, run_dir, wait_ms)
            run.to_json(run_dir / "data.json")
        browser.close()
    run.to_json(run_dir / "data.json")
    return run_dir
