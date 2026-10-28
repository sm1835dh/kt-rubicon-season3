"""Helpers shared by template drivers: spec extraction, layers, banners."""
from __future__ import annotations

import re

from ..model import SpecItem
from .base import Box

REGION_BTN = "button.menu__select-field[data-aria-label='change region']"
REGION_NAMES = {"CA-ON": ["Ontario"], "CA-QC": ["Québec", "Quebec"]}

_BOX_JS = """e => { const r = e.getBoundingClientRect(); return [r.left + scrollX, r.top + scrollY, r.width, r.height]; }"""

_PDD32_JS = r"""
() => {
  const out = [];
  for (const item of document.querySelectorAll('.pdd32-product-spec__content-item')) {
    const g = item.closest('.pdd32-product-spec__item');
    const gt = g && g.querySelector('.pdd32-product-spec__title');
    const t = item.querySelector('.pdd32-product-spec__content-item-title');
    const d = item.querySelector('.pdd32-product-spec__content-item-desc');
    if (!t) continue;
    const clean = e => e ? e.textContent.replace(/\s+/g, ' ').trim() : '';
    out.push([clean(gt), clean(t), clean(d)]);
  }
  return out;
}
"""

_US_SPECS_JS = r"""
() => {
  const out = [];
  const clean = e => e ? e.textContent.replace(/\s+/g, ' ').trim() : '';
  for (const name of document.querySelectorAll('[class*=Specs_subSpecItemName]')) {
    const item = name.closest('[class*=Specs_subSpecsItem]') || name.parentElement;
    const val = item.querySelector('[class*=Specs_subSpecsItemValue]');
    const li = name.closest('li');
    const gn = li && li.querySelector('[class*=Specs_specGroupName]');
    const label = name.querySelector('[itemprop=name]') || name;  // the tooltip sits beside [itemprop=name]
    out.push([clean(gn), clean(label), clean(val)]);
  }
  return out;
}
"""


def box_of(page, selector: str) -> Box | None:
    loc = page.locator(selector)
    for i in range(loc.count()):
        el = loc.nth(i)
        try:
            if el.is_visible():
                b = el.evaluate(_BOX_JS)
                if b[2] > 0 and b[3] > 0:
                    return tuple(b)
        except Exception:
            continue
    return None


def js_click(page, selector: str) -> bool:
    """Click the first visible match through JS (carousels and overlays block real clicks)."""
    loc = page.locator(selector)
    for i in range(loc.count()):
        try:
            if loc.nth(i).is_visible():
                loc.nth(i).evaluate("e => e.click()")
                return True
        except Exception:
            continue
    return False


def dismiss_banners(page) -> None:
    """Cookie consent (if the preset cookies did not suppress it), geo bar and chat teasers."""
    for sel in ("#truste-consent-required", ".truste-banner-close", ".nv16-country-selector__close"):
        if js_click(page, sel):
            page.wait_for_timeout(800)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10000)
    except Exception:
        pass


def region_text(page) -> str | None:
    loc = page.locator(REGION_BTN)
    return loc.first.inner_text().strip() if loc.count() else None


def ensure_region(page, ctx, wait_ms: int = 5000) -> list[str]:
    """CA province: the cookie set before load should already apply; reload once if it did not."""
    if not ctx.region:
        return []
    names = REGION_NAMES.get(ctx.region, [ctx.region])
    if (region_text(page) or "") in names:
        return []
    page.context.add_cookies([{"name": "country_region", "value": ctx.region, "domain": ".samsung.com", "path": "/"}])
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(wait_ms)
    dismiss_banners(page)
    return [] if (region_text(page) or "") in names else [f"region not applied: shows {region_text(page)}"]


def pdd32_specs(page) -> tuple[list[SpecItem], list[tuple[str, Box]]]:
    """AEM product spec section (#specs.pdd32-product-spec): every item is in the DOM, groups are collapsed."""
    if not page.locator(".pdd32-product-spec").count():
        return [], []
    btn = page.locator(".pdd32-product-spec__expand-cta button")
    if btn.count():
        label = (btn.first.text_content() or "").lower()
        if "collapse" not in label and "réduire" not in label:
            try:
                btn.first.scroll_into_view_if_needed(timeout=5000)
                btn.first.evaluate("e => e.click()")
                page.wait_for_timeout(1500)
            except Exception:
                pass
    items = [SpecItem(g, t, d) for g, t, d in page.evaluate(_PDD32_JS)]
    box = box_of(page, ".pdd32-product-spec")
    return items, ([("Specs", box)] if box else [])


def us_specs(page) -> tuple[list[SpecItem], list[tuple[str, Box]]]:
    """US Next.js specs: 'See All Specs' button (PDP) or a 'Specs' accordion (buy pages)."""
    for sel in ("a[class*=Specs_expandBtn]", "[data-testid=accordion-title]:has-text('Specs')",
                "[aria-label='Specs'][role=button]"):
        loc = page.locator(sel)
        if loc.count():
            try:
                loc.first.scroll_into_view_if_needed(timeout=5000)
                text = (loc.first.text_content() or "").lower()
                if "hide" not in text:
                    loc.first.evaluate("e => e.click()")
                page.wait_for_timeout(2000)
            except Exception:
                pass
            break
    items = [SpecItem(g, t, d) for g, t, d in page.evaluate(_US_SPECS_JS)]
    box = None
    for sel in ("[class*=Specs_productSpec]", "[id='#specs']", "#accordion-Specs", "[class*=Specs_specContainer]"):
        box = box_of(page, sel)
        if box:
            break
    return items, ([("Specs", box)] if box else [])


def open_layer_box(page, opener: str, layer: str = ".layer-popup", inner: str = ".layer-popup__inner",
                   wait_ms: int = 1500) -> Box | None:
    """Click an opener and return the box of the opened AEM layer (the caller closes it)."""
    if not js_click(page, opener):
        return None
    page.wait_for_timeout(wait_ms)
    for sel in (f"{layer}[aria-hidden='false'] {inner}", f"{layer}.is-active {inner}", f"{layer} {inner}"):
        b = box_of(page, sel)
        if b:
            return b
    return None


def close_layers(page) -> None:
    js_click(page, ".layer-popup .layer-popup__close")
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)


def norm_label(s: str | None) -> str:
    return re.sub(r"[\s\"'″”“’]+", "", (s or "")).lower()
