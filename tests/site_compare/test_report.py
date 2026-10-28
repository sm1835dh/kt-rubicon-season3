import base64
import re
from pathlib import Path

import pytest

from tools.site_compare.config import load_product
from tools.site_compare.model import (
    ComboResult, Context, Money, Offer, PriceTexts, Product, RunData, Shot, State, TextBox,
)
from tools.site_compare.report import Card, Panel, build_report, load_cards, resolve_panel

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
SECTIONS = load_product(Path("tools/site_compare/products/fold8_ultra.yaml")).sections
UK = Context("uk", "UK", "hubble", "https://www.samsung.com/uk/x/", "en-GB", "GBP")
US = Context("us", "US", "us", "https://www.samsung.com/us/x/", "en-US", "USD")
PRODUCT = Product("fold8_ultra", "Galaxy Z Fold8 Ultra", [UK, US], ["256GB"], {"Graphite": "ZK"}, "Graphite",
                  ["Unlocked", "Verizon"], SECTIONS)


def _shot(cid, title, sid, order, texts=()):
    return Shot(title, sid, order, f"shots/{cid}__{order:02d}.png", 400, 200, list(texts))


def _res(cid, ctx, want, base_text, match, shots):
    state = State(want["storage"], "Graphite", want.get("carrier"), None, "SKU-" + cid,
                  PriceTexts(base_text, None, "headline", None))
    money = Money(float(re.sub(r"[^\d.]", "", base_text)), "GBP" if ctx == "uk" else "USD")
    return ComboResult(cid, ctx, "main", want, state, f"https://www.samsung.com/{ctx}/x/", "ok", money,
                       Offer("SKU-" + cid, money.value, money.currency, None), match, shots, [],
                       f"shots/{cid}__full.png", [], "2026-10-28T01:00:00+09:00")


@pytest.fixture
def run_dir(tmp_path):
    results = [
        _res("uk__256gb", "uk", {"storage": "256GB", "color": "Graphite"}, "£1,899.00", True, [
            _shot("uk__256gb", "Storage", "storage", 1, [TextBox("£1,899.00", 300, 40, 80, 20)]),
            _shot("uk__256gb", "Trade-in", "trade_in", 2),
            _shot("uk__256gb", "Pay monthly phone contracts", "carrier_plans", 3),
            _shot("uk__256gb", "Brand new thing", None, 4)]),
        _res("us__256gb__unlocked", "us", {"storage": "256GB", "color": "Graphite", "carrier": "Unlocked"},
             "$1,899.99", True, [_shot("us__256gb__unlocked", "Storage", "storage", 1)]),
        _res("us__256gb__verizon", "us", {"storage": "256GB", "color": "Graphite", "carrier": "Verizon"},
             "$1,899.99", False, [_shot("us__256gb__verizon", "Storage", "storage", 1),
                                  _shot("us__256gb__verizon", "Choose your purchase option", "purchase_option", 2)]),
    ]
    (tmp_path / "shots").mkdir()
    for r in results:
        for s in r.sections:
            (tmp_path / s.path).write_bytes(PNG)
        (tmp_path / r.full_shot).write_bytes(PNG)
    RunData("fold8_ultra", "Galaxy Z Fold8 Ultra", "20261028-010000", "2026-10-28T01:00:00+09:00",
            [1440, 1000], 5000, [UK, US], results).to_json(tmp_path / "data.json")
    return tmp_path


def _cards(tmp_path, text):
    p = tmp_path / "cards.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def _html(run_dir, cards_yaml="cards: []\n"):
    return build_report(run_dir, PRODUCT, _cards(run_dir, cards_yaml)).read_text(encoding="utf-8")


def _row(html, label):
    i = html.index(f'<th scope="row">{label}</th>')
    return html[i:html.index("</tr>", i)]


def test_report_has_sections_and_price_table(run_dir):
    html = _html(run_dir)
    assert "차이점 카드" in html and "부록" in html and "US · Verizon" in html
    assert re.search(r'<td class="[^"]*\bdiff\b[^"]*"[^>]*>\s*<a href="#combo-us__256gb__verizon"', html)
    assert not re.search(r'<td class="[^"]*\bdiff\b[^"]*"[^>]*>\s*<a href="#combo-us__256gb__unlocked"', html)


def test_menu_table_marks_missing_section(run_dir):
    row = _row(_html(run_dir), "트레이드인")
    assert "✓" in row and "—" in row


def test_menu_table_lists_unmapped_title(run_dir):
    assert "Brand new thing" in _row(_html(run_dir), "Brand new thing")


def test_card_highlight_resolved(run_dir):
    run = RunData.from_json(run_dir / "data.json")
    p = resolve_panel(Panel("uk__256gb", "storage", ["£1,899.00"], None), run, PRODUCT)
    assert p["warnings"] == []
    assert len(p["boxes"]) == 1
    b = p["boxes"][0]
    assert (b["left"], b["top"], b["width"], b["height"]) == (75.0, 20.0, 20.0, 10.0)


def test_card_with_missing_refs_shows_warning(run_dir):
    run = RunData.from_json(run_dir / "data.json")
    assert any("combo" in w for w in resolve_panel(Panel("nope", "storage", [], None), run, PRODUCT)["warnings"])
    assert any("section" in w for w in resolve_panel(Panel("uk__256gb", "care", [], None), run, PRODUCT)["warnings"])
    assert any("highlight" in w for w in
               resolve_panel(Panel("uk__256gb", "storage", ["£9.99"], None), run, PRODUCT)["warnings"])
    html = _html(run_dir, """
cards:
  - id: c1
    title: 깨진 카드
    tags: [국가별 구성 차이]
    panels:
      - {combo: nope, section: storage}
      - {combo: uk__256gb, section: storage, highlight: ["£1,899.00"]}
    observation: "[사실] 관찰"
    note: 메모
""")
    assert "card-warn" in html and "깨진 카드" in html


def test_load_cards_rejects_unknown_tag(run_dir):
    p = _cards(run_dir, "cards:\n  - {id: c, title: t, tags: [엉뚱한], panels: [], observation: o, note: n}\n")
    with pytest.raises(ValueError):
        load_cards(p)


def test_load_cards_missing_file_is_empty(tmp_path):
    assert load_cards(tmp_path / "none.yaml") == []


def test_report_has_no_external_urls(run_dir):
    html = _html(run_dir)
    assert '<script src="http' not in html and '<link href="http' not in html and "<link rel" not in html


def test_unavailable_cell_shows_label_not_price(run_dir):
    run = RunData.from_json(run_dir / "data.json")
    r = next(x for x in run.results if x.combo_id == "us__256gb__verizon")
    r.status = "unavailable"
    run.to_json(run_dir / "data.json")
    html = _html(run_dir)
    i = html.index('href="#combo-us__256gb__verizon"')
    cell = html[html.rindex("<td", 0, i):html.index("</td>", i)]
    assert "선택 불가" in cell and "$1,899.99" not in cell


def test_wide_panel_spans_row(run_dir):
    run = RunData.from_json(run_dir / "data.json")
    r = next(x for x in run.results if x.combo_id == "uk__256gb")
    bar = Shot("Price bar", "price_bar", 9, "shots/uk__256gb__09.png", 1440, 83, [])
    (run_dir / bar.path).write_bytes(PNG)
    r.sections.append(bar)
    run.to_json(run_dir / "data.json")
    html = _html(run_dir, "cards:\n  - {id: w, title: 넓은 패널, tags: [국가별 구성 차이], observation: o, note: n,"
                          " panels: [{combo: uk__256gb, section: price_bar}, {combo: uk__256gb, section: storage}]}\n")
    assert html.count('<figure class="wide">') == 1


def test_warned_combo_flagged_in_price_table_header_and_cards(run_dir):
    run = RunData.from_json(run_dir / "data.json")
    next(x for x in run.results if x.combo_id == "uk__256gb").warnings.append("price not rendered")
    run.to_json(run_dir / "data.json")
    html = _html(run_dir, "cards:\n  - {id: c, title: t, tags: [국가별 구성 차이], observation: o, note: n,"
                          " panels: [{combo: uk__256gb, section: storage}]}\n")
    i = html.index('href="#combo-uk__256gb"')
    cell = html[html.rindex("<td", 0, i):html.index("</td>", i)]
    assert "warned" in cell and "경고" in cell
    assert "경고 있는 조합 1" in html
    panel = resolve_panel(Panel("uk__256gb", "storage", [], None), RunData.from_json(run_dir / "data.json"), PRODUCT)
    assert panel["combo_warnings"] == ["price not rendered"]
