"""Driver for the AEM product page template (hdd02 buying tool) used by UK/CA/CA-FR TVs and appliances."""
from __future__ import annotations

import re
from typing import Iterator

from ..model import Context, Option, PriceTexts, Product, State
from ..prices import money_tokens
from .base import BaseDriver, Box, OptionNotFound, OptionUnavailable
from .common import (
    close_layers, dismiss_banners, ensure_region, js_click, norm_label, open_layer_box, pdd32_specs, region_text,
    box_of,
)

AXIS_INPUTS = {"size": "input[name='pd-size']", "color": "input[name='pd-color']"}
OTHER_INPUTS = "input[name^='pd-others-']"
UNAVAILABLE = re.compile(r"no longer available|out of stock|rupture de stock|n'est plus disponible", re.I)
SNAPSHOT_KEEP = [".pdd39-anchor-nav", ".hdd02-pdp-header", "#sgDevPriceAreaBase", "section.hdd02-buying-tool", "#specs", "aside.nv16-country-selector",
                 ".cod03-delivery-location-selector"]

_STATE_JS = r"""
(axes) => {
  const q = s => document.querySelector(s);
  const t = e => e ? e.innerText.replace(/\s+/g, ' ').trim() : null;
  // first match with text: markup repeats blocks (desktop/mobile) and nests <p> in <p>
  const ft = s => [...document.querySelectorAll(s)].map(t).find(Boolean) || null;
  const own = e => e ? [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').replace(/\s+/g, ' ').trim() : null;
  const sel = {};
  for (const [axis, css] of Object.entries(axes)) {
    const i = q(css + ':checked');
    if (!i) continue;
    const lab = q(`label[for='${i.id}']`);
    sel[axis] = (i.dataset.colorname || t(lab) || i.value || '').trim();
  }
  const cta = q('.pdd39-anchor-nav__cta [data-modelcode], .cost-box__cta [data-modelcode], .cost-box [data-sku-code]');
  const base = q('.pdd39-anchor-nav .pd-buying-price__new-price-currency, #sgDevPriceAreaBase .pd-buying-price__new-price-currency');
  const inner = q('.pdd39-anchor-nav .pd-buying-price__new-price-inner, #sgDevPriceAreaBase .pd-buying-price__new-price-inner');
  const newp = q('.pdd39-anchor-nav .pd-buying-price__new-price, #sgDevPriceAreaBase .pd-buying-price__new-price');
  const was = ft('.pdd39-anchor-nav .pd-buying-price__was, #sgDevPriceAreaBase .pd-buying-price__was');
  const saving = ft('.pdd39-anchor-nav .pd-buying-price__text-saving-info, #sgDevPriceAreaBase .pd-buying-price__text-saving-info');
  const priceArea = q('.pdd39-anchor-nav__price, .pdd39-anchor-nav__top');
  return {
    sel,
    sku: t(q('.pdd39-anchor-nav__info-sku')) || (cta && (cta.dataset.modelcode || cta.dataset.skuCode)) || null,
    base: t(base), inner_own: own(inner), newp: t(newp),
    was: was ? was.replace(/^RRP:\s*/i, '') : null, saving: saving,
    headline: t(priceArea),
    cta: t(q('.pdd39-anchor-nav__cta')), summary: t(q('.hdd02-buying-tool__summary')),
  };
}
"""

_SECTIONS_JS = r"""
() => {
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const t = e => e ? e.innerText.replace(/\s+/g, ' ').trim() : '';
  const bx = e => { const r = e.getBoundingClientRect(); return [r.left + scrollX, r.top + scrollY, r.width, r.height]; };
  const out = [];
  for (const blk of document.querySelectorAll('.hdd02-buying-tool__option > *')) {
    if (!vis(blk) || blk.getBoundingClientRect().height < 20) continue;
    const h = blk.querySelector('h3.pd-select-option__headline, .pd-select-option__headline-wrap, p.pd-sellout-option__headline');
    out.push([h ? t(h).slice(0, 120) : 'Offers', bx(blk)]);
  }
  return out;
}
"""


class PdDriver(BaseDriver):
    def prepare(self, page, ctx: Context) -> list[str]:
        dismiss_banners(page)
        warnings = ensure_region(page, ctx)
        self._wait_templates(page)
        return warnings

    def _wait_templates(self, page, timeout_ms: int = 12000) -> None:
        """Prices render client-side: wait until '{{…}}' placeholders are gone and a price (or a sold-out notice) shows."""
        for _ in range(timeout_ms // 500):
            d = page.evaluate("""(() => { const t = s => { const e = document.querySelector(s); return e ? e.innerText : ''; };
                return [t('.hdd02-buying-tool__summary') + t('.pdd39-anchor-nav'), t('.pdd39-anchor-nav .pd-buying-price__new-price')]; })()""")
            if "{{" not in d[0] and (re.search(r"\d", d[1]) or UNAVAILABLE.search(d[0])):
                return
            page.wait_for_timeout(500)

    def _axis_css(self, axis: str) -> str:
        return AXIS_INPUTS.get(axis, OTHER_INPUTS)

    def options(self, page, ctx: Context, axis: str) -> list[Option]:
        rows = page.eval_on_selector_all(self._axis_css(axis), r"""els => els.map(e => {
            const lab = document.querySelector(`label[for='${e.id}']`);
            const text = lab ? lab.innerText.replace(/\s+/g, ' ').trim() : '';
            return {id: e.id, label: (e.dataset.colorname || text.split(' ')[0] || e.value || '').trim(), full: text,
                    sku: e.dataset.modelcode || null, disabled: e.disabled};
        })""")
        out = []
        for r in rows:
            if not r["id"]:
                continue
            out.append(Option(axis, norm_label(r["label"]), r["label"], (r["sku"] or "").upper() or None,
                              available=not r["disabled"] and not UNAVAILABLE.search(r["full"] or ""), handle=r["id"]))
        return out

    def _sku(self, page) -> str | None:
        return page.evaluate(r"""(() => { const t = document.querySelector('.pdd39-anchor-nav__info-sku');
            if (t && t.innerText.trim()) return t.innerText.trim();
            const c = document.querySelector('.pdd39-anchor-nav__cta [data-modelcode], .cost-box__cta [data-modelcode]');
            return c ? c.dataset.modelcode : null; })()""")

    def choose(self, page, ctx: Context, option: Option) -> None:
        if not option.handle or not page.locator(f"#{option.handle}").count():
            raise OptionNotFound(f"{option.axis} {option.label}: no input #{option.handle}")
        if not option.available:
            raise OptionUnavailable(f"{option.axis} {option.label} is marked unavailable")
        before = page.url
        if not js_click(page, f"label[for='{option.handle}']"):
            page.locator(f"#{option.handle}").check(force=True, timeout=5000)
        for _ in range(20):  # colour often navigates to another product URL; size updates in place
            page.wait_for_timeout(500)
            if page.url.split("?")[0] != before.split("?")[0]:
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(3000)
                self.prepare(page, ctx)
                return
            if option.sku and (self._sku(page) or "").upper() == option.sku:
                return

    def read_state(self, page, ctx: Context, product: Product) -> State:
        axes = {a.name: self._axis_css(a.name) for a in (ctx.axes if ctx.axes is not None else product.axes)}
        d = page.evaluate(_STATE_JS, axes)
        own = d["inner_own"] or ""
        toks = money_tokens(d["newp"] or "", ctx.locale)
        base = d["base"] or (toks[-1] if toks else None)
        monthly = money_tokens(own, ctx.locale)[0] if "/mo" in own and money_tokens(own, ctx.locale) else None
        was = d["was"] or (money_tokens(d["saving"] or "", ctx.locale) or [None])[0]
        blob = " ".join(x for x in (d["cta"], d["summary"]) if x)
        return State(d["sel"], region_text(page), (d["sku"] or "").upper() or None,
                     PriceTexts(base=base, monthly=monthly, headline=d["headline"], was=was),
                     available=False if UNAVAILABLE.search(blob) and not base else True)

    def _settle_price_bar(self, page) -> None:
        page.evaluate("window.scrollTo(0, 200)")
        page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 0)")
        last = None
        for _ in range(10):
            page.wait_for_timeout(300)
            top = page.evaluate("(() => { const e = document.querySelector('.pdd39-anchor-nav');"
                                " return e ? Math.round(e.getBoundingClientRect().top) : null; })()")
            if top == last:
                return
            last = top

    def section_boxes(self, page) -> list[tuple[str, Box]]:
        self._settle_price_bar(page)
        out: list[tuple[str, Box]] = []
        bar = box_of(page, ".pdd39-anchor-nav__top") or box_of(page, ".pdd39-anchor-nav")
        if bar:
            out.append(("Price bar", bar))
        out += [(t, tuple(b)) for t, b in page.evaluate(_SECTIONS_JS)]
        summary = box_of(page, ".hdd02-buying-tool__summary") or box_of(page, ".hdd02-buying-tool__cost-box")
        if summary:
            out.append(("Summary", summary))
        return out

    def section_titles(self, page) -> list[str]:
        return [t for t, _ in page.evaluate(_SECTIONS_JS)]

    def extra_shots(self, page) -> Iterator[tuple[str, Box]]:
        layers = [
            ("Finance options", "a[data-target-popup='eipPopup']"),
            ("Trade-up details", "button[an-la='trade-up:learn more']"),
            ("Trade-in details", "#trade-in .pd-select-option__cta-wrap button"),
            ("Measure your space", "a[data-target-popup='dimensionsPopup']"),
            ("Samsung Care+ plans", "label[for='pd-extended-warranty-option-0']"),
        ]
        for title, opener in layers:
            box = open_layer_box(page, opener)
            if box:
                yield title, box
            close_layers(page)

    def close_extras(self, page) -> None:
        close_layers(page)
        # The Care+ layer selects "Yes" when opened; put the default back so the summary keeps the device only.
        js_click(page, "label[for='pd-extended-warranty-option-1']")

    def specs(self, page):
        return pdd32_specs(page)
