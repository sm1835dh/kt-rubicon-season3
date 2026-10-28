"""Offline driver tests on trimmed DOM fixtures of real pages (saved by `python -m tools.site_compare snapshot`).

Every fixture's driver output must equal the golden values saved with it; a failing case names the template,
product and context whose parsing changed. Hand-written checks below pin facts from the 2026-10-28 research.
"""
import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tools.site_compare.capture import VIEWPORT
from tools.site_compare.config import load_product
from tools.site_compare.sites import get_driver
from tools.site_compare.snapshot import FIXTURES, diff_expected, expected_for, load_fixture

PRODUCTS = Path(__file__).resolve().parents[2] / "tools" / "site_compare" / "products"
TEMPLATES = ("pd", "us_pdp", "watchbc", "hubble", "us")
CASES = sorted(p for t in TEMPLATES for p in (FIXTURES / t).glob("*.expected.json"))


def _case(path: Path):
    template = path.parent.name
    stem = path.name.removesuffix(".expected.json")
    name, ctx_id = stem.split("__")
    product = load_product(PRODUCTS / f"{name.removesuffix('-specpage')}.yaml")
    ctx = next(c for c in product.contexts if c.id == ctx_id)
    return template, product, ctx, path.with_name(f"{stem}.html.gz")


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_context(viewport=VIEWPORT, java_script_enabled=True).new_page()
        yield pg
        b.close()


def _run(page, path):
    template, product, ctx, html = _case(path)
    expected = load_fixture(page, html)
    return expected, expected_for(page, get_driver(template), product, ctx)


@pytest.mark.parametrize("path", CASES, ids=lambda p: f"{p.parent.name}/{p.name.removesuffix('.expected.json')}")
def test_driver_reproduces_fixture(page, path):
    expected, got = _run(page, path)
    assert diff_expected(expected, got) == []


def _expected(template, stem):
    return json.loads((FIXTURES / template / f"{stem}.expected.json").read_text(encoding="utf-8"))


def _values(exp, axis):
    return {o[0] for o in exp["options"][axis]}


def test_pd_tv_sizes_by_country():
    assert _values(_expected("pd", "tv_s95h__uk"), "size") == {"48", "55", "65", "77"}
    assert _values(_expected("pd", "tv_s95h__ca-fr-qc"), "size") == {"55", "65", "77", "83"}


def test_pd_tv_ref_skus_and_prices():
    uk, qc = _expected("pd", "tv_s95h__uk"), _expected("pd", "tv_s95h__ca-en-qc")
    assert uk["state"]["sku"] == "QE77S95HFTXXU" and uk["state"]["prices"]["was"].startswith("£")
    assert qc["state"]["sku"] == "QN77S95HAFXZC" and qc["state"]["prices"]["monthly"] is None  # Quebec: no financing
    assert _expected("pd", "tv_s95h__ca-en-on")["state"]["prices"]["monthly"]  # Ontario EN shows monthly


def test_pd_washer_uk_f_is_discontinued_with_specs():
    f = _expected("pd", "washer_flagship__uk-f")
    assert f["state"]["available"] is False and f["state"]["prices"]["base"] is None
    assert f["spec_count"] >= 30


def test_pd_washer_and_fridge_colours():
    assert _values(_expected("pd", "washer_flagship__uk"), "color") == {"darksteel", "neatwhite"}
    assert _values(_expected("pd", "fridge_t_style__uk"), "color") == {"silver", "black"}
    assert _expected("pd", "washer_flagship__ca-fr-on")["state"]["prices"]["base"].endswith("$")  # fr-CA format


def test_pd_sections_map_to_rules():
    from tools.site_compare.config import map_section
    product = load_product(PRODUCTS / "washer_flagship.yaml")
    for ctx in ("uk", "ca-en-on", "ca-fr-qc"):
        ids = [map_section(t, product.sections) for t in _expected("pd", f"washer_flagship__{ctx}")["sections"]]
        assert "color" in ids and "pre_purchase" in ids, ids


def test_us_pdp_options_and_prices():
    tv, washer, fridge = (_expected("us_pdp", f"{p}__us") for p in ("tv_s95h", "washer_flagship", "fridge_t_style"))
    assert _values(tv, "size") == {"55", "65", "77", "83"}
    assert _values(washer, "color") == {"darksteel", "ivory"}
    assert _values(fridge, "depth") == {"counterdepth", "fulldepth"}
    for e in (tv, washer, fridge):
        p = e["state"]["prices"]
        assert p["base"].startswith("$") and p["was"].startswith("$") and p["monthly"].startswith("$")
    assert tv["state"]["sku"] == "QN77S95HAFXZA" and fridge["state"]["sku"] == "RF23DB9600QLAA"


def test_us_pdp_specs_have_groups_and_clean_labels():
    tv = _expected("us_pdp", "tv_s95h__us")
    assert tv["spec_count"] >= 100
    assert all(g and "?" not in label for g, label, _ in tv["spec_sample"])  # no tooltip text glued to labels


def test_watchbc_options_use_sellable_skus():
    uk = _expected("watchbc", "watch9__uk")
    assert _values(uk, "size") == {"40mm", "44mm"} and _values(uk, "connectivity") == {"bluetooth", "lte"}
    skus = {o[2] for opts in uk["options"].values() for o in opts}
    assert all(s.endswith("EUB") and s[10] != "D" for s in skus), skus  # preset codes, not case-only "…ZKDWEU"
    assert uk["state"]["sku"] == "SM-L340NZKAEUB" and uk["state"]["prices"]["base"] == "£349.00"


def test_watchbc_ca_fr_case_size_title():
    assert "Taille de la valise" in _expected("watchbc", "watch9__ca-fr-qc")["sections"]  # mistranslation kept as-is


def test_hubble_laptop_state():
    uk, fr = _expected("hubble", "laptop_book6_pro__uk"), _expected("hubble", "laptop_book6_pro__ca-fr-on")
    assert uk["state"]["sku"] == "NP960XJG-KGAUK" and uk["state"]["selection"]["color"] == "Grey"
    assert fr["state"]["sku"] == "NP960XJG-KG1CA" and fr["state"]["selection"]["color"] == "Gris"
    assert fr["state"]["prices"]["was"] and fr["state"]["prices"]["monthly"]  # Ontario financing


def test_spec_pages_extract_specs():
    for stem in ("watch9-specpage__uk", "watch9-specpage__ca-fr-qc", "laptop_book6_pro-specpage__uk",
                 "laptop_book6_pro-specpage__ca-en-on"):
        e = _expected("pd", stem)
        assert e["spec_count"] >= 20 and all(len(row) == 3 and row[1] for row in e["spec_sample"]), stem


def test_us_buy_pages_state():
    watch, laptop, fold8 = (_expected("us", f"{p}__us") for p in ("watch9", "laptop_book6_pro", "fold8_ultra"))
    assert watch["state"]["sku"] == "SM-L340NZKAXAA" and watch["state"]["selection"]["connectivity"] == "bluetooth"
    assert watch["state"]["prices"]["monthly"] == "$15.83"  # header shows "15.83/mo" without "$"
    assert _values(watch, "size") == {"40mm", "44mm"} and "casesizingguide" not in _values(watch, "size")
    assert laptop["state"]["sku"] == "NP960XJG-KG1US" and laptop["state"]["prices"]["was"]
    assert fold8["state"]["selection"]["carrier"] == "Unlocked"  # Fold8 keeps the summary-line reading
