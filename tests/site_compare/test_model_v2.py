from pathlib import Path

import pytest

from tools.site_compare.config import combo_id, combo_key, context_axes, expand_combos, load_product
from tools.site_compare.model import (
    AxisSpec, ComboResult, Context, Money, Offer, Option, PriceTexts, RunData, Shot, SpecItem, State, TextBox,
)

LEGACY = Path("tests/site_compare/fixtures/legacy_fold8_data.json")

DISCOVER_YAML = """
id: demo
title: Demo
axes: [{name: size, iterate: true}]
contexts:
  - {id: uk, label: UK, driver: pd, locale: en-GB, currency: GBP, url: "https://www.samsung.com/uk/x/", ref_sku: A1}
  - {id: us, label: US, driver: us_pdp, locale: en-US, currency: USD, url: "https://www.samsung.com/us/x/", ref_sku: B1,
     cookies: {eddzipcode: "10001"}, axes: [{name: depth, iterate: true}]}
  - {id: uk-f, label: UK F, driver: pd, locale: en-GB, currency: GBP, url: "https://www.samsung.com/uk/y/", ref_sku: C1,
     spec_only: true, axes: [], spec_url: "https://www.samsung.com/uk/z/"}
sections:
  - {id: size, label_ko: 크기, patterns: ["size"]}
key_specs:
  - {id: capacity, label_ko: 용량, patterns: ["capacity"]}
"""


def _write(tmp_path, text):
    p = tmp_path / "p.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_legacy_rundata_loads():
    run = RunData.from_json(LEGACY)
    r = run.results[0]
    assert r.got.selection == {"storage": "256GB", "color": "Graphite"}
    assert r.full_shots == ["shots/uk__256gb__full.png"]
    assert r.specs == [] and r.spec_shots == [] and r.is_ref is False
    assert r.key == "256GB · Graphite"
    assert run.discovered == {}


def test_rundata_v2_roundtrip(tmp_path):
    ctx = Context("uk", "UK", "pd", "https://x/uk/", "en-GB", "GBP", axes=[AxisSpec("size", iterate=True)], ref_sku="A1")
    state = State({"size": '77"'}, None, "A1", PriceTexts("£3,499.00"), available=True)
    shot = Shot("Specs", None, 1, "shots/s.png", 10, 20, [TextBox("Weight", 1, 2, 3, 4)])
    res = ComboResult("uk__77", "uk", "main", {"size": "77"}, state, "https://x/uk/", "ok", Money(3499.0, "GBP"),
                      Offer("A1", 3499.0, "GBP", None), True, [shot], [], ["shots/f-01.png", "shots/f-02.png"], [],
                      "2026-10-28T12:00:00+09:00", specs=[SpecItem("Weight", "Net Weight", "28.2 kg")],
                      spec_shots=[shot], key='77"', is_ref=True)
    run = RunData("demo", "Demo", "r1", "2026-10-28T12:00:00+09:00", [1440, 1000], 5000, [ctx], [res], discovered={"uk": 1})
    run.to_json(tmp_path / "data.json")
    assert RunData.from_json(tmp_path / "data.json") == run


def test_load_discover_product(tmp_path):
    p = load_product(_write(tmp_path, DISCOVER_YAML))
    assert p.mode == "discover"
    us = next(c for c in p.contexts if c.id == "us")
    assert context_axes(p, us) == [AxisSpec("depth", iterate=True)]
    assert context_axes(p, p.contexts[0]) == [AxisSpec("size", iterate=True)]
    assert us.cookies == {"eddzipcode": "10001"}
    ukf = next(c for c in p.contexts if c.id == "uk-f")
    assert ukf.spec_only and ukf.spec_driver == "pd" and context_axes(p, ukf) == []
    assert [k.id for k in p.key_specs] == ["capacity"]


def test_discover_requires_ref_sku(tmp_path):
    with pytest.raises(ValueError):
        load_product(_write(tmp_path, DISCOVER_YAML.replace(", ref_sku: A1", "")))


def test_discover_rejects_unknown_driver(tmp_path):
    with pytest.raises(ValueError):
        load_product(_write(tmp_path, DISCOVER_YAML.replace("driver: pd,", "driver: nope,", 1)))


def test_expand_combos_rejects_discover(tmp_path):
    with pytest.raises(ValueError):
        expand_combos(load_product(_write(tmp_path, DISCOVER_YAML)))


def test_combo_id_and_key():
    path = [Option("size", "77", '77"'), Option("connectivity", "lte", "LTE")]
    assert combo_id("uk", path) == "uk__77__lte"
    assert combo_key(path) == '77" · LTE'
    assert combo_id("us", []) == "us__ref" and combo_key([]) == "기준 구성"


def test_fold8_product_still_click_mode():
    p = load_product(Path("tools/site_compare/products/fold8_ultra.yaml"))
    assert p.mode == "click" and len(expand_combos(p)) == 39
