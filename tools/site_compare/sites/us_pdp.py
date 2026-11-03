"""Driver for samsung.com/us product pages (Next.js, templateType "VD"): TVs and appliances.

The page itself is the `-sku-<model>/` URL; choosing a tile routes to another SKU URL.
"""
from __future__ import annotations

import re
from typing import Iterator

from ..model import Context, Option, PriceTexts, Product, State
from ..prices import money_tokens
from .base import BaseDriver, Box, OptionNotFound, OptionUnavailable
from .common import box_of, click_tile, dismiss_banners, norm_label, us_specs

UNAVAILABLE = re.compile(r"not available in your area|out of stock|no longer available|sold out", re.I)
SNAPSHOT_KEEP = ["[class*=Header_headerContainer]", "[class*=PriceInfoText_]", "[class*=ModelInfo_]",
                 "[data-testid=SeriesTile]", "[data-testid=sizeTileSelect]", "[aria-label^='Color Variant:']",
                 "[role=heading][aria-level='2']", "[data-testid=paymentCardClass]", "#product-summary",
                 "[class*=Summary_container]", "[class*=Specs_productSpec]"]

_SKU_RE = re.compile(r"-sku-([a-z0-9-]+)/?(?:\?.*)?$", re.I)
_LAYERS = [("Samsung Care+ terms", "button[class*=CarePlus_ux2Anchor]"),
           ("Delivery details", "button[class*=ScrollableButtonGroup_ux2Anchor]"),
           ("Measure your space", "button[class*=Measurement_startMesaureCta]"),
           ("Depth details", "[an-la='depth:learn more']")]

_STATE_JS = r"""
() => {
  const t = e => e ? e.innerText.replace(/\s+/g, ' ').trim() : null;
  const q = s => document.querySelector(s);
  const checked = sel => [...document.querySelectorAll(sel)].find(e =>
      e.getAttribute('aria-checked') === 'true' || e.getAttribute('aria-pressed') === 'true' || /selected/i.test(e.className));
  const size = checked("[data-testid=sizeTileSelect][role=radio]");
  const color = checked("[aria-label^='Color Variant:']");
  const series = [...document.querySelectorAll("[data-testid=SeriesTile][role=radio]")].filter(e => e.getAttribute('aria-checked') === 'true');
  const cards = [...document.querySelectorAll('[data-testid=paymentCardClass]')].map(t);
  const model = t(q('[class*=ModelInfo_]'));
  return {
    size: size && (size.getAttribute('aria-label') || '').replace(/^Size:\s*/i, ''),
    color: color && (color.getAttribute('aria-label') || '').replace(/^Color Variant:\s*/i, ''),
    series: series.map(e => [e.getAttribute('an-la') || '', t(e)]),
    model, cards,
    total: t(q('#product-summary [class*=Summary_totalprice], [class*=Summary_container] [class*=Summary_totalprice]')),
    header: t(q('[class*=PriceInfoText_]')),
    avail: [t(q('#product-summary')), t(q('[class*=PriceInfoText_]')), t(q('#delivery'))].filter(Boolean).join(' '),
  };
}
"""

_SECTIONS_JS = r"""
() => {
  const vis = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const summary = document.querySelector('#product-summary') || document.querySelector('[class*=Summary_container]');
  const stop = summary ? summary.getBoundingClientRect().top + scrollY : Infinity;
  const pw = document.documentElement.clientWidth;
  const heads = [];
  for (const h of document.querySelectorAll("[role=heading][aria-level='2']")) {
    if (!vis(h)) continue;
    const t = (h.innerText || '').replace(/\s+/g, ' ').trim();
    const r = h.getBoundingClientRect(), y = r.top + scrollY;
    if (!t || y >= stop || r.left >= pw) continue;
    let box = h.parentElement;
    while (box && box.getBoundingClientRect().height < r.height * 3) box = box.parentElement;
    const br = (box || h).getBoundingClientRect();
    heads.push({t: t.slice(0, 120), y, x: br.left + scrollX, w: Math.min(br.width, pw - br.left)});
  }
  heads.sort((a, b) => a.y - b.y);
  return heads.map((h, i) => {
    const top = h.y - 12, next = i + 1 < heads.length ? heads[i + 1].y - 12 : Math.min(stop, top + 1200);
    return [h.t, [h.x, top, h.w, Math.max(40, next - top)]];
  });
}
"""


def sku_from_url(url: str) -> str | None:
    m = _SKU_RE.search(url or "")
    return m.group(1).upper() if m else None


class UsPdpDriver(BaseDriver):
    def prepare(self, page, ctx: Context) -> list[str]:
        dismiss_banners(page)
        return []

    def _tiles(self, axis: str) -> tuple[str, str]:
        """(selector, attribute holding the label) for an axis."""
        if axis == "size":
            return "[data-testid=sizeTileSelect][role=radio]", "aria-label"
        if axis == "color":
            return "[aria-label^='Color Variant:']", "aria-label"
        return f"[data-testid=SeriesTile][role=radio][an-la^='{axis}:']", "an-la"

    def options(self, page, ctx: Context, axis: str) -> list[Option]:
        sel, attr = self._tiles(axis)
        try:  # tiles hydrate a few seconds after load
            page.wait_for_selector(sel, state="attached", timeout=15000)
        except Exception:
            return []
        rows = page.eval_on_selector_all(sel, f"""els => els.map(e => ({{handle: e.getAttribute('{attr}'),
            text: (e.innerText || '').replace(/\\s+/g, ' ').trim(), sku: e.dataset.modelcode || null,
            disabled: e.getAttribute('aria-disabled') === 'true' || /disabled/i.test(e.className)}}))""")
        out, seen = [], set()
        for r in rows:
            label = re.sub(r"^(size|color variant):\s*", "", r["handle"] or "", flags=re.I)
            if ":" in label and attr == "an-la":
                label = label.split(":", 1)[1]
            label = label.strip() or r["text"]
            key = norm_label(label)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(Option(axis, key, label, (r["sku"] or "").upper() or None, available=not r["disabled"],
                              handle=r["handle"]))
        return out

    def choose(self, page, ctx: Context, option: Option) -> None:
        sel, attr = self._tiles(option.axis)
        tile = page.locator(f"{sel.split('[an-la^=')[0]}[{attr}='{option.handle}']").first if option.handle else None
        try:
            tile.wait_for(state="visible", timeout=15000)
        except Exception:
            tile = None
        if tile is None:
            raise OptionNotFound(f"{option.axis} {option.label}: no tile")
        if not option.available:
            raise OptionUnavailable(f"{option.axis} {option.label} is disabled")
        before = page.url
        click_tile(tile)
        for _ in range(30):
            page.wait_for_timeout(500)
            if page.url != before or tile.get_attribute("aria-checked") == "true":
                break
        page.wait_for_timeout(1500)

    def sku_url(self, ctx: Context, sku: str | None) -> str | None:
        return None  # slugs differ per SKU; reach other SKUs by clicking from the context URL

    def read_state(self, page, ctx: Context, product: Product) -> State:
        for y in range(0, 8000, 1000):  # summary and payment cards render when scrolled into view
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(150)
        page.evaluate("window.scrollTo(0, 0)")
        d = page.evaluate(_STATE_JS)
        sel: dict[str, str] = {}
        if d["size"]:
            sel["size"] = d["size"]
        if d["color"]:
            sel["color"] = d["color"]
        for anla, text in d["series"]:
            if ":" in anla:
                axis, val = anla.split(":", 1)
                sel[axis.strip()] = val.strip()
        sku = sku_from_url(page.url)
        if not sku and d["model"] and "/" in d["model"]:
            sku = d["model"].split("/")[-1].strip().upper()
        cards = d["cards"] or []
        one_time = next((c for c in cards if re.search(r"one-time", c, re.I)), "")
        monthly_card = next((c for c in cards if re.search(r"/mo", c)), "")
        header = d["header"] or ""
        base_tok = money_tokens(d["total"] or "", ctx.locale) or money_tokens(one_time, ctx.locale) \
            or money_tokens(header, ctx.locale)
        was = re.search(r"(?:was:?|comp\.? value:?)\s*(\$[\d,]+(?:\.\d{2})?)", header, re.I)
        monthly = money_tokens(monthly_card, ctx.locale, bare_monthly=True)
        return State(sel, None, sku,
                     PriceTexts(base=base_tok[0] if base_tok else None, monthly=monthly[0] if monthly else None,
                                headline=header or None, was=was.group(1) if was else None),
                     available=False if UNAVAILABLE.search(d["avail"] or "") else True)

    def section_boxes(self, page) -> list[tuple[str, Box]]:
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        out: list[tuple[str, Box]] = []
        bar = box_of(page, "[class*=Header_headerContainer]") or page.evaluate(r"""(() => {
            let e = document.querySelector('[class*=PriceInfoText_]');
            while (e && e.getBoundingClientRect().width < 1200) e = e.parentElement;
            if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + scrollX, r.top + scrollY, r.width, r.height]; })()""")
        if bar:
            out.append(("Price bar", tuple(bar)))
        out += [(t, tuple(b)) for t, b in page.evaluate(_SECTIONS_JS)]
        summary = box_of(page, "#product-summary") or box_of(page, "[class*=Summary_container]")
        if summary:
            out.append(("Summary", summary))
        return out

    def section_titles(self, page) -> list[str]:
        return [t for t, _ in page.evaluate(_SECTIONS_JS)]

    def _dialog_box(self, page) -> Box | None:
        b = page.evaluate(r"""(() => {
            const c = [...document.querySelectorAll('[class*=Overlay_dialog], [class*=Overlay_wrapper] [role=dialog], [role=dialog]')]
              .filter(e => !e.closest('[class*=SupportedLanguagesPopup]') && !/SupportedLanguagesPopup/.test(e.className))
              .filter(e => { const r = e.getBoundingClientRect(); return r.width > 200 && r.height > 100 && (e.innerText || '').trim(); });
            const e = c[c.length - 1]; if (!e) return null;
            const r = e.getBoundingClientRect(); return [r.left + scrollX, r.top + scrollY, r.width, r.height]; })()""")
        return tuple(b) if b else None

    def extra_shots(self, page) -> Iterator[tuple[str, Box]]:
        for title, sel in _LAYERS:
            loc = page.locator(sel)
            target = next((loc.nth(i) for i in range(loc.count()) if loc.nth(i).is_visible()), None)
            if target is None:
                continue
            try:
                target.scroll_into_view_if_needed(timeout=5000)
                target.click(timeout=5000)
            except Exception:
                continue
            page.wait_for_timeout(1500)
            box = self._dialog_box(page)
            if box:
                yield title, box
            self.close_extras(page)

    def close_extras(self, page) -> None:
        page.keyboard.press("Escape")
        page.wait_for_timeout(600)

    def specs(self, page):
        return us_specs(page)
