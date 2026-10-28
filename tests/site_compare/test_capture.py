from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from tools.site_compare import capture
from tools.site_compare.capture import capture_combo, run_capture
from tools.site_compare.model import Combo, Context, Money, PriceTexts, Product, RunData, SectionRule, State
from tools.site_compare.sites.base import OptionNotFound, OptionUnavailable

FIXTURE = (Path(__file__).parent / "fixtures" / "fake_buy.html").resolve().as_uri()
WAIT = 300
RULES = [
    SectionRule("storage", "용량", ["^storage$"]),
    SectionRule("color", "색상", ["^colou?r$"]),
    SectionRule("trade_in", "트레이드인", ["trade-?in"]),
]


class FakeDriver:
    """Drives tests/site_compare/fixtures/fake_buy.html."""

    def prepare(self, page, ctx):
        return []

    def select(self, page, axis, value, product):
        if axis != "storage":
            return
        radio = page.locator(f"input[name=mem][value='{value}']")
        if radio.get_attribute("data-unavailable") is not None:
            raise OptionUnavailable(f"storage {value}")
        radio.click()

    def read_state(self, page, ctx, product):
        storage = page.locator("input[name=mem]:checked").get_attribute("value")
        return State(storage, "Graphite", None, page.inner_text("#region"), page.inner_text("#sku"),
                     PriceTexts(base=page.inner_text("#price") or None))

    def section_boxes(self, page):
        out = []
        heads = page.locator("h2.t")
        for i in range(heads.count()):
            sec = heads.nth(i).locator("xpath=..")
            b = sec.bounding_box()
            out.append((heads.nth(i).inner_text(), (b["x"], b["y"], b["width"], b["height"])))
        return out

    def extra_shots(self, page):
        return iter(())

    def close_extras(self, page):
        pass


def _product(url=FIXTURE, region=None, n_contexts=1):
    ctxs = [Context(f"c{i}", f"C{i}", "hubble", url, "en-GB", "GBP", region) for i in range(n_contexts)]
    return Product("fake", "Fake", ctxs, ["256GB", "512GB", "1TB"], {"Graphite": "ZK"}, "Graphite", [], RULES)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        yield b
        b.close()


def _run(browser, tmp_path, want, query="", region=None, driver=None):
    product = _product(region=region)
    ctx = product.contexts[0]
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(FIXTURE + query)
    page.wait_for_timeout(WAIT)
    combo = Combo("c0__x", ctx.id, "main", want)
    (tmp_path / "shots").mkdir(exist_ok=True)
    r = capture_combo(page, driver or FakeDriver(), product, ctx, combo, tmp_path, WAIT, with_extras=True)
    page.close()
    return r


def test_capture_ok_records_prices_sections_and_jsonld(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "256GB", "color": "Graphite"})
    assert r.status == "ok", r.warnings
    assert r.got.storage == "256GB"
    assert r.base == Money(1899.0, "GBP")
    assert r.jsonld.price == 1899.0 and r.price_match is True
    assert [s.section_id for s in r.sections] == ["storage", "color", "trade_in"]
    assert (tmp_path / r.full_shot).exists() and all((tmp_path / s.path).exists() for s in r.sections)
    assert any(t.text == "£1,899.00" for s in r.sections for t in s.texts)


def test_text_boxes_join_multiline_labels(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "256GB", "color": "Graphite"})
    texts = [t.text for s in r.sections for t in s.texts]
    assert "Verizon Financing (Pay Monthly)" in texts


def test_capture_selects_requested_storage(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "512GB", "color": "Graphite"})
    assert r.status == "ok" and r.got.sku == "FAKE512" and r.base == Money(2069.0, "GBP")


def test_unavailable_option_recorded(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "1TB", "color": "Graphite"})
    assert r.status == "unavailable"
    assert r.full_shot is not None and (tmp_path / r.full_shot).exists()


def test_price_retry_then_warning(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "256GB", "color": "Graphite"}, query="?noprice=1")
    assert "price not rendered" in r.warnings
    assert r.base is None and r.price_match is None


def test_selection_mismatch_flagged(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "512GB", "color": "Graphite"}, query="?stuck=1")
    assert r.status == "mismatch"
    assert any(w.startswith("selection mismatch: storage") for w in r.warnings)


def test_region_mismatch_warning(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "256GB", "color": "Graphite"}, region="CA-QC")
    assert any(w.startswith("region mismatch") for w in r.warnings)
    assert r.status == "mismatch"  # wrong-province prices must not count as ok


def test_region_alias_accepted(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "256GB", "color": "Graphite"}, query="?region=Qu%C3%A9bec",
             region="CA-QC")
    assert not any(w.startswith("region mismatch") for w in r.warnings)


class ColorMessageDriver(FakeDriver):
    """Site shows an 'unavailable' message for colour, yet the final state is the requested one."""

    def select(self, page, axis, value, product):
        if axis == "color":
            raise OptionUnavailable("colour message shown")
        super().select(page, axis, value, product)


class MissingControlDriver(FakeDriver):
    def select(self, page, axis, value, product):
        raise OptionNotFound(f"no control for {axis}")


def test_unavailable_needs_final_state_mismatch(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "512GB", "color": "Graphite"}, driver=ColorMessageDriver())
    assert r.status == "ok"
    assert r.got.storage == "512GB"  # later axes are still tried after an unavailable step


def test_missing_control_is_error_not_unavailable(browser, tmp_path):
    r = _run(browser, tmp_path, {"storage": "512GB", "color": "Graphite"}, driver=MissingControlDriver())
    assert r.status == "error"
    assert any("no control for storage" in w for w in r.warnings)
