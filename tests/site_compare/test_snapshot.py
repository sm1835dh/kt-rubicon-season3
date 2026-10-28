import gzip
import re
import json

import pytest
from playwright.sync_api import sync_playwright

from tools.site_compare.capture import VIEWPORT
from tools.site_compare.model import AxisSpec, Context, Product
from tools.site_compare.snapshot import expected_for, load_fixture, save_snapshot

from .test_discover import FIXTURE, RULES, FakePdpDriver


class SnapFakeDriver(FakePdpDriver):
    SNAPSHOT_KEEP = [".col", "#specs", "script[type='application/ld+json']"]

    def section_titles(self, page):
        return [t for t, _ in self.section_boxes(page)]


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_context(viewport=VIEWPORT).new_page()
        yield pg
        b.close()


def _setup():
    ctx = Context("c0", "C0", "pd", FIXTURE, "en-GB", "GBP", ref_sku="P65B")
    product = Product("fake", "Fake", [ctx], sections=RULES, mode="discover",
                      axes=[AxisSpec("size", iterate=True), AxisSpec("color", iterate=True)])
    return product, ctx


def test_snapshot_roundtrip_reproduces_driver_output(page, tmp_path):
    product, ctx = _setup()
    driver = SnapFakeDriver()
    page.goto(FIXTURE)
    page.wait_for_timeout(300)
    live = expected_for(page, driver, product, ctx)
    path = save_snapshot(page, driver, product, ctx, tmp_path, "fake")
    assert path.name == "fake__c0.html.gz" and path.with_name("fake__c0.expected.json").exists()
    expected = load_fixture(page, path)
    assert expected == json.loads(json.dumps(live))
    assert expected_for(page, driver, product, ctx) == expected  # same driver output from the saved DOM
    assert [o[0] for o in expected["options"]["size"]] == ["55", "65", "77"]
    assert expected["state"]["sku"] == "P65B" and expected["spec_count"] == 4


def test_snapshot_keeps_only_listed_parts_and_marks_hidden(page, tmp_path):
    product, ctx = _setup()
    page.goto(FIXTURE)
    page.wait_for_timeout(300)
    page.evaluate("document.querySelector('#avail').style.display = 'none'")
    path = save_snapshot(page, SnapFakeDriver(), product, ctx, tmp_path, "fake")
    html = gzip.decompress(path.read_bytes()).decode()
    assert 'class="tall"' not in html and "<style" not in html
    tag = re.search(r'<div[^>]*id="avail"[^>]*>', html).group(0)
    assert "display: none" in tag or "display:none" in tag
    assert 'application/ld+json' in html and "setTimeout" not in html
