import base64
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tools.site_compare import capture
from tools.site_compare.capture import (
    CONSENT_COOKIES, VIEWPORT, _shot, capture_leaf, discover_leaves, full_shots, preset_cookies,
)
from tools.site_compare.model import AxisSpec, Context, Option, PriceTexts, Product, SectionRule, SpecItem, State
from tools.site_compare.pngsize import png_size
from tools.site_compare.sites.base import BaseDriver

FIXTURE = (Path(__file__).parent / "fixtures" / "fake_pdp.html").resolve().as_uri()
WAIT = 300
RULES = [SectionRule("size", "크기", ["size"]), SectionRule("color", "색상", ["colou?r"]),
         SectionRule("pre_purchase", "구매 전 확인", ["pre-purchase"])]


class FakePdpDriver(BaseDriver):
    """Drives tests/site_compare/fixtures/fake_pdp.html."""

    def __init__(self, direct=True, empty=False):
        self.direct, self.empty = direct, empty

    def sku_url(self, ctx, sku):
        return f"{ctx.url.split('?')[0]}?sku={sku}" + ("&broken=1" if "broken" in ctx.url else "") if self.direct else None

    def options(self, page, ctx, axis):
        rows = page.eval_on_selector_all(f"input[name={axis}]", """els => els.map(e => ({id: e.id, v: e.value,
            l: e.dataset.label, sku: e.dataset.modelcode, sold: e.hasAttribute('data-soldout')}))""")
        return [Option(axis, r["v"].lower(), r["l"], r["sku"], available=not r["sold"], handle=r["id"]) for r in rows]

    def choose(self, page, ctx, option):
        page.click(f"#{option.handle}")
        page.wait_for_timeout(150)

    def read_state(self, page, ctx, product):
        if self.empty:
            return State({}, None, None, PriceTexts())
        size = page.eval_on_selector("input[name=size]:checked", "e => e.dataset.label")
        color = page.eval_on_selector("input[name=color]:checked", "e => e.value")
        return State({"size": size, "color": color}, None, page.inner_text("#sku"),
                     PriceTexts(base=page.inner_text("#price") or None), available=not page.inner_text("#avail"))

    def section_boxes(self, page):
        if self.empty:
            return []
        out = []
        heads = page.locator("h3.t")
        for i in range(heads.count()):
            b = heads.nth(i).locator("xpath=..").bounding_box()
            out.append((heads.nth(i).inner_text(), (b["x"], b["y"], b["width"], b["height"])))
        return out

    def specs(self, page):
        if self.empty:
            return [], []
        items = page.eval_on_selector_all("#specs dt", "els => els.map(e => [e.dataset.group, e.innerText, e.nextElementSibling.innerText])")
        b = page.locator("#specs").bounding_box()
        return [SpecItem(*i) for i in items], [("Specs", (b["x"], b["y"], b["width"], b["height"]))]


def _ctx(url=FIXTURE, **kw):
    return Context("c0", "C0", "pd", url, "en-GB", "GBP", ref_sku="P65B", **kw)


def _product(axes):
    return Product("fake", "Fake", [_ctx()], sections=RULES, mode="discover", axes=axes)


@pytest.fixture(scope="module")
def bctx():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        c = b.new_context(viewport=VIEWPORT)
        yield c
        c.close()
        b.close()


def _leaves(bctx, axes, driver=None, ctx=None):
    product = _product(axes)
    leaves, warnings = discover_leaves(bctx, driver or FakePdpDriver(), product, ctx or product.contexts[0], WAIT)
    return product, leaves, warnings


def _capture(bctx, tmp_path, product, leaf, driver=None, ctx=None):
    (tmp_path / "shots").mkdir(exist_ok=True)
    return capture_leaf(bctx, driver or FakePdpDriver(), product, ctx or product.contexts[0], leaf, tmp_path, WAIT,
                        with_extras=True)


def test_discover_single_axis_leaves(bctx):
    _, leaves, _ = _leaves(bctx, [AxisSpec("size", iterate=True)])
    assert [l.target_sku for l in leaves] == ["P55B", "P65B", "P77B"]
    assert [l.id for l in leaves] == ["c0__55", "c0__65", "c0__77"]
    assert [l.is_ref for l in leaves] == [False, True, False]
    assert leaves[0].key == '55"' and leaves[0].want == {"size": '55"'}


def test_discover_two_axes_with_fixed(bctx):
    _, leaves, _ = _leaves(bctx, [AxisSpec("size", iterate=True), AxisSpec("color", fixed="White")])
    assert [l.target_sku for l in leaves] == ["P55W", "P65W", "P77W"]
    assert all(len(l.path) == 2 for l in leaves)


def test_discover_fixed_value_missing_warns(bctx):
    _, leaves, warnings = _leaves(bctx, [AxisSpec("color", fixed="Pink")])
    assert leaves == [] and any("Pink" in w for w in warnings)


def test_discover_no_axes_uses_ref(bctx):
    _, leaves, _ = _leaves(bctx, [])
    assert len(leaves) == 1 and leaves[0].id == "c0__ref" and leaves[0].target_sku == "P65B" and leaves[0].is_ref


def test_capture_leaf_ok_with_specs(bctx, tmp_path):
    product, leaves, _ = _leaves(bctx, [AxisSpec("size", iterate=True)])
    r = _capture(bctx, tmp_path, product, leaves[0])
    assert r.status == "ok", r.warnings
    assert r.got.sku == "P55B" and r.base.value == 1000.0 and r.price_match is True
    assert [s.section_id for s in r.sections] == ["size", "color", "pre_purchase"]
    assert len(r.specs) == 4 and r.specs[0] == SpecItem("Display", "Screen Size", '55"')
    assert len(r.spec_shots) == 1 and (tmp_path / r.spec_shots[0].path).exists()
    assert r.key == '55"' and r.is_ref is False


def test_capture_leaf_by_clicking_when_no_direct_url(bctx, tmp_path):
    driver = FakePdpDriver(direct=False)
    product, leaves, _ = _leaves(bctx, [AxisSpec("size", iterate=True)], driver)
    r = _capture(bctx, tmp_path, product, leaves[0], driver)
    assert r.status == "ok" and r.got.sku == "P55B"


def test_discover_unavailable_leaf_recorded(bctx, tmp_path):
    product, leaves, _ = _leaves(bctx, [AxisSpec("size", iterate=True)])
    r = _capture(bctx, tmp_path, product, leaves[2])  # 77" is sold out
    assert r.status == "unavailable"
    assert any(w.startswith("not available") for w in r.warnings)
    assert "price not rendered" not in r.warnings


def test_leaf_sku_mismatch_flagged(bctx, tmp_path):
    ctx = _ctx(FIXTURE + "?broken=1")
    product = Product("fake", "Fake", [ctx], sections=RULES, mode="discover", axes=[AxisSpec("size", iterate=True)])
    leaves, _ = discover_leaves(bctx, FakePdpDriver(), product, ctx, WAIT)
    r = _capture(bctx, tmp_path, product, leaves[1], ctx=ctx)  # 65" leaf, page shows 55" SKU
    assert r.status == "mismatch"
    assert any(w.startswith("sku mismatch") for w in r.warnings)


def test_nothing_captured_is_error(bctx, tmp_path):
    product, leaves, _ = _leaves(bctx, [])
    r = _capture(bctx, tmp_path, product, leaves[0], FakePdpDriver(empty=True))
    assert r.status == "error" and "nothing captured" in r.warnings


def test_full_shots_are_sliced(bctx, tmp_path):
    page = bctx.new_page()
    page.goto(FIXTURE)
    page.wait_for_timeout(WAIT)
    (tmp_path / "shots").mkdir()
    paths = full_shots(page, tmp_path, "x")
    page.close()
    assert len(paths) == 5  # 20,000px page in ≤4,000px slices (tall clips render shifted in Chrome)
    assert all(png_size(tmp_path / p)[1] <= 4000 for p in paths)


def test_clip_clamped_to_page_width(bctx, tmp_path):
    page = bctx.new_page()
    page.goto(FIXTURE)
    (tmp_path / "shots").mkdir()
    warnings = []
    assert _shot(page, tmp_path, "off", "Off", None, 1, (5000, 0, 300, 300), warnings) is None
    s = _shot(page, tmp_path, "edge", "Edge", None, 2, (1300, 10, 400, 100), warnings)
    page.close()
    assert s is not None and png_size(tmp_path / s.path) == (s.width, s.height) and s.width <= 140
    assert warnings and "outside" in warnings[0]


def test_preset_cookies(bctx):
    c = bctx.browser.new_context()
    preset_cookies(c, Context("q", "Q", "pd", "https://www.samsung.com/ca/x/", "en-CA", "CAD", region="CA-QC",
                              cookies={"eddzipcode": "10001"}))
    got = {k["name"]: k["value"] for k in c.cookies()}
    c.close()
    assert {k: got[k] for k in CONSENT_COOKIES} == CONSENT_COOKIES
    assert got["country_region"] == "CA-QC" and got["eddzipcode"] == "10001"


def test_png_size(tmp_path):
    f = tmp_path / "a.png"
    f.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="))
    assert png_size(f) == (1, 1)


class FlakyPriceDriver(FakePdpDriver):
    """Price stays empty until the page has been reloaded once (simulates a throttled price API)."""

    def read_state(self, page, ctx, product):
        st = super().read_state(page, ctx, product)
        if not page.evaluate("performance.getEntriesByType('navigation')[0].type === 'reload'"):
            st.prices.base = None
        return st


def test_price_missing_triggers_one_reload(bctx, tmp_path):
    product, leaves, _ = _leaves(bctx, [AxisSpec("size", iterate=True)])
    r = _capture(bctx, tmp_path, product, leaves[1], FlakyPriceDriver())
    assert r.status == "ok" and r.base.value == 2000.0, r.warnings
    assert "price not rendered" not in r.warnings and any("reloaded" in w for w in r.warnings)


class TallSpecDriver(FakePdpDriver):
    def specs(self, page):
        items, _ = super().specs(page)
        return items, [("Specs", (0, 100, 1440, 7000))]


def test_tall_spec_box_is_split(bctx, tmp_path):
    product, leaves, _ = _leaves(bctx, [])
    r = _capture(bctx, tmp_path, product, leaves[0], TallSpecDriver())
    assert len(r.spec_shots) == 3 and all(s.height <= 3000 for s in r.spec_shots)
    assert [s.title for s in r.spec_shots] == ["Specs (1/3)", "Specs (2/3)", "Specs (3/3)"]


class CountingDriver(FakePdpDriver):
    def __init__(self):
        super().__init__(direct=False)
        self.clicks = 0

    def choose(self, page, ctx, option):
        self.clicks += 1
        super().choose(page, ctx, option)


def test_already_selected_options_are_not_clicked(bctx, tmp_path):
    driver = CountingDriver()
    product, leaves, _ = _leaves(bctx, [AxisSpec("size", iterate=True)], driver)
    driver.clicks = 0
    ref = next(l for l in leaves if l.is_ref)
    r = _capture(bctx, tmp_path, product, ref, driver)
    assert r.status == "ok" and driver.clicks == 0


class LateOptionsDriver(FakePdpDriver):
    """Options are missing until the page has been reloaded (late hydration)."""

    def options(self, page, ctx, axis):
        if not page.evaluate("performance.getEntriesByType('navigation')[0].type === 'reload'"):
            return []
        return super().options(page, ctx, axis)


def test_discover_reloads_once_when_options_missing(bctx):
    _, leaves, warnings = _leaves(bctx, [AxisSpec("size", iterate=True)], LateOptionsDriver())
    assert len(leaves) == 3, warnings


class DroppedClickDriver(FakePdpDriver):
    """The first click is swallowed (e.g. an overlay or a slow hydration), later clicks work."""

    def __init__(self):
        super().__init__(direct=False)
        self.dropped = False

    def choose(self, page, ctx, option):
        if not self.dropped:
            self.dropped = True
            return
        super().choose(page, ctx, option)


def test_click_path_retried_once_on_mismatch(bctx, tmp_path):
    driver = DroppedClickDriver()
    product, leaves, _ = _leaves(bctx, [AxisSpec("size", iterate=True)], driver)
    driver.dropped = False
    r = _capture(bctx, tmp_path, product, leaves[0], driver)  # 55": first click lost, page stays on 65"
    assert r.status == "ok" and r.got.sku == "P55B", r.warnings
    assert any(w.startswith("retried:") for w in r.warnings)
