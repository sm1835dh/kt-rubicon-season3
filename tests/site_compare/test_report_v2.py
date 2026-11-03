import base64
import html as html_lib
import json
import re
from pathlib import Path

from tools.site_compare.model import (
    ComboResult, Context, Money, PriceTexts, Product, RunData, SectionRule, Shot, SpecItem, State, TextBox,
)
from tools.site_compare.report import Panel, build_index, build_report, resolve_panel

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
UK = Context("uk", "UK", "pd", "https://www.samsung.com/uk/x/", "en-GB", "GBP", ref_sku="UK77")
UKF = Context("uk-f", "UK · old", "pd", "https://www.samsung.com/uk/y/", "en-GB", "GBP", ref_sku="UKF", spec_only=True)
US = Context("us", "US", "us_pdp", "https://www.samsung.com/us/x/", "en-US", "USD", ref_sku="US77")
KEY = [SectionRule("capacity", "용량", ["capacity"]), SectionRule("weight", "무게", ["^net weight"])]
SECTIONS = [SectionRule("size", "크기", ["size"])]
PRODUCT = Product("demo", "Demo", [UK, UKF, US], sections=SECTIONS, mode="discover", key_specs=KEY)


def _res(ctx, size, base, *, ref=False, status="ok", available=True, specs=(), spec_shots=(), full=1):
    cid = f"{ctx.id}__{size}" if size else f"{ctx.id}__ref"
    label = f'{size}"' if size and ctx is US else (size or "기준 구성")
    state = State({"size": label} if size else {}, None, f"SKU-{cid}", PriceTexts(base), available)
    money = Money(float(re.sub(r"[^\d.]", "", base)), ctx.currency) if base else None
    return ComboResult(cid, ctx.id, "main", {"size": label} if size else {}, state, ctx.url, status, money, None,
                       None, [Shot("Choose your size", "size", 1, f"shots/{cid}__01.png", 10, 10, [])], [],
                       [f"shots/{cid}__full-{n:02d}.png" for n in range(1, full + 1)], [], "2026-10-29T10:00:00+09:00",
                       specs=list(specs), spec_shots=list(spec_shots), key=label, is_ref=ref)


def _run_dir(tmp_path, results, contexts=(UK, UKF, US), discovered=None):
    d = tmp_path / "demo" / "20261029-100000"
    (d / "shots").mkdir(parents=True)
    for r in results:
        for p in [s.path for s in r.sections + r.spec_shots] + r.full_shots:
            (d / p).write_bytes(PNG)
    RunData("demo", "Demo", d.name, "2026-10-29T10:00:00+09:00", [1440, 1000], 5000, list(contexts), results,
            discovered=discovered or {}).to_json(d / "data.json")
    return d


def _cards(tmp_path, text="cards: []\n"):
    p = tmp_path / "cards.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def _html(tmp_path, results, cards="cards: []\n", **kw):
    d = _run_dir(tmp_path, results, **kw)
    return build_report(d, PRODUCT, _cards(tmp_path, cards)).read_text(encoding="utf-8")


def _row(html, label):
    i = html.index(f'<th scope="row">{label}</th>')
    return html[i:html.index("</tr>", i)]


def test_discover_price_table_rows_union_and_missing_cells(tmp_path):
    results = [_res(UK, s, f"£{s},000.00", ref=s == "77") for s in ("48", "55", "65", "77")]
    results += [_res(UKF, None, None, ref=True, status="unavailable", available=False)]
    results += [_res(US, s, f"${s},999.99", ref=s == "77") for s in ("55", "65", "77", "83")]
    html = _html(tmp_path, results)
    table = html[html.index('id="price-table"'):]
    table = table[:table.index("</table>")]
    rows = [html_lib.unescape(m).rstrip('"') for m in re.findall(r'<th scope="row">([^<]+)</th>', table)]
    assert rows == ["48", "55", "65", "77", "83"]  # the spec-only context sits in the reference (77) row
    assert "판매 종료" in _row(table, "77")
    assert "—" in _row(table, "83&#34;").split("</td>")[0]  # UK has no 83" (label comes from US: 83")
    assert "$55,999.99" in _row(table, "55") and "£55,000.00" in _row(table, "55")  # 55 and 55" share a row


def test_discontinued_cell_label(tmp_path):
    results = [_res(UK, None, "£1.00", ref=True), _res(UKF, None, None, ref=True, status="unavailable",
                                                        available=False), _res(US, None, "$1.00", ref=True)]
    html = _html(tmp_path, results)
    assert "판매 종료" in _row(html[html.index('id="price-table"'):], "기준 구성")


def test_key_spec_table_uses_ref_combo(tmp_path):
    ref = _res(UK, "77", "£1.00", ref=True, specs=[SpecItem("Overview", "Washing Capacity (kg)", "11 kg"),
                                                   SpecItem("Weight", "Net Weight", "75 kg")])
    other = _res(UK, "55", "£1.00", specs=[SpecItem("Overview", "Washing Capacity (kg)", "9 kg")])
    us = _res(US, "77", "$1.00", ref=True, specs=[SpecItem("Specs", "Washer Capacity (cu. ft.)", "5.3")])
    html = _html(tmp_path, [ref, other, us])
    table = html[html.index('id="key-specs"'):]
    row = _row(table, "용량")
    assert "11 kg" in row and "9 kg" not in row and "5.3" in row
    assert 'title="Washing Capacity (kg)"' in row
    assert "—" in _row(table, "무게").split("</td>")[-2]  # US has no net weight


def test_spec_appendix_and_slices(tmp_path):
    specs = [SpecItem("Display", "Screen Size", '77"'), SpecItem("Display", "Resolution", "3840 x 2160")]
    shot = Shot("Specs", None, 1, "shots/uk__77__spec-1.png", 10, 10, [TextBox("Screen Size", 1, 1, 5, 5)])
    html = _html(tmp_path, [_res(UK, "77", "£1.00", ref=True, specs=specs, spec_shots=[shot], full=3)])
    assert html.count("<td>Screen Size</td>") == 1 and "3840 x 2160" in html
    assert all(f'shots/uk__77__full-0{n}.png' in html for n in (1, 2, 3))
    assert "shots/uk__77__spec-1.png" in html


def test_card_spec_panel(tmp_path):
    shot = Shot("Specs", None, 1, "shots/uk__77__spec-1.png", 100, 100, [TextBox("6.1 cu.ft", 10, 20, 30, 10)])
    d = _run_dir(tmp_path, [_res(UK, "77", "£1.00", ref=True, spec_shots=[shot])])
    p = resolve_panel(Panel("uk__77", "spec", ["6.1 cu.ft"], None), RunData.from_json(d / "data.json"), PRODUCT)
    assert p["warnings"] == [] and len(p["boxes"]) == 1 and p["img"] == "shots/uk__77__spec-1.png"


def test_discovered_counts_in_header(tmp_path):
    html = _html(tmp_path, [_res(UK, "77", "£1.00", ref=True)], discovered={"uk": 4, "us": 4})
    assert "UK 4" in html and "US 4" in html


def test_index_lists_products(tmp_path):
    _run_dir(tmp_path, [_res(UK, "77", "£1.00", ref=True)])
    other = tmp_path / "fold8" / "20261028-100623"
    (other / "shots").mkdir(parents=True)
    RunData("fold8", "Fold8", other.name, "2026-10-28T10:06:23+09:00", [1440, 1000], 5000, [UK], []).to_json(
        other / "data.json")
    (tmp_path / "demo" / "20261029-100000" / "report.html").write_text("x")
    out = build_index(tmp_path)
    html = out.read_text(encoding="utf-8")
    assert out == tmp_path / "index.html"
    assert 'href="demo/20261029-100000/report.html"' in html and "Fold8" in html and "ok 1" in html


def test_fold8_rebuild_from_legacy_run(tmp_path):
    from tools.site_compare.config import load_product
    d = tmp_path / "fold8_ultra" / "legacy"
    (d / "shots").mkdir(parents=True)
    (d / "data.json").write_text(Path("tests/site_compare/fixtures/legacy_fold8_data.json").read_text())
    product = load_product(Path("tools/site_compare/products/fold8_ultra.yaml"))
    cards = _cards(tmp_path, "cards:\n  - {id: c, title: t, tags: [국가별 구성 차이], observation: o, note: n,"
                             " panels: [{combo: uk__256gb, section: storage}]}\n")
    html = build_report(d, product, cards).read_text(encoding="utf-8")
    assert "256GB" in html and 'id="key-specs"' not in html  # Fold8 has no key_specs


def test_build_remaps_section_titles_with_current_rules(tmp_path):
    r = _res(UK, "77", "£1.00", ref=True)
    r.sections = [Shot("Acheter Directement. Obtenez Plus.", None, 1, "shots/uk__77__01.png", 10, 10,
                       [TextBox("Livraison gratuite", 1, 1, 5, 5)])]
    d = _run_dir(tmp_path, [r])
    rules = SECTIONS + [SectionRule("buy_direct", "직접 구매 혜택", ["acheter directement"])]
    product = Product("demo", "Demo", [UK, UKF, US], sections=rules, mode="discover", key_specs=KEY)
    cards = _cards(tmp_path, "cards:\n  - {id: c, title: t, tags: [국가별 구성 차이], observation: o, note: n,"
                             " panels: [{combo: uk__77, section: buy_direct, highlight: [Livraison gratuite]}]}\n")
    html = build_report(d, product, cards).read_text(encoding="utf-8")
    assert "section not found" not in html and "highlight not found" not in html
    assert '<th scope="row">직접 구매 혜택</th>' in html  # menu table row uses the rule's label


def test_discover_rules_describe_axes_and_ref_skus(tmp_path):
    from tools.site_compare.model import AxisSpec
    us = Context("us", "US", "us_pdp", "https://www.samsung.com/us/x/", "en-US", "USD", ref_sku="US77",
                 axes=[AxisSpec("depth", iterate=True)])
    product = Product("demo", "Demo", [UK, UKF, us], sections=SECTIONS, mode="discover", key_specs=KEY,
                      axes=[AxisSpec("size", iterate=True), AxisSpec("color", fixed="Graphite")])
    d = _run_dir(tmp_path, [_res(UK, "77", "£1.00", ref=True)], contexts=(UK, UKF, us))
    html = build_report(d, product, _cards(tmp_path)).read_text(encoding="utf-8")
    rules = html[html.index("캡쳐 규칙"):html.index("</table>", html.index("캡쳐 규칙"))]
    assert "통신사" not in rules and "용량의" not in rules  # Fold8 (click mode) wording stays out
    assert "size 전체 · color Graphite 고정" in rules and "depth 전체" in rules and "스펙만" in rules
    assert "<td>UK77</td>" in rules and "<td>US77</td>" in rules


def test_tall_panel_is_cropped_around_highlights(tmp_path):
    tall = Shot("Specs (2/2)", None, 2, "shots/uk__77__spec-2.png", 1440, 2600,
                [TextBox("1782.6 x 1089.6 x 319.9 inch", 600, 2000, 200, 20), TextBox("Round Feet", 700, 1900, 80, 20)])
    small = Shot("Choose your size", "size", 1, "shots/uk__77__01.png", 448, 334, [TextBox("77", 100, 100, 30, 20)])
    r = _res(UK, "77", "£1.00", ref=True, spec_shots=[Shot("Specs (1/2)", None, 1, "shots/uk__77__spec-1.png", 1440,
                                                          2600, []), tall])
    r.sections = [small]
    run = RunData.from_json(_run_dir(tmp_path, [r]) / "data.json")
    p = resolve_panel(Panel("uk__77", "spec-2", ["1782.6 x 1089.6 x 319.9 inch", "Round Feet"], None), run, PRODUCT)
    c = p["crop"]
    assert c and c["x0"] <= 600 and c["x1"] >= 800 and c["y0"] <= 1900 and c["y1"] >= 2020
    assert c["x1"] - c["x0"] < 1440 and c["y1"] - c["y0"] < 1000  # a readable window, not the whole slice
    assert p["view_w"] == c["x1"] - c["x0"]  # shown at most at its pixel width (no upscaling)
    b = p["boxes"][0]  # boxes are relative to the crop window
    assert b["left"] == round((600 - c["x0"]) / (c["x1"] - c["x0"]) * 100, 3)
    assert b["top"] == round((2000 - c["y0"]) / (c["y1"] - c["y0"]) * 100, 3)
    assert resolve_panel(Panel("uk__77", "size", ["77"], None), run, PRODUCT)["crop"] is None


def test_wide_window_spans_the_card_row(tmp_path):
    trade = Shot("Trade-in", "trade", 1, "shots/uk__77__02.png", 1264, 263,
                 [TextBox("Get an instant discount for trading in your current device.", 40, 60, 900, 24)])
    narrow = Shot("Choose your size", "size", 1, "shots/uk__77__01.png", 448, 334, [TextBox("77", 100, 100, 30, 20)])
    r = _res(UK, "77", "£1.00", ref=True)
    r.sections = [narrow, trade]
    run = RunData.from_json(_run_dir(tmp_path, [r]) / "data.json")
    rules = SECTIONS + [SectionRule("trade", "트레이드인", ["trade-in"])]
    product = Product("demo", "Demo", [UK, UKF, US], sections=rules, mode="discover", key_specs=KEY)
    assert resolve_panel(Panel("uk__77", "trade", ["instant discount"], None), run, product)["wide"] is True
    assert resolve_panel(Panel("uk__77", "size", ["77"], None), run, product)["wide"] is False


def test_tiny_highlight_gets_a_visible_box(tmp_path):
    summary = Shot("Summary", "size", 1, "shots/uk__77__01.png", 1440, 619, [TextBox("Charger included", 987, 815 - 400, 1, 1)])
    r = _res(UK, "77", "£1.00", ref=True)
    r.sections = [summary]
    run = RunData.from_json(_run_dir(tmp_path, [r]) / "data.json")
    p = resolve_panel(Panel("uk__77", "size", ["Charger included"], None), run, PRODUCT)
    c = p["crop"]
    cw, ch = (c["x1"] - c["x0"], c["y1"] - c["y0"]) if c else (1440, 619)
    b = p["boxes"][0]
    assert b["width"] * cw / 100 >= 28 and b["height"] * ch / 100 >= 28  # alt text of an icon is a 1×1 element


def test_same_sku_in_another_language_shares_a_row(tmp_path):
    en = Context("ca-en-on", "CA-EN", "pd", "https://www.samsung.com/ca/x/", "en-CA", "CAD", ref_sku="RF23")
    fr = Context("ca-fr-on", "CA-FR", "pd", "https://www.samsung.com/ca_fr/x/", "fr-CA", "CAD", ref_sku="RF23")
    a, b = _res(en, "silver", "$3,299.98", ref=True), _res(fr, "acierinoxydable", "$3,299.98", ref=True)
    a.got.sku = b.got.sku = "RF23DG9600SRAC"
    mism = _res(fr, "noir", "$1.00", status="mismatch")
    mism.got.sku = "RF23DG9600SRAC"  # a mismatch shows another variant's SKU: it must not join that row
    product = Product("demo", "Demo", [en, fr], sections=SECTIONS, mode="discover", key_specs=KEY)
    d = _run_dir(tmp_path, [a, b, mism], contexts=(en, fr))
    html = build_report(d, product, _cards(tmp_path)).read_text(encoding="utf-8")
    table = html[html.index('id="price-table"'):]
    table = table[:table.index("</table>")]
    assert re.findall(r'<th scope="row">([^<]+)</th>', table) == ["silver", "noir"]


def test_key_spec_patterns_are_tried_in_order(tmp_path):
    ref = _res(UK, "77", "£1.00", ref=True, specs=[SpecItem("Performance", "Noise Emission Class", "A"),
                                                   SpecItem("Performance", "Noise Level (Spin)", "72 dB")])
    product = Product("demo", "Demo", [UK, UKF, US], sections=SECTIONS, mode="discover",
                      key_specs=[SectionRule("noise", "소음", ["noise level", "noise"])])
    html = build_report(_run_dir(tmp_path, [ref]), product, _cards(tmp_path)).read_text(encoding="utf-8")
    row = _row(html[html.index('id="key-specs"'):], "소음")
    assert "72 dB" in row and ">A<" not in row


def test_same_sku_in_another_country_keeps_its_own_row(tmp_path):
    ca = Context("ca-en-on", "CA-EN", "pd", "https://www.samsung.com/ca/x/", "en-CA", "CAD", ref_sku="WF90")
    us = Context("us", "US", "us_pdp", "https://www.samsung.com/us/x/", "en-US", "USD", ref_sku="WF90")
    uk = Context("uk", "UK", "pd", "https://www.samsung.com/uk/x/", "en-GB", "GBP", ref_sku="WF90H")
    a, b = _res(ca, "gray", "$1,499.99", ref=True), _res(us, "darksteel", "$1,299.00", ref=True)
    c = _res(uk, "darksteel", "£1.00", ref=True)
    a.got.sku = b.got.sku = "WF90F53ADSA5"  # CA calls it Gray, US calls it Dark Steel
    product = Product("demo", "Demo", [uk, ca, us], sections=SECTIONS, mode="discover", key_specs=KEY)
    html = build_report(_run_dir(tmp_path, [c, a, b], contexts=(uk, ca, us)), product, _cards(tmp_path)).read_text(
        encoding="utf-8")
    table = html[html.index('id="price-table"'):]
    table = table[:table.index("</table>")]
    assert "$1,299.00" in _row(table, "darksteel") and "$1,299.00" not in _row(table, "gray")
