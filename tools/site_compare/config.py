"""Product config loading, combo expansion and section-title mapping."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from .model import Combo, Context, Product, SectionRule

DRIVERS = {"hubble", "us"}


def load_product(path: Path) -> Product:
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    contexts = [Context(**c) for c in d["contexts"]]
    ids = [c.id for c in contexts]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate context id in {path}: {ids}")
    for c in contexts:
        if c.driver not in DRIVERS:
            raise ValueError(f"unknown driver {c.driver!r} for context {c.id}")
    if d["fixed_color"] not in d["colors"]:
        raise ValueError(f"fixed_color {d['fixed_color']!r} not in colors")
    return Product(
        id=d["id"], title=d["title"], contexts=contexts, storages=list(d["storages"]),
        colors=dict(d["colors"]), fixed_color=d["fixed_color"], carriers=list(d.get("carriers") or []),
        sections=[SectionRule(**s) for s in d["sections"]],
    )


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def expand_combos(product: Product) -> list[Combo]:
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
                main.append(Combo(cid, ctx.id, "main", want))
        for color in product.colors:
            if color == product.fixed_color:
                continue
            want = {"storage": first, "color": color}
            if carriers[0]:
                want["carrier"] = carriers[0]
            checks.append(Combo(f"{ctx.id}__{slug(first)}__color-{slug(color)}", ctx.id, "color_check", want))
    return main + checks


def map_section(title: str, rules: list[SectionRule]) -> str | None:
    t = re.sub(r"\s+", " ", title).strip()
    for rule in rules:
        if any(re.search(p, t, re.IGNORECASE) for p in rule.patterns):
            return rule.id
    return None
