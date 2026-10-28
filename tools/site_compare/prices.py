"""Money tokens/parsing and JSON-LD offer extraction."""
from __future__ import annotations

import json
import re

from .model import Money, Offer

_SP = "[   ]"
# en: "£1,899.00", "$2099.99" — symbol first, comma thousands, dot decimals
_EN = re.compile(r"[£$€]\s?(?:\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)(?![\d])")
# fr: "2 699,99 $" — symbol last, space thousands, comma decimals
_FR = re.compile(rf"(?<![\d,.])(?:\d{{1,3}}(?:{_SP}\d{{3}})+(?:,\d{{1,2}})?|\d+(?:,\d{{1,2}})?){_SP}?[$€]")
_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)


def _is_fr(locale: str) -> bool:
    return locale.lower().startswith("fr")


def money_tokens(text: str, locale: str) -> list[str]:
    if not text:
        return []
    return (_FR if _is_fr(locale) else _EN).findall(text)


def parse_money(token: str | None, locale: str, currency: str) -> Money | None:
    if not token:
        return None
    toks = money_tokens(token, locale)
    if not toks:
        return None
    num = re.sub(r"[£$€\s  ]", "", toks[0])
    num = num.replace(",", ".") if _is_fr(locale) else num.replace(",", "")
    return Money(float(num), currency)


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _offer(sku: str, offers) -> Offer | None:
    o = offers[0] if isinstance(offers, list) and offers else offers
    if not isinstance(o, dict):
        return None
    price = o.get("price", o.get("lowPrice"))
    if price in (None, ""):
        return None
    strike = None
    specs = o.get("priceSpecification") or []
    for s in specs if isinstance(specs, list) else [specs]:
        if isinstance(s, dict) and "Strikethrough" in str(s.get("priceType", "")):
            strike = float(s["price"])
    return Offer(sku.upper(), float(price), o.get("priceCurrency", ""), strike)


def extract_offers(html: str) -> dict[str, Offer]:
    out: dict[str, Offer] = {}
    for m in _LD.finditer(html):
        try:
            data = json.loads(m.group(1).strip())
        except ValueError:
            continue
        for d in _walk(data):
            if d.get("sku") and d.get("offers"):
                off = _offer(str(d["sku"]), d["offers"])
                if off:
                    out.setdefault(off.sku, off)
    return out


def price_matches(base: Money | None, offer: Offer | None) -> bool | None:
    if base is None or offer is None:
        return None
    return base.currency == offer.currency and abs(base.value - offer.price) < 0.01
