"""Data model shared by config, capture and report."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Context:
    id: str
    label: str
    driver: str
    url: str
    locale: str
    currency: str
    region: str | None = None


@dataclass
class Combo:
    id: str
    context_id: str
    kind: str  # "main" | "color_check"
    want: dict[str, str]


@dataclass
class SectionRule:
    id: str
    label_ko: str
    patterns: list[str]


@dataclass
class Product:
    id: str
    title: str
    contexts: list[Context]
    storages: list[str]
    colors: dict[str, str]  # color name -> SKU color code
    fixed_color: str
    carriers: list[str]
    sections: list[SectionRule]


@dataclass
class PriceTexts:
    base: str | None = None
    monthly: str | None = None
    headline: str | None = None
    was: str | None = None


@dataclass
class State:
    storage: str | None
    color: str | None
    carrier: str | None
    region: str | None
    sku: str | None
    prices: PriceTexts = field(default_factory=PriceTexts)


@dataclass
class Money:
    value: float
    currency: str


@dataclass
class Offer:
    sku: str
    price: float
    currency: str
    strike: float | None


@dataclass
class TextBox:
    text: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class Shot:
    title: str
    section_id: str | None
    order: int
    path: str
    width: int
    height: int
    texts: list[TextBox]


@dataclass
class ComboResult:
    combo_id: str
    context_id: str
    kind: str
    want: dict[str, str]
    got: State | None
    url_final: str | None
    status: str  # ok | unavailable | mismatch | error
    base: Money | None
    jsonld: Offer | None
    price_match: bool | None
    sections: list[Shot]
    extras: list[Shot]
    full_shot: str | None
    warnings: list[str]
    captured_at: str


@dataclass
class RunData:
    product_id: str
    title: str
    run_id: str
    captured_at: str
    viewport: list[int]
    wait_ms: int
    contexts: list[Context]
    results: list[ComboResult]

    def to_json(self, path: Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> "RunData":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            product_id=d["product_id"], title=d["title"], run_id=d["run_id"], captured_at=d["captured_at"],
            viewport=d["viewport"], wait_ms=d["wait_ms"],
            contexts=[Context(**c) for c in d["contexts"]],
            results=[_result(r) for r in d["results"]],
        )


def _shot(d: dict) -> Shot:
    return Shot(**{**d, "texts": [TextBox(**t) for t in d["texts"]]})


def _result(d: dict) -> ComboResult:
    got = d["got"]
    if got is not None:
        got = State(**{**got, "prices": PriceTexts(**got["prices"])})
    return ComboResult(**{
        **d,
        "got": got,
        "base": Money(**d["base"]) if d["base"] else None,
        "jsonld": Offer(**d["jsonld"]) if d["jsonld"] else None,
        "sections": [_shot(s) for s in d["sections"]],
        "extras": [_shot(s) for s in d["extras"]],
    })
