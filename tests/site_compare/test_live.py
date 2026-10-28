"""Live tests against real samsung.com. Run with: .venv/bin/pytest -m live tests/site_compare/test_live.py"""
import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tools.site_compare.capture import VIEWPORT, capture_combo, norm_region, preset_cookies
from tools.site_compare.config import load_product
from tools.site_compare.model import Combo
from tools.site_compare.sites import get_driver

PRODUCT = load_product(Path("tools/site_compare/products/fold8_ultra.yaml"))
WAIT = 5000


def _capture(tmp_path, ctx_id, want):
    ctx = next(c for c in PRODUCT.contexts if c.id == ctx_id)
    driver = get_driver(ctx.driver)
    (tmp_path / "shots").mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        bctx = browser.new_context(viewport=VIEWPORT)
        preset_cookies(bctx, ctx)  # same as capture_context
        page = bctx.new_page()
        page.goto(ctx.url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(WAIT)
        prep = driver.prepare(page, ctx)
        r = capture_combo(page, driver, PRODUCT, ctx, Combo("live", ctx.id, "main", want), tmp_path, WAIT, True)
        browser.close()
    r.warnings[:0] = prep
    return r


@pytest.mark.live
@pytest.mark.parametrize("ctx_id,storage", [("uk", "512GB"), ("ca-en-on", "256GB"), ("ca-fr-qc", "1TB")])
def test_hubble_live_combo(tmp_path, ctx_id, storage):
    r = _capture(tmp_path, ctx_id, {"storage": storage, "color": "Graphite"})
    print(r.status, r.got, r.warnings, [(s.title, s.section_id) for s in r.sections], [s.title for s in r.extras])
    assert r.status == "ok", r.warnings
    assert r.got.selection["storage"].replace(" ", "") == storage and r.got.selection["color"] == "Graphite"
    assert r.base is not None and r.price_match is True
    assert {"storage", "color", "trade_in", "care", "price_bar", "summary"} <= {s.section_id for s in r.sections}
    assert [s.title for s in r.extras] == ["Offer banner"]
    bar = next(s for s in r.sections if s.section_id == "price_bar")
    assert any(re.search(r"\d", t.text) and ("$" in t.text or "£" in t.text) for t in bar.texts), [t.text for t in bar.texts]
    device = next(s for s in r.sections if s.section_id == "device")
    feature = {"uk": "Ultra Sleek", "ca-en-on": "Ultra Sleek", "ca-fr-qc": "Ultra épuré"}[ctx_id]  # feature icons sit above the heading
    assert any(feature in t.text for t in device.texts), [t.text for t in device.texts]
    if ctx_id == "ca-fr-qc":
        assert norm_region(r.got.region) == "CA-QC"
        assert not any(w.startswith("region mismatch") for w in r.warnings)


@pytest.mark.live
@pytest.mark.parametrize("carrier,suffix", [("Unlocked", "XAA"), ("Verizon", "VZW")])
def test_us_live_combo(tmp_path, carrier, suffix):
    # 2026-10-29: the site stopped offering carrier tiles for 512GB, so the carrier check uses 256GB
    r = _capture(tmp_path, "us", {"storage": "256GB", "color": "Graphite", "carrier": carrier})
    print(r.status, r.got, r.warnings, [(s.title, s.section_id) for s in r.sections], [s.title for s in r.extras])
    if carrier != "Unlocked" and r.status == "unavailable":
        # 2026-10-29: the site shows only the Unlocked tile for Graphite; "unavailable" needs the site's evidence
        assert any("not offered" in w or "unavailable for" in w for w in r.warnings), r.warnings
        return
    assert r.status == "ok", r.warnings
    assert r.got.sku == f"SM-F976UZKA{suffix}" and r.got.selection["carrier"] == carrier
    assert r.base is not None
    if carrier == "Unlocked":
        assert r.price_match is True
    ids = {s.section_id for s in r.sections}
    assert {"storage", "color", "connectivity", "trade_in", "care", "purchase_option", "price_bar", "summary"} <= ids
    if carrier == "Verizon":
        po = next(s for s in r.sections if s.section_id == "purchase_option")
        assert any("Verizon Financing" in t.text for t in po.texts)
    assert [s.title for s in r.extras] == ["Carrier deals", "Care+ details"]


@pytest.mark.live
def test_us_live_unavailable(tmp_path):
    r = _capture(tmp_path, "us", {"storage": "256GB", "color": "Green Shadow", "carrier": "Verizon"})
    assert r.status == "unavailable", (r.status, r.warnings)
