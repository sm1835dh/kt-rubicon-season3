"""Product config loading, combo expansion and section-title mapping."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from .model import AxisSpec, Combo, Context, Option, Product, SectionRule

DRIVERS = {"hubble", "us", "pd", "us_pdp", "watchbc"}


def _axes(items) -> list[AxisSpec]:
    return [AxisSpec(**a) for a in items or []]


def _context(c: dict) -> Context:
    c = dict(c)
    if "axes" in c:
        c["axes"] = _axes(c["axes"])
    if c.get("spec_url") and not c.get("spec_driver"):
        c["spec_driver"] = "pd"
    return Context(**c)


def load_product(path: Path) -> Product:
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    contexts = [_context(c) for c in d["contexts"]]
    ids = [c.id for c in contexts]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate context id in {path}: {ids}")
    for c in contexts:
        if c.driver not in DRIVERS:
            raise ValueError(f"unknown driver {c.driver!r} for context {c.id}")
        if c.spec_driver and c.spec_driver not in DRIVERS:
            raise ValueError(f"unknown spec_driver {c.spec_driver!r} for context {c.id}")
    sections = [SectionRule(**s) for s in d.get("sections") or []]
    key_specs = [SectionRule(**s) for s in d.get("key_specs") or []]
    if "storages" in d:  # click mode: explicit storage × colour (× carrier) combos (Fold8)
        if d["fixed_color"] not in d["colors"]:
            raise ValueError(f"fixed_color {d['fixed_color']!r} not in colors")
        return Product(
            id=d["id"], title=d["title"], contexts=contexts, storages=list(d["storages"]),
            colors=dict(d["colors"]), fixed_color=d["fixed_color"], carriers=list(d.get("carriers") or []),
            sections=sections, mode="click", key_specs=key_specs,
        )
    for c in contexts:
        if not c.ref_sku:
            raise ValueError(f"context {c.id} needs ref_sku in discover mode")
    return Product(id=d["id"], title=d["title"], contexts=contexts, sections=sections, mode="discover",
                   axes=_axes(d.get("axes")), key_specs=key_specs)


def context_axes(product: Product, ctx: Context) -> list[AxisSpec]:
    return ctx.axes if ctx.axes is not None else product.axes


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def combo_key(path: list[Option]) -> str:
    return " · ".join(o.label for o in path) if path else "기준 구성"


def combo_id(ctx_id: str, path: list[Option]) -> str:
    return f"{ctx_id}__" + "__".join(slug(o.value) for o in path) if path else f"{ctx_id}__ref"


def expand_combos(product: Product) -> list[Combo]:
    if product.mode != "click":
        raise ValueError("discover-mode combos are found on the page (capture.discover_leaves)")
    main: list[Combo] = []
    checks: list[Combo] = []
    first = product.storages[0]
    for ctx in product.contexts:
        carriers = product.carriers if ctx.driver == "us" else [None]
        for storage in product.storages:
            for carrier in carriers:
                want = {"storage": storage, "color": product.fixed_color}
                cid = f"{ctx.id}__{slug(storage)}"
                if carrier:
                    want["carrier"] = carrier
                    cid += f"__{slug(carrier)}"
                main.append(Combo(cid, ctx.id, "main", want, key=" · ".join(want.values())))
        for color in product.colors:
            if color == product.fixed_color:
                continue
            want = {"storage": first, "color": color}
            if carriers[0]:
                want["carrier"] = carriers[0]
            checks.append(Combo(f"{ctx.id}__{slug(first)}__color-{slug(color)}", ctx.id, "color_check", want,
                                key=" · ".join(want.values())))
    return main + checks


def map_section(title: str, rules: list[SectionRule]) -> str | None:
    t = re.sub(r"\s+", " ", title).strip()
    for rule in rules:
        if any(re.search(p, t, re.IGNORECASE) for p in rule.patterns):
            return rule.id
    return None
