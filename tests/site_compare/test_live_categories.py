"""Live tests for the category products against real samsung.com.

Run: .venv/bin/pytest -m live tests/site_compare/test_live_categories.py -k <driver>
Prices and stock change; these tests assert structure (SKU, sections, specs), not amounts.
"""
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tools.site_compare.capture import VIEWPORT, capture_leaf, capture_specs_page, discover_leaves, preset_cookies
from tools.site_compare.config import load_product
from tools.site_compare.prices import money_tokens
from tools.site_compare.sites import get_driver

WAIT = 5000
PRODUCTS = Path("tools/site_compare/products")


def _setup(product_id, ctx_id):
    product = load_product(PRODUCTS / f"{product_id}.yaml")
    ctx = next(c for c in product.contexts if c.id == ctx_id)
    return product, ctx, get_driver(ctx.driver)


def _with_context(fn):
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        try:
            return fn(b)
        finally:
            b.close()


def _leaves(product_id, ctx_id):
    product, ctx, driver = _setup(product_id, ctx_id)

    def run(b):
        bctx = b.new_context(viewport=VIEWPORT)
        preset_cookies(bctx, ctx)
        return discover_leaves(bctx, driver, product, ctx, WAIT)
    return _with_context(run)


def capture_ref(tmp_path, product_id, ctx_id):
    product, ctx, driver = _setup(product_id, ctx_id)
    (tmp_path / "shots").mkdir(exist_ok=True)

    def run(b):
        bctx = b.new_context(viewport=VIEWPORT)
        preset_cookies(bctx, ctx)
        leaves, warnings = discover_leaves(bctx, driver, product, ctx, WAIT)
        ref = next(l for l in leaves if l.is_ref)
        r = capture_leaf(bctx, driver, product, ctx, ref, tmp_path, WAIT, with_extras=True)
        if ctx.spec_url:
            capture_specs_page(bctx, ctx, r, tmp_path, WAIT)
        r.warnings[:0] = warnings
        return r
    r = _with_context(run)
    print(r.combo_id, r.status, r.got, r.warnings, [(s.title, s.section_id) for s in r.sections],
          [s.title for s in r.extras], len(r.specs), r.specs[:3])
    return r


def _assert_ref(r, sku, min_specs=30, min_buy_sections=3):
    assert r.status == "ok", r.warnings
    assert (r.got.sku or "").upper() == sku
    assert r.got.prices.base and money_tokens(r.got.prices.base, "fr-CA" if "," in r.got.prices.base[-4:] else "en-GB") \
        or r.base is not None
    ids = [s.section_id for s in r.sections]
    assert "price_bar" in ids and "summary" in ids, ids
    assert len([i for i in ids if i not in ("price_bar", "summary")]) >= min_buy_sections, ids
    assert len(r.specs) >= min_specs and r.spec_shots


# --- pd: UK / CA / CA-FR product pages (TV, washer, fridge) -------------------------------------------------

@pytest.mark.live
@pytest.mark.parametrize("product_id,ctx_id,sku", [
    ("tv_s95h", "uk", "QE77S95HFTXXU"), ("tv_s95h", "ca-en-qc", "QN77S95HAFXZC"),
    ("washer_flagship", "uk", "WF90H11C4WT1"), ("washer_flagship", "ca-fr-on", "WF90F53ADSA5"),
    ("fridge_t_style", "uk", "RF65DG960ESREU"),
])
def test_pd_live_ref(tmp_path, product_id, ctx_id, sku):
    r = capture_ref(tmp_path, product_id, ctx_id)
    _assert_ref(r, sku)
    if ctx_id.startswith("ca"):
        assert r.got.region in ("Ontario", "Quebec", "Québec")


@pytest.mark.live
def test_pd_live_tv_sizes_uk():
    leaves, _ = _leaves("tv_s95h", "uk")
    assert {l.path[0].value for l in leaves} == {"48", "55", "65", "77"}, [l.path[0].label for l in leaves]


@pytest.mark.live
def test_pd_live_tv_sizes_ca():
    leaves, _ = _leaves("tv_s95h", "ca-fr-qc")
    assert {l.path[0].value for l in leaves} == {"55", "65", "77", "83"}, [l.path[0].label for l in leaves]


@pytest.mark.live
def test_pd_live_washer_uk_f_spec_only(tmp_path):
    r = capture_ref(tmp_path, "washer_flagship", "uk-f")
    assert r.status == "unavailable", r.warnings
    assert len(r.specs) >= 30


# --- us_pdp: US product pages (TV, washer, fridge) -----------------------------------------------------------

@pytest.mark.live
@pytest.mark.parametrize("product_id,sku", [("tv_s95h", "QN77S95HAFXZA"), ("washer_flagship", "WF90F53ADSA5"),
                                            ("fridge_t_style", "RF23DB9600QLAA")])
def test_us_pdp_live_ref(tmp_path, product_id, sku):
    r = capture_ref(tmp_path, product_id, "us")
    _assert_ref(r, sku, min_specs=50)
    p = r.got.prices
    assert p.was and p.monthly and p.monthly.startswith("$"), p
    assert r.price_match is True, (r.base, r.jsonld)
    assert not any("highlights" in s.title.lower() for s in r.sections)
    texts = " ".join(t.text for s in r.sections for t in s.texts)
    assert "not available in your area" not in texts  # eddzipcode=10001 applied


@pytest.mark.live
def test_us_pdp_live_fridge_depth_options():
    leaves, _ = _leaves("fridge_t_style", "us")
    assert {l.path[0].value for l in leaves} == {"counterdepth", "fulldepth"}, [l.path[0].label for l in leaves]


@pytest.mark.live
def test_us_pdp_live_tv_sizes():
    leaves, _ = _leaves("tv_s95h", "us")
    assert {l.path[0].value for l in leaves} == {"55", "65", "77", "83"}, [l.path[0].label for l in leaves]


# --- watchbc: UK / CA / CA-FR watch buy pages; hubble: laptop series buy pages ------------------------------

@pytest.mark.live
@pytest.mark.parametrize("ctx_id,sku", [("uk", "SM-L340NZKAEUB"), ("ca-fr-qc", "SM-L340NZKAXAC")])
def test_watchbc_live_ref(tmp_path, ctx_id, sku):
    r = capture_ref(tmp_path, "watch9", ctx_id)
    _assert_ref(r, sku, min_specs=20, min_buy_sections=6)
    assert "case_size" in {s.section_id for s in r.sections}
    assert r.got.selection.get("connectivity", "").lower() == "bluetooth"


@pytest.mark.live
def test_watchbc_live_leaves_uk():
    leaves, warnings = _leaves("watch9", "uk")
    assert len(leaves) == 4, (warnings, [l.id for l in leaves])
    assert {(l.path[0].value, l.path[1].value) for l in leaves} == {
        ("40mm", "bluetooth"), ("40mm", "lte"), ("44mm", "bluetooth"), ("44mm", "lte")}
    assert all(l.target_sku and "ZK" in l.target_sku for l in leaves), [l.target_sku for l in leaves]


@pytest.mark.live
@pytest.mark.parametrize("ctx_id,sku", [("uk", "NP960XJG-KGAUK"), ("ca-fr-on", "NP960XJG-KG1CA")])
def test_hubble_laptop_live_ref(tmp_path, ctx_id, sku):
    r = capture_ref(tmp_path, "laptop_book6_pro", ctx_id)
    _assert_ref(r, sku, min_specs=20, min_buy_sections=6)
    assert r.got.selection.get("color") and r.got.selection.get("storage")
    if ctx_id.startswith("ca"):
        assert r.got.prices.was, r.got.prices


# --- us: US buy pages (watch, laptop) — the same driver as Fold8 in click mode ------------------------------

@pytest.mark.live
def test_us_watch_live_ref(tmp_path):
    r = capture_ref(tmp_path, "watch9", "us")
    _assert_ref(r, "SM-L340NZKAXAA", min_specs=20, min_buy_sections=6)
    assert r.got.selection.get("connectivity", "").lower() == "bluetooth", r.got.selection  # no "Wifi" mix-up
    assert r.got.selection.get("color", "").lower() == "graphite", r.got.selection
    assert r.got.prices.monthly and r.got.prices.monthly.startswith("$"), r.got.prices


@pytest.mark.live
def test_us_watch_live_leaves():
    leaves, warnings = _leaves("watch9", "us")
    assert {(l.path[0].value, l.path[1].value) for l in leaves} == {
        ("40mm", "bluetooth"), ("40mm", "lte"), ("44mm", "bluetooth"), ("44mm", "lte")}, (warnings, [l.id for l in leaves])


@pytest.mark.live
def test_us_laptop_live_ref(tmp_path):
    r = capture_ref(tmp_path, "laptop_book6_pro", "us")
    _assert_ref(r, "NP960XJG-KG1US", min_specs=20, min_buy_sections=6)
    assert r.got.prices.was and r.price_match is True, (r.got.prices, r.jsonld)
