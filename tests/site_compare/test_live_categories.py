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
