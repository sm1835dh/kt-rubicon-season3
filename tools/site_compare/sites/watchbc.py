"""Driver for the watch buying tool (watch-bc) used by samsung.com/uk, /ca, /ca_fr Galaxy Watch buy pages.

`/buy/?modelCode=<SKU>` opens the page with that variant selected, so combos are reached directly.
"""
from __future__ import annotations

import re
from typing import Iterator

from ..model import Context, Option, PriceTexts, Product, State
from .base import BaseDriver, Box, OptionNotFound, OptionUnavailable
from .common import box_of, dismiss_banners, ensure_region, js_click, norm_label, region_text

AXIS_CODES = {"device": "C-DVC", "size": "C-SIZ", "connectivity": "C-CON", "color": "C-CLR",
              "band_type": "B-TYP", "band_color": "B-CLR", "band_size": "B-SIZ"}
UNAVAILABLE = re.compile(r"out of stock|rupture de stock|no longer available", re.I)
SNAPSHOT_KEEP = [".watch-bc-price-bar", ".watch-bc-offer-banner-wrap", ".watch-bc-option__option[data-type-code]",
                 ".watch-bc-buyflow", ".total-summary", ".cod03-delivery-location-selector"]

_STATE_JS = r"""
(codes) => {
  const t = e => e ? e.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = s => document.querySelector(s);
  const sel = {};
  for (const [axis, code] of Object.entries(codes)) {
    const grp = q(`.watch-bc-option__option[data-type-code='${code}']`);
    if (!grp) continue;
    const i = grp.querySelector('input:checked') || (grp.querySelector('.is-checked input'));
    if (i) sel[axis] = (i.dataset.modeldisplay || i.value || '').trim();
  }
  return {sel, sku: t(q('.total-summary .model-code')), base: t(q('strong.bar-total-price')),
          was: (() => { const e = q('.bar-was-price'); return e && e.offsetParent ? t(e) : null; })(),
          headline: t(q('.watch-bc-price-bar')), cta: t(q('.watch-bc-price-bar .cta, .total-summary .cta'))};
}
"""

_SECTIONS_JS = r"""
() => {
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const t = e => e ? e.innerText.replace(/\s+/g, ' ').trim() : '';
  const bx = e => { const r = e.getBoundingClientRect(); return [r.left + scrollX, r.top + scrollY, r.width, r.height]; };
  const out = [];
  for (const g of document.querySelectorAll('.watch-bc-option__option[data-type-code]')) {
    if (vis(g)) out.push([t(g.querySelector('h2.watch-bc-option__option-title')) || g.dataset.typeCode, bx(g)]);
  }
  for (const f of document.querySelectorAll('.watch-bc-buyflow')) {
    const h = f.querySelector('.watch-bc-buyflow__headline-title');
    if (vis(f) && h && t(h)) out.push([t(h).slice(0, 120), bx(f)]);
  }
  return out.sort((a, b) => a[1][1] - b[1][1]);
}
"""


class WatchBcDriver(BaseDriver):
    def prepare(self, page, ctx: Context) -> list[str]:
        dismiss_banners(page)
        warnings = ensure_region(page, ctx)
        self._wait_price(page)
        return warnings

    def _wait_price(self, page, timeout_ms: int = 10000) -> None:
        for _ in range(timeout_ms // 500):
            if re.search(r"\d", page.evaluate("(() => { const e = document.querySelector('strong.bar-total-price');"
                                              " return e ? e.innerText : ''; })()")):
                return
            page.wait_for_timeout(500)

    def sku_url(self, ctx: Context, sku: str | None) -> str | None:
        return f"{ctx.url.split('?')[0]}?modelCode={sku}" if sku else None

    def options(self, page, ctx: Context, axis: str) -> list[Option]:
        code = AXIS_CODES.get(axis)
        if not code:
            return []
        rows = page.eval_on_selector_all(f".watch-bc-option__option[data-type-code='{code}'] input", r"""els => els.map(e => {
            const lab = document.querySelector(`label[for='${e.id}']`);
            const item = e.closest('.watch-bc-option__option-item');
            const hidden = item && getComputedStyle(item).display === 'none';
            return {id: e.id, label: (e.dataset.modeldisplay || (lab && lab.innerText) || e.value || '').replace(/\s+/g, ' ').trim(),
                    // data-modelcode can be a case-only code (…ZKDWEU); the preset code is the sellable SKU
                    sku: e.dataset.productPresetmodelcode || e.dataset.modelcode || null, ok: !e.disabled && !hidden,
                    soldout: !!(item && /out of stock|rupture/i.test(item.innerText))};
        })""")
        out, seen = [], set()
        for r in rows:
            key = norm_label(r["label"])
            if not r["id"] or not key or key in seen:
                continue
            seen.add(key)
            out.append(Option(axis, key, r["label"], (r["sku"] or "").upper() or None,
                              available=r["ok"] and not r["soldout"], handle=r["id"]))
        return out

    def _sku(self, page) -> str:
        return (page.evaluate("(() => { const e = document.querySelector('.total-summary .model-code');"
                              " return e ? e.innerText.trim() : ''; })()") or "").upper()

    def choose(self, page, ctx: Context, option: Option) -> None:
        if not option.handle or not page.locator(f"#{option.handle}").count():
            raise OptionNotFound(f"{option.axis} {option.label}: no input #{option.handle}")
        if not option.available:
            raise OptionUnavailable(f"{option.axis} {option.label} is hidden or disabled")
        before = self._sku(page)
        if not js_click(page, f"label[for='{option.handle}']"):
            page.locator(f"#{option.handle}").evaluate("e => e.click()")
        for _ in range(20):  # the price bar blanks for ~1-2 s and the option DOM re-renders
            page.wait_for_timeout(500)
            sku = self._sku(page)
            if (option.sku and sku == option.sku) or (not option.sku and sku and sku != before):
                break
        self._wait_price(page)

    def read_state(self, page, ctx: Context, product: Product) -> State:
        d = page.evaluate(_STATE_JS, AXIS_CODES)
        blob = d["cta"] or ""
        return State(d["sel"], region_text(page), (d["sku"] or "").upper() or None,
                     PriceTexts(base=d["base"], headline=d["headline"], was=d["was"]),
                     available=False if UNAVAILABLE.search(blob) and not d["base"] else True)

    def section_boxes(self, page) -> list[tuple[str, Box]]:
        page.evaluate("window.scrollTo(0, 200)")
        page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(800)
        out: list[tuple[str, Box]] = []
        for title, sel in (("Price bar", ".watch-bc-price-bar"), ("Offer banner", ".watch-bc-offer-banner-wrap")):
            b = box_of(page, sel)
            if b:
                out.append((title, b))
        out += [(t, tuple(b)) for t, b in page.evaluate(_SECTIONS_JS)]
        summary = box_of(page, ".total-summary")
        if summary:
            out.append(("Summary", summary))
        return out

    def section_titles(self, page) -> list[str]:
        return [t for t, _ in page.evaluate(_SECTIONS_JS)]

    def extra_shots(self, page) -> Iterator[tuple[str, Box]]:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        btn = page.locator("button.s-offer-open")
        for i in range(btn.count()):  # the UK carousel clones slides at negative x
            el = btn.nth(i)
            try:
                if el.is_visible() and el.evaluate("e => e.getBoundingClientRect().left >= 0"):
                    el.evaluate("e => e.click()")
                    page.wait_for_timeout(1000)
                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(600)
                    b = box_of(page, ".watch-bc-offer-banner-wrap")
                    if b:
                        yield "Offer banner (expanded)", b
                    el.evaluate("e => e.click()")
                    break
            except Exception:
                continue
