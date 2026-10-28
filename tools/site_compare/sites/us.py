"""Driver for samsung.com/us buy pages (Next.js; every selection moves to a -sku-<model>/ URL)."""
from __future__ import annotations

import re
from typing import Iterator

from ..model import Context, PriceTexts, Product, State
from ..prices import money_tokens
from .base import BaseDriver, Box, OptionNotFound, OptionUnavailable

CARRIER_SUFFIX = {"unlocked": "XAA", "verizon": "VZW", "at&t": "ATT"}
STORAGE_CODE = {"256gb": "A", "512gb": "E", "1tb": "F"}

_SECTIONS_JS = r"""
() => {
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0; };
  // Reviews start the non-buy part of the page; the header rating widget near the top is not it.
  const stopAt = (() => { const r = [...document.querySelectorAll('[class*=ReviewSummary_], [class*=AISummaryBlock], #reviews, footer')]
    .filter(vis).map(e => e.getBoundingClientRect().top + scrollY).filter(y => y > 1000);
    const sum = [...document.querySelectorAll('div')].filter(e => /SM-[A-Z0-9]+ \/ SM-/.test(e.innerText)
      && /Total/.test(e.innerText) && e.getBoundingClientRect().width > 500)
      .sort((a, b) => a.innerText.length - b.innerText.length)[0];
    if (sum) r.push(sum.getBoundingClientRect().top + scrollY);  // buy flow ends at the order summary
    return r.length ? Math.min(...r) : Infinity; })();
  const title = (document.querySelector('h1') || {}).innerText || '';
  const heads = [];
  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el) || el.closest('header, nav, footer, [role=dialog], [class*=gnb]')) continue;
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    const t = (el.innerText || '').trim().replace(/\s+/g, ' ');
    if (!t || t.length > 60 || /[$\d]/.test(t) || t === title.trim()) continue;
    const s = getComputedStyle(el);
    if (parseFloat(s.fontSize) < 20 || (+s.fontWeight < 600 && !/bold/i.test(s.fontFamily))) continue;
    const r = el.getBoundingClientRect(), y = r.top + scrollY;
    if (y < 300 || y >= stopAt) continue;
    let box = el.parentElement;
    while (box && box.getBoundingClientRect().height < r.height * 3) box = box.parentElement;
    const br = (box || el).getBoundingClientRect();
    heads.push({t, y, x: br.left + scrollX, w: br.width});
  }
  heads.sort((a, b) => a.y - b.y);
  const uniq = heads.filter((h, i) => !i || h.t !== heads[i - 1].t || Math.abs(h.y - heads[i - 1].y) > 5);
  return uniq.map((h, i) => {
    const top = h.y - 12;
    const next = i + 1 < uniq.length ? uniq[i + 1].y - 12 : Math.min(top + 900, stopAt);
    return [h.t, [h.x, top, h.w, Math.max(40, next - top)]];
  });
}
"""

_STATE_JS = r"""
() => {
  const lines = document.body.innerText.split('\n').map(s => s.trim()).filter(Boolean);
  const skuLine = lines.find(l => /^SM-[A-Z0-9]+\s*\/\s*SM-[A-Z0-9]+$/.test(l)) || '';
  const sel = lines[lines.indexOf(skuLine) - 1] || '';
  const ti = lines.findIndex(l => l === 'Total');
  const bar = document.querySelector('h1') && document.querySelector('h1').closest('div[class]');
  let top = document.querySelector('h1');
  while (top && top.getBoundingClientRect().width < 1300) top = top.parentElement;
  return {skuLine, sel, total: ti >= 0 ? lines.slice(ti + 1, ti + 3).join(' ') : '',
          headline: top ? top.innerText.replace(/\s+/g, ' ').trim() : ''};
}
"""


def _sku_from_url(url: str) -> str | None:
    m = re.search(r"-sku-(sm-[a-z0-9]+)/?$", url.lower())
    return m.group(1).upper() if m else None


def _rect(page, js_expr: str) -> Box | None:
    b = page.evaluate(f"""() => {{ const e = {js_expr}; if (!e) return null; const r = e.getBoundingClientRect();
        return r.width && r.height ? [r.left + scrollX, r.top + scrollY, r.width, r.height] : null; }}""")
    return tuple(b) if b else None


class UsDriver(BaseDriver):
    # Carrier tiles change after re-clicks and overlays, so every combo starts from a fresh load.
    fresh_page_per_combo = True

    def prepare(self, page, ctx: Context) -> list[str]:
        btn = page.locator(".truste-banner-close")
        if btn.count() and btn.first.is_visible():
            btn.first.click(timeout=3000)
            page.wait_for_timeout(800)
        return []

    def _expected_sku(self, page, axis: str, value: str, product: Product) -> str | None:
        sku = _sku_from_url(page.url)
        if not sku or len(sku) < 14:
            return None
        if axis == "storage" and value.lower() in STORAGE_CODE:
            return sku[:10] + STORAGE_CODE[value.lower()] + sku[11:]
        if axis == "color" and value in product.colors:
            return sku[:8] + product.colors[value] + sku[10:]
        if axis == "carrier" and value.lower() in CARRIER_SUFFIX:
            return sku[:11] + CARRIER_SUFFIX[value.lower()]
        return None

    def select(self, page, axis: str, value: str, product: Product) -> None:
        groups = {"storage": ("[data-testid=handleRelationSelect]", f"[data-modeldisplay='{value.lower()}']"),
                  "color": ("[aria-label^='Color Variant:']", f"[aria-label='Color Variant: {value}']"),
                  "carrier": ("[aria-label^='Carrier:']", f"[aria-label='Carrier: {value}']")}
        if axis not in groups:
            return
        group, one = groups[axis]
        loc = page.locator(one if axis != "storage" else group + one).first
        if not loc.count():
            shown = page.eval_on_selector_all(group, "els => els.map(e => e.getAttribute('aria-label') || e.dataset.modeldisplay)")
            if shown:  # the site lists this axis but not this value: it does not offer it
                raise OptionUnavailable(f"{axis} {value} not offered; shown: {shown}")
            raise OptionNotFound(f"{axis} {value}: no {axis} tiles at all ({group})")
        expected = self._expected_sku(page, axis, value, product)
        loc.click(timeout=10000)
        page.wait_for_timeout(1500)
        if expected and _sku_from_url(page.url) != expected:
            page.wait_for_timeout(3000)  # client-side routing can lag; the final state decides, not this step
        msg = page.get_by_text(re.compile(r"is unavailable for", re.I))
        if msg.count() and msg.first.is_visible():
            raise OptionUnavailable(msg.first.inner_text().strip())

    def read_state(self, page, ctx: Context, product: Product) -> State:
        # The order summary only renders once scrolled into view.
        for y in range(0, 6000, 1000):
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(200)
        page.evaluate("window.scrollTo(0, 0)")
        d = page.evaluate(_STATE_JS)
        parts = [p.strip() for p in d["sel"].split("|")]
        storage, color, carrier = (parts + [None, None, None])[:3] if len(parts) >= 3 else (None, None, None)
        sku = None
        m = re.search(r"/\s*(SM-[A-Z0-9]+)$", d["skuLine"])
        if m:
            sku = m.group(1)
        sku = sku or _sku_from_url(page.url)
        total = money_tokens(d["total"], ctx.locale)
        was = re.search(r"was\s*(\$[\d,.]+)", d["total"])
        head = money_tokens(d["headline"], ctx.locale)
        monthly = next((t for t in head if f"{t}/mo" in d["headline"].replace(" ", "")), None)
        selection = {k: v for k, v in (("storage", storage), ("color", color), ("carrier", carrier)) if v}
        return State(selection, None, sku,
                     PriceTexts(base=total[0] if total else None, monthly=monthly,
                                headline=d["headline"] or None, was=was.group(1) if was else None))

    def section_boxes(self, page) -> list[tuple[str, Box]]:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        out: list[tuple[str, Box]] = []
        bar = _rect(page, "(() => { let e = document.querySelector('h1'); "
                          "while (e && e.getBoundingClientRect().width < 1300) e = e.parentElement; return e; })()")
        if bar:
            out.append(("Price bar", bar))
        out += [(t, tuple(b)) for t, b in page.evaluate(_SECTIONS_JS)]
        summary = _rect(page, "(() => { const c = [...document.querySelectorAll('div')].filter(e => "
                              "/You Saved Today|Total/.test(e.innerText) && /SM-[A-Z0-9]+ \\/ SM-/.test(e.innerText) "
                              "&& e.getBoundingClientRect().width > 500); "
                              "return c.sort((a, b) => a.innerText.length - b.innerText.length)[0]; })()")
        if summary:
            out.append(("Summary", summary))
        return out

    def _dialog_box(self, page) -> Box | None:
        return _rect(page, "[...document.querySelectorAll('[role=dialog], [aria-modal=true], [class*=Overlay_wrapper]')]"
                           ".filter(e => e.getBoundingClientRect().height > 50).pop()")

    def extra_shots(self, page) -> Iterator[tuple[str, Box]]:
        for title, locator in (("Carrier deals", page.get_by_text("See all deals", exact=True)),
                               ("Care+ details", page.locator("button", has_text=re.compile(r"^\s*Details\s*$")))):
            target = next((locator.nth(i) for i in range(locator.count()) if locator.nth(i).is_visible()), None)
            if target is None:
                continue
            target.scroll_into_view_if_needed()
            target.click(timeout=5000)
            page.wait_for_timeout(1500)
            box = self._dialog_box(page)
            if box:
                yield title, box
            self.close_extras(page)

    def close_extras(self, page) -> None:
        page.keyboard.press("Escape")
        page.wait_for_timeout(600)
        close = page.locator("[role=dialog] button[aria-label*='close' i], [class*=Overlay_wrapper] button[aria-label*='close' i]")
        if close.count() and close.first.is_visible():
            close.first.click(timeout=3000)
            page.wait_for_timeout(600)
