import json

from tools.site_compare.model import Money, Offer
from tools.site_compare.prices import extract_offers, money_tokens, parse_money, price_matches


def test_money_tokens_uk_label():
    assert money_tokens("256GB｜12GB £52.75/mo. or £1,899.00", "en-GB") == ["£52.75", "£1,899.00"]


def test_money_tokens_ca_fr_label():
    assert money_tokens("À partir de 75,00 $ /mo.‡ ou 2 699,99 $", "fr-CA") == ["75,00 $", "2 699,99 $"]


def test_money_tokens_ca_fr_nbsp():
    assert money_tokens("ou 2 699,99 $", "fr-CA") == ["2 699,99 $"]


def test_money_tokens_us_was():
    assert money_tokens("was: $2099.99 $1,899.99", "en-US") == ["$2099.99", "$1,899.99"]


def test_money_tokens_ignores_plain_numbers():
    assert money_tokens("256GB｜12GB for 24 mos", "en-US") == []


def test_parse_money():
    assert parse_money("£1,899.00", "en-GB", "GBP") == Money(1899.0, "GBP")
    assert parse_money("2 699,99 $", "fr-CA", "CAD") == Money(2699.99, "CAD")
    assert parse_money("2 699,99 $", "fr-CA", "CAD") == Money(2699.99, "CAD")
    assert parse_money("$2099.99", "en-US", "USD") == Money(2099.99, "USD")
    assert parse_money("", "en-US", "USD") is None and parse_money(None, "en-US", "USD") is None


def _ld(obj):
    return f'<script type="application/ld+json">{json.dumps(obj)}</script>'


def test_extract_offers_product_group():
    html = _ld({"@type": "ProductGroup", "hasVariant": [
        {"sku": "SM-F976BZKBEUB", "offers": {"price": "1899", "priceCurrency": "GBP"}}]})
    assert extract_offers(html)["SM-F976BZKBEUB"] == Offer("SM-F976BZKBEUB", 1899.0, "GBP", None)


def test_extract_offers_us_strike():
    html = _ld({"@type": "Product", "sku": "SM-F976UDGAXAA", "offers": {
        "price": "1899.99", "priceCurrency": "USD",
        "priceSpecification": {"@type": "UnitPriceSpecification",
                               "priceType": "https://schema.org/StrikethroughPrice", "price": 2099.99}}})
    assert extract_offers(html)["SM-F976UDGAXAA"] == Offer("SM-F976UDGAXAA", 1899.99, "USD", 2099.99)


def test_extract_offers_lowercase_sku_and_list():
    html = _ld([{"@type": "BreadcrumbList"},
                {"@type": "Product", "sku": "sm-f976uzkavzw", "offers": [{"price": 1899.99, "priceCurrency": "USD"}]}])
    assert "SM-F976UZKAVZW" in extract_offers(html)


def test_extract_offers_ignores_broken_json():
    assert extract_offers('<script type="application/ld+json">{oops</script>') == {}


def test_price_matches():
    assert price_matches(Money(1899.99, "USD"), Offer("X", 1899.99, "USD", None)) is True
    assert price_matches(Money(1899.0, "USD"), Offer("X", 1899.99, "USD", None)) is False
    assert price_matches(Money(1899.99, "CAD"), Offer("X", 1899.99, "USD", None)) is False
    assert price_matches(None, Offer("X", 1.0, "USD", None)) is None
    assert price_matches(Money(1.0, "USD"), None) is None


def test_money_tokens_bare_monthly():
    text = "$379.99 or 15.83/mo for 24 mos at 0% APR"
    assert money_tokens(text, "en-US") == ["$379.99"]
    assert money_tokens(text, "en-US", bare_monthly=True) == ["$379.99", "$15.83"]
    assert money_tokens("Pay Monthly $54.13/mo for 24 mos", "en-US", bare_monthly=True) == ["$54.13"]
    assert money_tokens("or 102.09/mo", "en-GB", bare_monthly=True) == ["£102.09"]
