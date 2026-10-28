"""Trimmed DOM fixtures of real pages + the driver output they must reproduce (offline regression tests).

When samsung.com changes, re-run `python -m tools.site_compare snapshot <product>`, then `pytest`:
the offline tests show which template's parsing broke.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import asdict
from pathlib import Path

from .config import context_axes
from .prices import extract_offers

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "site_compare" / "fixtures"

_SNAP_JS = r"""
(keep) => {
  // checked/selected are properties; outerHTML only keeps attributes
  for (const i of document.querySelectorAll('input')) i.checked ? i.setAttribute('checked', '') : i.removeAttribute('checked');
  for (const o of document.querySelectorAll('option')) o.selected ? o.setAttribute('selected', '') : o.removeAttribute('selected');
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') el.setAttribute('data-sc-hidden', '1');
  }
  let taken = [];
  for (const sel of keep) {
    for (const el of document.querySelectorAll(sel)) {
      if (taken.some(t => t === el || t.contains(el))) continue;
      taken = taken.filter(t => !el.contains(t));
      taken.push(el);
    }
  }
  taken.sort((a, b) => a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1);
  const drop = 'script, style, link, noscript, iframe, svg, img, picture, video, source';
  const parts = taken.map(el => {
    const c = el.cloneNode(true);
    for (const n of [c, ...c.querySelectorAll('[data-sc-hidden]')]) {
      if (n.getAttribute && n.getAttribute('data-sc-hidden')) { n.style.display = 'none'; n.removeAttribute('data-sc-hidden'); }
    }
    c.querySelectorAll(drop).forEach(x => x.remove());
    return c.outerHTML;
  });
  document.querySelectorAll('[data-sc-hidden]').forEach(e => e.removeAttribute('data-sc-hidden'));
  // JSON-LD verbatim, wherever it lives in the page
  const ld = [...document.querySelectorAll('script[type="application/ld+json"]')]
    .map(e => '<script type="application/ld+json">' + e.textContent.replace(/<\/script/gi, '<\\/script') + '</script>');
  return '<!doctype html><html><head><meta charset="utf-8"></head><body>\n' + parts.join('\n') + '\n' + ld.join('\n') + '\n</body></html>';
}
"""


def section_titles(driver, page) -> list[str]:
    if hasattr(driver, "section_titles"):
        return driver.section_titles(page)
    return [t for t, _ in driver.section_boxes(page)]


def expected_for(page, driver, product, ctx) -> dict:
    """What the driver extracts from the current page: the golden values of a fixture."""
    specs, _ = driver.specs(page)  # expanding scrolls the page; read everything else back at the top
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)
    opts = {a.name: [[o.value, o.label, o.sku, o.available] for o in driver.options(page, ctx, a.name)]
            for a in context_axes(product, ctx) if a.iterate or a.fixed}
    st = driver.read_state(page, ctx, product)
    prices = asdict(st.prices)
    prices.pop("headline")  # free text with live rating counts; not a parsing contract
    return json.loads(json.dumps({
        "options": opts,
        "state": {"selection": st.selection, "sku": st.sku, "prices": prices, "available": st.available},
        "sections": section_titles(driver, page),
        "spec_count": len(specs),
        "spec_sample": [[s.group, s.label, s.value] for s in specs[:5]],
        "offers": sorted(extract_offers(page.content())),
    }, ensure_ascii=False))


def save_snapshot(page, driver, product, ctx, out_dir: Path, name: str | None = None) -> Path:
    expected = expected_for(page, driver, product, ctx)
    html = page.evaluate(_SNAP_JS, list(getattr(driver, "SNAPSHOT_KEEP", ["body"])))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{name or product.id}__{ctx.id}"
    path = out_dir / f"{base}.html.gz"
    path.write_bytes(gzip.compress(html.encode("utf-8")))
    (out_dir / f"{base}.expected.json").write_text(json.dumps(expected, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def load_fixture(page, path: Path) -> dict:
    path = Path(path)
    page.set_content(gzip.decompress(path.read_bytes()).decode("utf-8"), wait_until="domcontentloaded")
    return json.loads(path.with_name(path.name.replace(".html.gz", ".expected.json")).read_text(encoding="utf-8"))


def diff_expected(a: dict, b: dict) -> list[str]:
    return [f"{k}: live={a.get(k)!r} fixture={b.get(k)!r}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


def snapshot_product(product, only: set[str] | None, wait_ms: int = 5000) -> list[Path]:
    """Open each context at its reference SKU, save the fixture, then check the driver reads the saved DOM alike."""
    from playwright.sync_api import sync_playwright

    from .capture import VIEWPORT, preset_cookies, scroll_through
    from .sites import get_driver

    saved: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        for ctx in product.contexts:
            if only and ctx.id not in only:
                continue
            jobs = [(get_driver(ctx.driver), get_driver(ctx.driver).sku_url(ctx, ctx.ref_sku) or ctx.url, product.id)]
            if ctx.spec_url:
                jobs.append((get_driver(ctx.spec_driver or "pd"), ctx.spec_url, f"{product.id}-specpage"))
            for driver, url, name in jobs:
                bctx = browser.new_context(viewport=VIEWPORT)
                preset_cookies(bctx, ctx)
                page = bctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                page.wait_for_timeout(wait_ms)
                driver.prepare(page, ctx)
                scroll_through(page, limit=80000)
                path = save_snapshot(page, driver, product, ctx, FIXTURES / type(driver).__module__.rsplit(".", 1)[-1], name)
                check = bctx.new_page()
                diffs = diff_expected(load_fixture(check, path), expected_for(check, driver, product, ctx))
                print(f"[{ctx.id}] {path.relative_to(FIXTURES)} {path.stat().st_size // 1024} KB "
                      + ("OK" if not diffs else "OFFLINE DIFF:\n  " + "\n  ".join(diffs)), flush=True)
                saved.append(path)
                bctx.close()
        browser.close()
    return saved
