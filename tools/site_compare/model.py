"""Data model shared by config, capture and report."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AxisSpec:
    name: str
    iterate: bool = False
    fixed: str | None = None


@dataclass
class Option:
    axis: str
    value: str  # normalized for comparison (lowercase, no spaces/quotes)
    label: str  # as shown on screen
    sku: str | None = None  # SKU the page moves to when this option is chosen, if known
    url: str | None = None
    available: bool = True
    handle: str | None = None  # driver-specific locator hint (input id, an-la value …)


@dataclass
class SpecItem:
    group: str
    label: str
    value: str


@dataclass
class Context:
    id: str
    label: str
    driver: str
    url: str
    locale: str
    currency: str
    region: str | None = None
    axes: list[AxisSpec] | None = None  # overrides the product axes (discover mode)
    ref_sku: str | None = None
    spec_url: str | None = None  # specs live on another page (e.g. the PDP of a buy page)
    spec_driver: str | None = None
    cookies: dict[str, str] | None = None
    spec_only: bool = False


@dataclass
class Combo:
    id: str
    context_id: str
    kind: str  # "main" | "color_check"
    want: dict[str, str]
    path: list[Option] = field(default_factory=list)
    target_sku: str | None = None
    key: str = ""
    is_ref: bool = False


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
    storages: list[str] = field(default_factory=list)
    colors: dict[str, str] = field(default_factory=dict)  # color name -> SKU color code
    fixed_color: str = ""
    carriers: list[str] = field(default_factory=list)
    sections: list[SectionRule] = field(default_factory=list)
    mode: str = "click"  # "click" (explicit combos, Fold8) | "discover" (axes found on the page)
    axes: list[AxisSpec] = field(default_factory=list)
    key_specs: list[SectionRule] = field(default_factory=list)


@dataclass
class PriceTexts:
    base: str | None = None
    monthly: str | None = None
    headline: str | None = None
    was: str | None = None


@dataclass
class State:
    selection: dict[str, str]
    region: str | None
    sku: str | None
    prices: PriceTexts = field(default_factory=PriceTexts)
    available: bool | None = None  # False when the page says the product cannot be bought


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
    full_shots: list[str]
    warnings: list[str]
    captured_at: str
    specs: list[SpecItem] = field(default_factory=list)
    spec_shots: list[Shot] = field(default_factory=list)
    key: str = ""
    is_ref: bool = False


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
    discovered: dict[str, int] = field(default_factory=dict)  # leaves found per context (discover mode)

    def to_json(self, path: Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def from_json(cls, path: Path) -> "RunData":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            product_id=d["product_id"], title=d["title"], run_id=d["run_id"], captured_at=d["captured_at"],
            viewport=d["viewport"], wait_ms=d["wait_ms"],
            contexts=[_context(c) for c in d["contexts"]],
            results=[_result(r) for r in d["results"]],
            discovered=d.get("discovered") or {},
        )


def _context(d: dict) -> Context:
    axes = d.get("axes")
    return Context(**{**d, "axes": [AxisSpec(**a) for a in axes] if axes is not None else None})


def _shot(d: dict) -> Shot:
    return Shot(**{**d, "texts": [TextBox(**t) for t in d["texts"]]})


def _state(d: dict | None) -> State | None:
    if d is None:
        return None
    if "selection" in d:
        sel = d["selection"]
    else:  # v1 (Fold8) layout: storage / color / carrier fields
        sel = {k: d[k] for k in ("storage", "color", "carrier") if d.get(k)}
    return State(sel, d.get("region"), d.get("sku"), PriceTexts(**d["prices"]), d.get("available"))


def _result(d: dict) -> ComboResult:
    d = dict(d)
    full = d.pop("full_shot", None)
    shots = d.get("full_shots", [full] if full else [])
    return ComboResult(**{
        **d,
        "got": _state(d["got"]),
        "base": Money(**d["base"]) if d["base"] else None,
        "jsonld": Offer(**d["jsonld"]) if d["jsonld"] else None,
        "sections": [_shot(s) for s in d["sections"]],
        "extras": [_shot(s) for s in d["extras"]],
        "full_shots": shots,
        "specs": [SpecItem(**s) for s in d.get("specs", [])],
        "spec_shots": [_shot(s) for s in d.get("spec_shots", [])],
        "key": d["key"] if "key" in d else " · ".join(v for v in d["want"].values() if v),  # v1 had no key
        "is_ref": d.get("is_ref", False),
    })
