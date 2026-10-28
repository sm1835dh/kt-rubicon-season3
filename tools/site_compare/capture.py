"""Capture orchestrator: select each combo through a site driver, verify it, screenshot it, record values."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from .config import combo_id, combo_key, context_axes, expand_combos, map_section, slug
from .model import Combo, ComboResult, Context, Option, Product, RunData, Shot, SpecItem, State, TextBox
from .pngsize import png_size
from .prices import extract_offers, money_tokens, parse_money, price_matches
from .sites import Box, OptionUnavailable, SiteDriver, get_driver

KST = timezone(timedelta(hours=9))
VIEWPORT = {"width": 1440, "height": 1000}
AXES = ("storage", "color", "carrier")
REGIONS = {"CA-ON": {"ontario"}, "CA-QC": {"quebec", "québec"}}
# TrustArc consent stored up front: the consent click reloads UK/CA pages and breaks the capture.
CONSENT_COOKIES = {"notice_preferences": "0:", "notice_gdpr_prefs": "0::implied,eu",
                   "notice_behavior": "implied,eu", "cmapi_cookie_privacy": "permit 1 required"}
SLICE_PX = 4000  # one full-page capture breaks past ~16k px, and tall clips deep in a page render shifted
SPEC_SLICE_PX = 3000

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


def norm_value(v: str | None) -> str:
    """Option comparison key: lowercase without spaces, quotes or inch marks."""
    return re.sub(r"[\s\"'″”“’]+", "", (v or "").split("｜")[0]).lower()


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


def preset_cookies(browser_context, ctx: Context) -> None:
    values = dict(CONSENT_COOKIES)
    if ctx.region:
        values["country_region"] = ctx.region
    values.update(ctx.cookies or {})
    browser_context.add_cookies([{"name": k, "value": v, "domain": ".samsung.com", "path": "/"}
                                 for k, v in values.items()])


def collect_text_boxes(page, box: Box) -> list[TextBox]:
    return [TextBox(*row) for row in page.evaluate(_TEXT_BOXES_JS, list(box))]


def page_size(page) -> tuple[float, float]:
    return tuple(page.evaluate("[Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),"
                               " Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)]"))


def scroll_through(page, step: int = 800, pause_ms: int = 250, limit: int = 20000) -> None:
    height = min(page.evaluate("document.body.scrollHeight"), limit)
    for y in range(0, height, step):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(pause_ms)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(pause_ms)


def _shot(page, run_dir: Path, name: str, title: str, section_id: str | None, order: int, box: Box,
          warnings: list[str]) -> Shot | None:
    """Clip screenshot clamped to the page; Shot carries the real PNG size."""
    pw, ph = page_size(page)
    x, y = max(0.0, box[0]), max(0.0, box[1])
    w, h = min(box[2], pw - x), min(box[3], ph - y)
    if w < 1 or h < 1:
        warnings.append(f"shot {name}: box outside the page {tuple(round(v) for v in box)}")
        return None
    rel = f"shots/{name}.png"
    page.screenshot(path=str(run_dir / rel), clip={"x": x, "y": y, "width": w, "height": h}, full_page=True)
    rw, rh = png_size(run_dir / rel)
    return Shot(title, section_id, order, rel, rw, rh, collect_text_boxes(page, (x, y, w, h)))


def full_shots(page, run_dir: Path, name: str, slice_px: int = SLICE_PX) -> list[str]:
    scroll_through(page, limit=80000)
    pw, ph = page_size(page)
    out = []
    for n, y in enumerate(range(0, int(ph), slice_px), 1):
        rel = f"shots/{name}__full-{n:02d}.png"
        page.screenshot(path=str(run_dir / rel), clip={"x": 0, "y": y, "width": pw, "height": min(slice_px, ph - y)},
                        full_page=True)
        out.append(rel)
    return out


def _has_price(text: str | None, locale: str) -> bool:
    return bool(money_tokens(text or "", locale))


def _site_prefix(url: str) -> str:
    u = urlparse(url)
    first = u.path.strip("/").split("/")[0]
    return f"{u.scheme}://{u.netloc}/{first}/"


def _read_state_with_retry(page, driver, product, ctx, wait_ms, warnings, reload_ok: bool = False) -> State:
    """Wait once more for a missing price; in discover mode (state is in the URL) also reload once —
    prices sometimes never render when many pages are opened in a row."""
    missing = lambda st: not _has_price(st.prices.base, ctx.locale) and st.available is not False
    got = driver.read_state(page, ctx, product)
    if missing(got):
        page.wait_for_timeout(wait_ms)
        got = driver.read_state(page, ctx, product)
    if missing(got) and reload_ok:
        page.reload(wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(wait_ms)
        warnings += [f"prepare: {w}" for w in driver.prepare(page, ctx)]
        got = driver.read_state(page, ctx, product)
        warnings.append("reloaded: price was missing")
    if missing(got):
        warnings.append("price not rendered")
    return got


def _capture_page(page, driver, product, name: str, run_dir: Path, with_extras: bool, warnings: list[str]):
    """Sections, layers and specs of the current page state."""
    sections: list[Shot] = []
    extras: list[Shot] = []
    spec_shots: list[Shot] = []
    scroll_through(page, limit=80000)
    for order, (title, box) in enumerate(driver.section_boxes(page), 1):
        s = _shot(page, run_dir, f"{name}__{order:02d}-{slug(title)[:40]}", title, map_section(title, product.sections),
                  order, box, warnings)
        if s:
            sections.append(s)
    if not sections:
        warnings.append("no sections found")
    if with_extras:
        try:
            for n, (title, box) in enumerate(driver.extra_shots(page), 1):
                s = _shot(page, run_dir, f"{name}__extra-{n}", title, None, n, box, warnings)
                if s:
                    extras.append(s)
        finally:
            driver.close_extras(page)
    specs, boxes = _specs(page, driver, warnings)
    spec_shots = _spec_shots(page, run_dir, name, boxes, warnings)
    return sections, extras, specs, spec_shots


def split_box(box: Box, max_h: float = SPEC_SLICE_PX) -> list[Box]:
    x, y, w, h = box
    n = max(1, -(-int(h) // int(max_h)))
    step = h / n
    return [(x, y + i * step, w, step) for i in range(n)]


def _spec_shots(page, run_dir: Path, name: str, boxes, warnings: list[str]) -> list[Shot]:
    shots: list[Shot] = []
    for title, box in boxes:
        parts = split_box(box)
        for i, part in enumerate(parts, 1):
            label = f"{title} ({i}/{len(parts)})" if len(parts) > 1 else title
            s = _shot(page, run_dir, f"{name}__spec-{len(shots) + 1}", label, None, len(shots) + 1, part, warnings)
            if s:
                shots.append(s)
    return shots


def _specs(page, driver, warnings) -> tuple[list[SpecItem], list[tuple[str, Box]]]:
    try:
        return driver.specs(page)
    except Exception as e:
        warnings.append(f"specs failed: {type(e).__name__}: {e}")
        return [], []


def _finish_shots(page, ctx: Context, run_dir: Path, name: str, warnings: list[str]) -> tuple[str | None, list[str]]:
    url_final, shots = None, []
    try:
        url_final = page.url
        if not url_final.startswith(_site_prefix(ctx.url)):
            warnings.append(f"redirected: {url_final}")
        shots = full_shots(page, run_dir, name)
    except Exception as e:
        warnings.append(f"full screenshot failed: {e}")
    return url_final, shots


def capture_combo(page, driver: SiteDriver, product: Product, ctx: Context, combo: Combo, run_dir: Path,
                  wait_ms: int, with_extras: bool) -> ComboResult:
    """Click mode (Fold8): select want axes on the current page, then capture."""
    warnings: list[str] = []
    status = "ok"
    got = base = offer = match = None
    sections: list[Shot] = []
    extras: list[Shot] = []
    specs: list[SpecItem] = []
    spec_shots: list[Shot] = []
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

        got = _read_state_with_retry(page, driver, product, ctx, wait_ms, warnings)
        off = [f"selection mismatch: {axis} want={combo.want[axis]} got={got.selection.get(axis)}"
               for axis in AXES if axis in combo.want and _norm(combo.want[axis]) != _norm(got.selection.get(axis))]
        if off:
            status = "unavailable" if refused else "mismatch"
            warnings += refused + off
        elif refused:
            warnings += [f"{w} (but the final state matches)" for w in refused]
        if ctx.region and norm_region(got.region) != ctx.region:
            warnings.append(f"region mismatch: want={ctx.region} got={got.region}")
            if status == "ok":
                status = "mismatch"  # prices shown belong to another province

        sections, extras, specs, spec_shots = _capture_page(page, driver, product, combo.id, run_dir, with_extras,
                                                            warnings)
        base = parse_money(got.prices.base, ctx.locale, ctx.currency)
        offer = extract_offers(page.content()).get((got.sku or "").upper())
        match = price_matches(base, offer)
    except Exception as e:  # keep the run going; the report shows the error
        status = "error"
        warnings.append(f"error: {type(e).__name__}: {e}")
    url_final, shots = _finish_shots(page, ctx, run_dir, combo.id, warnings)
    return ComboResult(combo.id, ctx.id, combo.kind, combo.want, got, url_final, status, base, offer, match,
                       sections, extras, shots, warnings, now_kst().isoformat(timespec="seconds"),
                       specs=specs, spec_shots=spec_shots, key=combo.key)


def _open(browser_context, driver, ctx: Context, url: str, wait_ms: int):
    page = browser_context.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(wait_ms)
    return page, [f"prepare: {w}" for w in driver.prepare(page, ctx)]


def _matches(option: Option, value: str) -> bool:
    return norm_value(value) in (option.value, norm_value(option.label))


def _walk_path(page, driver, product: Product, ctx: Context, path: list[Option], wait_ms: int) -> list[str]:
    """Click the path's options in order; returns the options the site refused."""
    refused: list[str] = []
    current = driver.read_state(page, ctx, product).selection
    for o in path:
        if _matches(o, current.get(o.axis, "")):
            continue  # the page already shows this option (e.g. the reference SKU)
        try:
            driver.choose(page, ctx, o)
        except OptionUnavailable as e:
            refused.append(f"unavailable: {e}")
        page.wait_for_timeout(wait_ms)
        current = driver.read_state(page, ctx, product).selection
    return refused


def _off_target(combo: Combo, got: State) -> list[str]:
    off = []
    if combo.target_sku and got.sku and norm_value(got.sku) != norm_value(combo.target_sku):
        off.append(f"sku mismatch: want={combo.target_sku} got={got.sku}")
    off += [f"selection mismatch: {o.axis} want={o.label} got={got.selection.get(o.axis)}"
            for o in combo.path if o.axis in got.selection and not _matches(o, got.selection[o.axis])]
    return off


def discover_leaves(browser_context, driver, product: Product, ctx: Context, wait_ms: int) -> tuple[list[Combo], list[str]]:
    """Walk the option tree of the context's axes; one Combo per leaf."""
    axes = [a for a in context_axes(product, ctx) if a.iterate or a.fixed]
    warnings: list[str] = []
    if not axes:
        return [Combo(f"{ctx.id}__ref", ctx.id, "main", {}, [], ctx.ref_sku, combo_key([]), True)], warnings
    start = driver.sku_url(ctx, ctx.ref_sku) or ctx.url
    leaves: list[Combo] = []
    ref_selection: dict[str, str] = {}

    def walk(prefix: list[Option]):
        page, _ = _open(browser_context, driver, ctx, start, wait_ms)
        try:
            for o in prefix:
                driver.choose(page, ctx, o)
                page.wait_for_timeout(wait_ms)
            if not prefix:
                ref_selection.update(driver.read_state(page, ctx, product).selection)
            spec = axes[len(prefix)]
            opts = driver.options(page, ctx, spec.name)
            if not opts:  # options hydrate late on some loads: one reload before concluding there are none
                page.reload(wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(wait_ms)
                driver.prepare(page, ctx)
                for o in prefix:
                    driver.choose(page, ctx, o)
                    page.wait_for_timeout(wait_ms)
                opts = driver.options(page, ctx, spec.name)
        finally:
            page.close()
        if spec.fixed:
            opts = [o for o in opts if _matches(o, spec.fixed)][:1]
            if not opts:
                warnings.append(f"discover: no {spec.name} option {spec.fixed!r} under {[o.label for o in prefix]}")
        if not opts and not spec.fixed:
            warnings.append(f"discover: no {spec.name} options under {[o.label for o in prefix]}")
        for o in opts:
            if len(prefix) + 1 == len(axes):
                path = prefix + [o]
                leaves.append(Combo(combo_id(ctx.id, path), ctx.id, "main", {p.axis: p.label for p in path}, path,
                                    o.sku, combo_key(path)))
            else:
                walk(prefix + [o])

    walk([])
    ref = [l for l in leaves if l.target_sku and ctx.ref_sku and norm_value(l.target_sku) == norm_value(ctx.ref_sku)]
    if not ref:  # SKUs unknown: the leaf whose values equal the reference page's selection
        ref = [l for l in leaves if all(_matches(o, ref_selection.get(o.axis, "")) for o in l.path)]
    for l in ref[:1]:
        l.is_ref = True
    return leaves, warnings


def capture_leaf(browser_context, driver, product: Product, ctx: Context, combo: Combo, run_dir: Path, wait_ms: int,
                 with_extras: bool) -> ComboResult:
    """Discover mode: open the leaf's state on a fresh page (direct URL or click path), verify, capture."""
    warnings: list[str] = []
    status = "ok"
    got = base = offer = match = None
    sections: list[Shot] = []
    extras: list[Shot] = []
    specs: list[SpecItem] = []
    spec_shots: list[Shot] = []
    url = driver.sku_url(ctx, combo.target_sku) if combo.target_sku else None
    page = None
    url_final, shots = None, []
    try:
        page, prep = _open(browser_context, driver, ctx, url or ctx.url, wait_ms)
        warnings += prep
        clicking = not url and bool(combo.path)
        refused = _walk_path(page, driver, product, ctx, combo.path, wait_ms) if clicking else []
        got = _read_state_with_retry(page, driver, product, ctx, wait_ms, warnings, reload_ok=True)
        off = _off_target(combo, got)
        if off and clicking and not refused and got.available is not False:
            # a click can be swallowed (overlay, late hydration): walk the path once more on a fresh page
            warnings.append(f"retried: {'; '.join(off)}")
            page.close()
            page = None
            page, _ = _open(browser_context, driver, ctx, ctx.url, wait_ms)
            refused = _walk_path(page, driver, product, ctx, combo.path, wait_ms)
            got = _read_state_with_retry(page, driver, product, ctx, wait_ms, warnings, reload_ok=True)
            off = _off_target(combo, got)
        if got.available is False:
            status = "unavailable"
            warnings.append("not available: the page says this product cannot be bought")
            warnings += off
        elif off:
            status = "unavailable" if refused else "mismatch"
            warnings += refused + off
        elif refused:
            warnings += [f"{w} (but the final state matches)" for w in refused]
        if ctx.region and norm_region(got.region) != ctx.region:
            warnings.append(f"region mismatch: want={ctx.region} got={got.region}")
            if status == "ok":
                status = "mismatch"
        sections, extras, specs, spec_shots = _capture_page(page, driver, product, combo.id, run_dir, with_extras,
                                                            warnings)
        base = parse_money(got.prices.base, ctx.locale, ctx.currency)
        offer = extract_offers(page.content()).get((got.sku or "").upper())
        match = price_matches(base, offer)
        if status == "ok" and base is None and not sections and not specs:
            status = "error"
            warnings.append("nothing captured")
    except Exception as e:
        status = "error"
        warnings.append(f"error: {type(e).__name__}: {e}")
    if page is not None:
        url_final, shots = _finish_shots(page, ctx, run_dir, combo.id, warnings)
        page.close()
    return ComboResult(combo.id, ctx.id, combo.kind, combo.want, got, url_final, status, base, offer, match,
                       sections, extras, shots, warnings, now_kst().isoformat(timespec="seconds"),
                       specs=specs, spec_shots=spec_shots, key=combo.key, is_ref=combo.is_ref)


def capture_specs_page(browser_context, ctx: Context, result: ComboResult, run_dir: Path, wait_ms: int) -> None:
    """Specs that live on another page (buy page → PDP): fill the reference result."""
    driver = get_driver(ctx.spec_driver or "pd")
    try:
        page, prep = _open(browser_context, driver, ctx, ctx.spec_url, wait_ms)
    except Exception as e:
        result.warnings.append(f"spec page failed: {type(e).__name__}: {e}")
        return
    try:
        scroll_through(page, limit=80000)
        specs, boxes = _specs(page, driver, result.warnings)
        result.specs = specs
        result.spec_shots = _spec_shots(page, run_dir, result.combo_id, boxes, result.warnings)
        if not specs:
            result.warnings.append(f"no specs on {ctx.spec_url}")
    finally:
        page.close()


def capture_context(browser, driver: SiteDriver, product: Product, ctx: Context, combos: list[Combo],
                    run_dir: Path, wait_ms: int) -> list[ComboResult]:
    bctx = browser.new_context(viewport=VIEWPORT)
    preset_cookies(bctx, ctx)
    page = bctx.new_page()

    def open_page() -> list[str]:
        page.goto(ctx.url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(wait_ms)
        return [f"prepare: {w}" for w in driver.prepare(page, ctx)]

    def failed(c: Combo, e: Exception) -> ComboResult:
        msg = f"error: page load/prepare failed: {type(e).__name__}: {e}"
        return ComboResult(c.id, ctx.id, c.kind, c.want, None, None, "error", None, None, None, [], [], [],
                           [msg], now_kst().isoformat(timespec="seconds"), key=c.key)

    try:
        prep = open_page()
    except Exception as e:
        bctx.close()
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
        _log(r)
    bctx.close()
    return results


def _log(r: ComboResult) -> None:
    print(f"  {r.combo_id}: {r.status} sku={r.got.sku if r.got else None} base={r.got.prices.base if r.got else None} "
          f"specs={len(r.specs)} warnings={len(r.warnings)}", flush=True)


def capture_discover_context(browser, driver, product: Product, ctx: Context, run_dir: Path,
                             wait_ms: int) -> tuple[list[ComboResult], int]:
    bctx = browser.new_context(viewport=VIEWPORT)
    preset_cookies(bctx, ctx)
    results: list[ComboResult] = []
    try:
        leaves, dwarn = discover_leaves(bctx, driver, product, ctx, wait_ms)
    except Exception as e:
        leaves, dwarn = [], [f"discover failed: {type(e).__name__}: {e}"]
    print(f"  discovered {len(leaves)} combos", flush=True)
    if not leaves:  # nothing to capture: keep one error row so the report shows the context
        results.append(ComboResult(f"{ctx.id}__ref", ctx.id, "main", {}, None, None, "error", None, None, None, [], [],
                                   [], dwarn or ["discover: no combos"], now_kst().isoformat(timespec="seconds"),
                                   key=combo_key([]), is_ref=True))
    for i, leaf in enumerate(leaves):
        r = capture_leaf(bctx, driver, product, ctx, leaf, run_dir, wait_ms, with_extras=leaf.is_ref)
        if i == 0:
            r.warnings[:0] = dwarn
        if leaf.is_ref and ctx.spec_url:
            capture_specs_page(bctx, ctx, r, run_dir, wait_ms)
        results.append(r)
        _log(r)
    bctx.close()
    return results, len(leaves)


def run_capture(product: Product, out_root: Path, only: set[str] | None, headed: bool, wait_ms: int,
                into: Path | None = None) -> Path:
    """Capture into a new run dir, or with `into` recapture `only`'s contexts in an existing run (others kept)."""
    started = now_kst()
    run_dir = Path(into) if into else Path(out_root) / product.id / started.strftime("%Y%m%d-%H%M%S")
    (run_dir / "shots").mkdir(parents=True, exist_ok=True)
    combos = expand_combos(product) if product.mode == "click" else []
    if into:
        run = RunData.from_json(run_dir / "data.json")
        run.contexts = product.contexts
    else:
        run = RunData(product.id, product.title, run_dir.name, started.isoformat(timespec="seconds"),
                      [VIEWPORT["width"], VIEWPORT["height"]], wait_ms, product.contexts, [])
    order = {c.id: i for i, c in enumerate(product.contexts)}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=not headed)
        for ctx in product.contexts:
            if only and ctx.id not in only:
                continue
            print(f"[{ctx.id}] {ctx.url}", flush=True)
            driver = get_driver(ctx.driver)
            if product.mode == "click":
                mine = [c for c in combos if c.context_id == ctx.id]
                results = capture_context(browser, driver, product, ctx, mine, run_dir, wait_ms)
            else:
                results, n = capture_discover_context(browser, driver, product, ctx, run_dir, wait_ms)
                run.discovered[ctx.id] = n
            run.results = [r for r in run.results if r.context_id != ctx.id] + results
            run.results.sort(key=lambda r: order.get(r.context_id, len(order)))  # stable: combo order kept
            run.to_json(run_dir / "data.json")
        browser.close()
    run.to_json(run_dir / "data.json")
    return run_dir
