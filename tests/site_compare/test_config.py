from pathlib import Path

import pytest

from tools.site_compare.config import expand_combos, load_product, map_section, slug
from tools.site_compare.model import (
    ComboResult, Context, Money, Offer, PriceTexts, RunData, Shot, State, TextBox,
)

P = Path("tools/site_compare/products/fold8_ultra.yaml")


def test_load_product_fold8():
    p = load_product(P)
    assert [c.id for c in p.contexts] == ["uk", "ca-en-on", "ca-en-qc", "ca-fr-on", "ca-fr-qc", "us"]
    assert p.contexts[2].region == "CA-QC"
    assert p.contexts[5].driver == "us"
    assert p.fixed_color == "Graphite" and p.colors["Graphite"] == "ZK"


def test_load_product_rejects_unknown_driver(tmp_path):
    bad = P.read_text().replace("driver: us,", "driver: foo,")
    f = tmp_path / "bad.yaml"
    f.write_text(bad)
    with pytest.raises(ValueError):
        load_product(f)


def test_load_product_rejects_unknown_fixed_color(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text(P.read_text().replace("fixed_color: Graphite", "fixed_color: Pink"))
    with pytest.raises(ValueError):
        load_product(f)


def test_load_product_rejects_duplicate_context(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text(P.read_text().replace("{id: ca-en-qc,", "{id: ca-en-on,"))
    with pytest.raises(ValueError):
        load_product(f)


def test_expand_main_combos():
    main = [c for c in expand_combos(load_product(P)) if c.kind == "main"]
    assert len(main) == 21
    ids = {c.id for c in main}
    assert {"uk__256gb", "ca-fr-qc__1tb", "us__1tb__verizon", "us__256gb__unlocked"} <= ids
    us512 = next(c for c in main if c.id == "us__512gb__unlocked")
    assert us512.want == {"storage": "512GB", "color": "Graphite", "carrier": "Unlocked"}
    assert next(c for c in main if c.id == "uk__256gb").want == {"storage": "256GB", "color": "Graphite"}


def test_expand_color_checks():
    cc = [c for c in expand_combos(load_product(P)) if c.kind == "color_check"]
    assert len(cc) == 18  # 6 contexts × 3 non-fixed colors
    c = next(c for c in cc if c.id == "us__256gb__color-cream")
    assert c.want == {"storage": "256GB", "color": "Cream", "carrier": "Unlocked"}
    assert not any(c.want["color"] == "Graphite" for c in cc)


def test_expand_order_main_before_color_checks():
    kinds = [c.kind for c in expand_combos(load_product(P))]
    assert kinds == ["main"] * 21 + ["color_check"] * 18


@pytest.mark.parametrize("title,expected", [
    ("Samsung Trade-In", "trade_in"), ("Trade-in", "trade_in"), ("Couleur", "color"), ("Colour", "color"),
    ("Save more, upgrade sooner with the Annual Upgrade Program", "upgrade_program"),
    ("Économisez plus, mettez-vous à niveau plus tôt avec le programme de mise à niveau annuelle", "upgrade_program"),
    ("Samsung  Care+", "care"), ("Something new", None),
])
def test_map_section(title, expected):
    assert map_section(title, load_product(P).sections) == expected


def test_slug():
    assert [slug(s) for s in ["256GB", "Violet Shadow", "1TB"]] == ["256gb", "violet-shadow", "1tb"]


def test_rundata_roundtrip(tmp_path):
    ctx = Context("uk", "UK", "hubble", "https://x/uk/", "en-GB", "GBP", None)
    state = State({"storage": "256GB", "color": "Graphite"}, None, "SM-F976BZKBEUB",
                  PriceTexts("£1,899.00", "£52.75/mo.", "From …", None))
    shot = Shot("Storage", "storage", 1, "shots/a.png", 400, 300, [TextBox("£1,899.00", 1.0, 2.0, 3.0, 4.0)])
    res = ComboResult("uk__256gb", "uk", "main", {"storage": "256GB", "color": "Graphite"}, state,
                      "https://x/uk/", "ok", Money(1899.0, "GBP"), Offer("SM-F976BZKBEUB", 1899.0, "GBP", None),
                      True, [shot], [], ["shots/full.png"], ["w1"], "2026-10-28T01:00:00+09:00")
    run = RunData("fold8_ultra", "Galaxy Z Fold8 Ultra", "20261028-010000", "2026-10-28T01:00:00+09:00",
                  [1440, 1000], 5000, [ctx], [res])
    run.to_json(tmp_path / "data.json")
    assert RunData.from_json(tmp_path / "data.json") == run
