"""Driver for the hubble buying tool used by samsung.com/uk, /ca, /ca_fr buy pages."""
from __future__ import annotations

import re
from typing import Iterator

from ..model import Context, PriceTexts, Product, State
from ..prices import money_tokens
from .base import Box, OptionNotFound, OptionUnavailable

WAIT_MS = 5000  # spec: wait 5s after (re)load
REGION_NAMES = {"CA-ON": ["Ontario"], "CA-QC": ["Québec", "Quebec"]}
REGION_BTN = "button.menu__select-field[data-aria-label='change region']"
STORAGE = "input.hubble-pd-radio__input[name^='memory-rdo']"
COLOR = "input.hubble-pd-radio__input[name$='color']"

_SECTIONS_JS = r"""
() => {
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const heads = [...document.querySelectorAll('h2.s-option-title, h2.s-sub-title')].filter(vis);
  const rows = heads.map(h => {
    const box = (h.closest('.hubble-product__options') || h.parentElement).getBoundingClientRect();
    const r = h.getBoundingClientRect();
    return {t: h.innerText.trim().replace(/\s+/g, ' '), y: r.top + scrollY, x: box.left + scrollX, w: box.width,
            boxTop: box.top + scrollY, bottom: box.bottom + scrollY};
  }).sort((a, b) => a.y - b.y);
  // A section starts at its heading, or at its container's top when the container begins after the previous
  // heading (e.g. the feature icons that sit above "Device").
  const tops = rows.map((r, i) => (i === 0 || rows[i - 1].y < r.boxTop) ? Math.min(r.y - 12, r.boxTop) : r.y - 12);
  return rows.map((r, i) => {
    const next = i + 1 < rows.length ? tops[i + 1] : r.bottom;
    return [r.t, [r.x, tops[i], r.w, Math.max(40, next - tops[i])]];
  });
}
"""


def _box(page, selector: str) -> Box | None:
    loc = page.locator(selector).first
    if not loc.count() or not loc.is_visible():
        return None
    b = page.evaluate("""s => { const r = document.querySelector(s).getBoundingClientRect();
        return [r.left + scrollX, r.top + scrollY, r.width, r.height]; }""", selector)
    return tuple(b) if b[2] > 0 and b[3] > 0 else None


def _click_if_visible(page, selector: str) -> bool:
    loc = page.locator(selector)
    try:
        for i in range(loc.count()):
            if loc.nth(i).is_visible():
                loc.nth(i).click(timeout=3000)
                page.wait_for_timeout(800)
                return True
    except Exception:
        pass
    return False


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


class HubbleDriver:
    def prepare(self, page, ctx: Context) -> list[str]:
        warnings: list[str] = []
        _click_if_visible(page, "#truste-consent-required")
        if ctx.region and not self._region_ok(page, ctx.region):
            # The province picker does not apply headless; the site keeps the choice in this cookie.
            page.context.add_cookies([{"name": "country_region", "value": ctx.region,
                                       "domain": ".samsung.com", "path": "/"}])
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT_MS)
            _click_if_visible(page, "#truste-consent-required")
            if not self._region_ok(page, ctx.region):
                warnings.append(f"region not applied: shows {self._region_text(page)}")
        return warnings

    def _region_text(self, page) -> str | None:
        loc = page.locator(REGION_BTN).first
        return loc.inner_text().strip() if loc.count() else None

    def _region_ok(self, page, region: str) -> bool:
        return (self._region_text(page) or "") in REGION_NAMES.get(region, [region])

    def _radio(self, page, selector: str, match) -> str | None:
        rows = page.eval_on_selector_all(selector, """els => els.map(e => ({id: e.id,
            en: e.dataset.englishname || '', dn: e.dataset.displayname || '', code: e.dataset.modelcode || '',
            disabled: e.disabled}))""")
        for r in rows:
            if match(r):
                return None if r["disabled"] else r["id"]
        if rows:  # the site lists options for this axis but not this one: it does not offer it
            raise OptionUnavailable(f"not offered; shown: {[r['dn'] or r['en'] for r in rows]}")
        raise OptionNotFound(f"no options at all for {selector}")

    def _click_radio(self, page, input_id: str) -> None:
        label = page.locator(f"label[for='{input_id}']").first
        if label.count() and label.is_visible():
            label.click(timeout=5000)
        else:
            page.locator(f"#{input_id}").check(force=True, timeout=5000)

    def select(self, page, axis: str, value: str, product: Product) -> None:
        if axis == "storage":
            want = _norm(value)
            rid = self._radio(page, STORAGE, lambda r: _norm(r["dn"].split("｜")[0]) == want)
        elif axis == "color":
            code = product.colors.get(value)
            rid = self._radio(page, COLOR, lambda r: r["en"].lower() == value.lower() or (code and r["code"][8:10] == code))
        else:
            return
        if rid is None:
            raise OptionUnavailable(f"{axis} {value} is disabled")
        self._click_radio(page, rid)

    def read_state(self, page, ctx: Context, product: Product) -> State:
        d = page.evaluate(f"""() => {{
          const st = document.querySelector("{STORAGE}:checked"), co = document.querySelector("{COLOR}:checked");
          const lab = st && (document.querySelector('label[for="' + st.id + '"]') || st.closest('label'));
          const cart = document.querySelector('.price-bar-cart-btn[data-modelcode]');
          const bar = document.querySelector('.hubble-price-bar__price');
          const was = lab && lab.querySelector('del, s, [class*=was], [class*=strike]');
          return {{storage: st && st.dataset.displayname, color_en: co && co.dataset.englishname,
                  color_code: co && co.dataset.modelcode, sku: (cart && cart.dataset.modelcode) || (co && co.dataset.modelcode),
                  label: lab && lab.innerText, headline: bar && bar.innerText, was: was && was.innerText}};
        }}""")
        storage = (d["storage"] or "").split("｜")[0].strip() or None
        color = None
        for name, code in product.colors.items():
            if (d["color_en"] or "").lower() == name.lower() or (d["color_code"] or "")[8:10] == code:
                color = name
                break
        toks = money_tokens(d["label"] or "", ctx.locale)
        label = d["label"] or ""
        monthly = toks[0] if len(toks) > 1 and "/mo" in label else None
        ws = lambda s: re.sub(r"\s+", " ", s).strip() if s else None
        return State(storage, color, None, self._region_text(page), d["sku"],
                     PriceTexts(base=toks[-1] if toks else None, monthly=monthly, headline=ws(d["headline"]),
                                was=ws(d["was"])))

    def section_boxes(self, page) -> list[tuple[str, Box]]:
        # Jumping straight back from far down leaves the price bar stuck at top 0; a small scroll event
        # makes it return under the header, then wait until its position settles.
        page.evaluate("window.scrollTo(0, 200)")
        page.wait_for_timeout(300)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
        last = None
        for _ in range(10):
            top = page.evaluate("(() => { const e = document.querySelector('.hubble-price-bar'); "
                                "return e ? Math.round(e.getBoundingClientRect().top) : null; })()")
            if top == last:
                break
            last = top
            page.wait_for_timeout(300)
        out: list[tuple[str, Box]] = []
        bar = _box(page, ".hubble-price-bar")
        if bar:
            out.append(("Price bar", bar))
        out += [(t, tuple(b)) for t, b in page.evaluate(_SECTIONS_JS)]
        summary = _box(page, ".hubble-product__summary")
        if summary:
            out.append(("Summary", summary))
        return out

    def extra_shots(self, page) -> Iterator[tuple[str, Box]]:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        # The offer banner (one slide in CA, a carousel in UK) expands in place. Its CTA never settles for a
        # real click and also scrolls to the trade-in block, so click via JS and come back to the top.
        opener = page.locator("button.s-offer-open")
        idx = next((i for i in range(opener.count()) if opener.nth(i).is_visible()), None)
        if idx is not None:
            opener.nth(idx).evaluate("e => e.click()")
            page.wait_for_timeout(1000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(800)
            box = _box(page, ".hubble-offer-banner-v2-wrap")
            if box:
                yield "Offer banner", box
            opener.nth(idx).evaluate("e => e.click()")
            page.wait_for_timeout(500)

    def close_extras(self, page) -> None:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
