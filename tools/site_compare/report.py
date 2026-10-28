"""Build report.html from a run's data.json and a product's card notes."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .model import ComboResult, Product, RunData, Shot

TAGS = ("국가별 구성 차이", "사이트 데이터 오류", "소스 vs 화면 불일치", "CA-FR 번역")
NOT_MENU = {"price_bar", "summary"}  # pseudo sections: captured, but not buy-flow steps


@dataclass
class Panel:
    combo: str
    section: str  # section_id | "full" | "extra-{n}"
    highlight: list[str] = field(default_factory=list)
    caption: str | None = None


@dataclass
class Card:
    id: str
    title: str
    tags: list[str]
    panels: list[Panel]
    observation: str
    note: str


def load_cards(path: Path) -> list[Card]:
    path = Path(path)
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cards = []
    for c in data.get("cards") or []:
        bad = [t for t in c.get("tags", []) if t not in TAGS]
        if bad:
            raise ValueError(f"card {c.get('id')}: unknown tags {bad}; allowed {TAGS}")
        panels = [Panel(p["combo"], p["section"], list(p.get("highlight") or []), p.get("caption"))
                  for p in c.get("panels") or []]
        cards.append(Card(c["id"], c["title"], list(c.get("tags") or []), panels,
                          c.get("observation", ""), c.get("note", "")))
    return cards


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ").replace(" ", " ")).strip()


def _find_shot(r: ComboResult, section: str) -> tuple[Shot | None, str | None]:
    if section == "full":
        return None, (r.full_shots[0] if r.full_shots else None)
    m = re.fullmatch(r"spec(?:-(\d+))?", section)
    if m:
        n = int(m.group(1) or 1)
        shot = r.spec_shots[n - 1] if 0 < n <= len(r.spec_shots) else None
        return shot, shot.path if shot else None
    m = re.fullmatch(r"extra-(\d+)", section)
    if m:
        n = int(m.group(1))
        shot = r.extras[n - 1] if 0 < n <= len(r.extras) else None
    else:
        shot = next((s for s in r.sections if s.section_id == section), None)
    return shot, shot.path if shot else None


def _got_text(r: ComboResult) -> str:
    if not r.got:
        return "(상태 없음)"
    parts = list(r.got.selection.values()) + [r.got.region, r.got.sku]
    return " | ".join(p for p in parts if p)


def resolve_panel(panel: Panel, run: RunData, product: Product) -> dict:
    labels = {c.id: c.label for c in run.contexts}
    sec_labels = {s.id: s.label_ko for s in product.sections}
    out = {"img": None, "width": None, "height": None, "boxes": [], "warnings": [], "anchor": panel.combo,
           "label": panel.combo, "section": sec_labels.get(panel.section, panel.section), "url": None, "got": "",
           "caption": panel.caption, "status": None, "wide": False, "combo_warnings": []}
    r = next((x for x in run.results if x.combo_id == panel.combo), None)
    if r is None:
        out["warnings"].append(f"combo not found: {panel.combo}")
        return out
    carrier = r.want.get("carrier")
    out.update(label=labels.get(r.context_id, r.context_id) + (f" · {carrier}" if carrier else ""),
               url=r.url_final, got=_got_text(r), status=r.status, combo_warnings=list(r.warnings))
    shot, path = _find_shot(r, panel.section)
    if path is None:
        out["warnings"].append(f"section not found: {panel.combo} / {panel.section}")
        return out
    out["img"] = path
    if shot is None:
        if panel.highlight:
            out["warnings"].append("highlight not supported on full screenshot")
        return out
    out.update(width=shot.width, height=shot.height, wide=shot.height > 0 and shot.width / shot.height > 5)
    for h in panel.highlight:
        want = _ws(h)
        hits = [t for t in shot.texts if _ws(t.text) == want] or [t for t in shot.texts if want in _ws(t.text)]
        if not hits:
            out["warnings"].append(f"highlight not found: {h}")
            continue
        t = min(hits, key=lambda t: t.w * t.h)
        out["boxes"].append({"left": round(t.x / shot.width * 100, 3), "top": round(t.y / shot.height * 100, 3),
                             "width": round(t.w / shot.width * 100, 3), "height": round(t.h / shot.height * 100, 3)})
    return out


def _columns(run: RunData, product: Product) -> list[dict]:
    cols = []
    for ctx in run.contexts:
        if ctx.driver == "us" and product.carriers:
            cols += [{"ctx": ctx, "carrier": c, "label": f"{ctx.label} · {c}"} for c in product.carriers]
        else:
            cols.append({"ctx": ctx, "carrier": None, "label": ctx.label})
    return cols


def _main(run: RunData, ctx_id: str, storage: str, carrier: str | None) -> ComboResult | None:
    for r in run.results:
        if (r.kind == "main" and r.context_id == ctx_id and r.want.get("storage") == storage
                and r.want.get("carrier") == carrier):
            return r
    return None


def _row_id(r: ComboResult) -> str:
    return r.combo_id.split("__", 1)[1] if "__" in r.combo_id else r.combo_id


def _lead_number(label: str) -> float | None:
    m = re.match(r"\s*(\d+(?:\.\d+)?)", label)
    return float(m.group(1)) if m else None


def _ref_result(run: RunData, product: Product, col: dict) -> ComboResult | None:
    if product.mode == "click":
        return _main(run, col["ctx"].id, product.storages[0], col["carrier"])
    mine = [r for r in run.results if r.context_id == col["ctx"].id and r.kind == "main"]
    return next((r for r in mine if r.is_ref), mine[0] if mine else None)


def _price_rows(run: RunData, product: Product, cols: list[dict]) -> list[dict]:
    if product.mode == "click":
        return [{"label": s, "cells": [_price_cell(_main(run, c["ctx"].id, s, c["carrier"]), c) for c in cols]}
                for s in product.storages]
    # a context without option axes (e.g. a spec-only one) sits in the row of the other contexts' reference combo
    ref_row = next((_row_id(r) for r in run.results if r.is_ref and _row_id(r) != "ref"), "ref")
    row_of = lambda r: ref_row if _row_id(r) == "ref" else _row_id(r)
    ids: list[str] = []
    labels: dict[str, str] = {}
    for ctx in run.contexts:  # union of combo keys in context order; "55" and '55"' share a row (same value)
        for r in run.results:
            if r.context_id == ctx.id and r.kind == "main" and row_of(r) not in labels:
                ids.append(row_of(r))
            if r.context_id == ctx.id and r.kind == "main" and _row_id(r) != "ref":
                labels.setdefault(row_of(r), r.key or row_of(r))
            elif r.context_id == ctx.id and r.kind == "main":
                labels.setdefault(row_of(r), "기준 구성")
    if ids and all(_lead_number(labels[i]) is not None for i in ids):
        ids.sort(key=lambda i: _lead_number(labels[i]))  # stable: 40mm·BT before 40mm·LTE
    rows = []
    for i in ids:
        cells = []
        for c in cols:
            r = next((r for r in run.results if r.context_id == c["ctx"].id and r.kind == "main" and row_of(r) == i),
                     None)
            cells.append(_price_cell(r, c) if r else
                         {"id": None, "cls": "cell missing" + (" spec-only" if c["ctx"].spec_only else ""),
                          "text": "—", "was": None, "title": "이 컨텍스트에는 없는 조합", "status": None, "warn": 0})
        rows.append({"label": labels[i], "cells": cells})
    return rows


def _key_spec_rows(run: RunData, product: Product, cols: list[dict]) -> list[dict]:
    refs = [_ref_result(run, product, c) for c in cols]
    rows = []
    for rule in product.key_specs:
        cells = []
        for r in refs:
            hit = next((sp for sp in (r.specs if r else []) if any(re.search(p, sp.label, re.I) for p in rule.patterns)),
                       None)
            cells.append({"value": hit.value, "label": hit.label} if hit else None)
        rows.append({"label": rule.label_ko, "cells": cells})
    return rows


def _price_cell(r: ComboResult | None, col: dict | None = None) -> dict:
    if r is None:
        return {"id": None, "cls": "cell missing", "text": "미수집", "was": None, "title": "", "status": None, "warn": 0}
    p = r.got.prices if r.got else None
    cls = "cell" + (" diff" if r.price_match is False else "") + ("" if r.status == "ok" else f" st-{r.status}")
    if col and col["ctx"].spec_only:
        cls += " spec-only"
    tip = []
    if p:
        tip += [f"headline: {p.headline}", f"monthly: {p.monthly}", f"was: {p.was}"]
    if r.jsonld:
        tip.append(f"JSON-LD: {r.jsonld.price} {r.jsonld.currency}" + (f" (정가 {r.jsonld.strike})" if r.jsonld.strike else ""))
    if r.status == "unavailable":  # the page stayed on another variant; its price is not this combo's price
        sold_out = bool(r.got and r.got.available is False)
        return {"id": r.combo_id, "cls": cls, "text": "판매 종료" if sold_out else "선택 불가", "was": None,
                "title": "\n".join(r.warnings), "status": None, "warn": 0}
    if r.warnings:
        cls += " warned"
        tip += r.warnings
    return {"id": r.combo_id, "cls": cls, "text": (p.base if p and p.base else "—"), "was": p.was if p else None,
            "title": "\n".join(tip), "status": r.status, "warn": len(r.warnings)}


def _menu_rows(run: RunData, product: Product, cols: list[dict]) -> list[dict]:
    per_col = []
    for c in cols:
        r = _ref_result(run, product, c)
        per_col.append([s for s in (r.sections if r else []) if s.section_id not in NOT_MENU])
    rows = []
    for rule in product.sections:
        if rule.id in NOT_MENU:
            continue
        cells = [next((s.order for s in shots if s.section_id == rule.id), None) for shots in per_col]
        if any(cells):
            rows.append({"label": rule.label_ko, "cells": cells})
    unmapped = []
    for shots in per_col:
        for s in shots:
            if s.section_id is None and _ws(s.title) not in unmapped:
                unmapped.append(_ws(s.title))
    for title in unmapped:
        rows.append({"label": title, "raw": True,
                     "cells": [next((s.order for s in shots if s.section_id is None and _ws(s.title) == title), None)
                               for shots in per_col]})
    return rows


def build_report(run_dir: Path, product: Product, cards_path: Path) -> Path:
    run_dir = Path(run_dir)
    run = RunData.from_json(run_dir / "data.json")
    cols = _columns(run, product)
    cards = []
    for card in load_cards(cards_path):
        panels = [resolve_panel(p, run, product) for p in card.panels]
        cards.append({"card": card, "panels": panels, "warnings": [w for p in panels for w in p["warnings"]]})
    labels = {c.id: c.label for c in run.contexts}
    by_ctx = {c.id: [r for r in run.results if r.context_id == c.id] for c in run.contexts}
    checks = [r for r in run.results if r.kind == "color_check"]
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                      autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)
    html = env.get_template("report.html.j2").render(
        run=run, product=product, cols=cols, labels=labels, by_ctx=by_ctx, checks=checks, cards=cards,
        status=Counter(r.status for r in run.results), n_warn=sum(len(r.warnings) for r in run.results),
        n_warned=sum(1 for r in run.results if r.warnings),
        price_rows=_price_rows(run, product, cols), key_spec_rows=_key_spec_rows(run, product, cols),
        menu_rows=_menu_rows(run, product, cols), colors=list(product.colors),
        sec_labels={s.id: s.label_ko for s in product.sections},
    )
    out = run_dir / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


def build_index(out_root: Path) -> Path:
    """out_root/index.html: the latest run of every product with its status counts and report link."""
    out_root = Path(out_root)
    items = []
    for product_dir in sorted(p for p in out_root.iterdir() if p.is_dir()):
        runs = sorted(d for d in product_dir.iterdir() if (d / "data.json").exists())
        if not runs:
            continue
        run = RunData.from_json(runs[-1] / "data.json")
        items.append({"title": run.title, "product": product_dir.name, "run": runs[-1].name,
                      "captured_at": run.captured_at, "status": Counter(r.status for r in run.results),
                      "n": len(run.results), "contexts": [c.label for c in run.contexts],
                      "report": f"{product_dir.name}/{runs[-1].name}/report.html",
                      "has_report": (runs[-1] / "report.html").exists()})
    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                      autoescape=select_autoescape(["html", "j2"]), trim_blocks=True, lstrip_blocks=True)
    out = out_root / "index.html"
    out.write_text(env.get_template("index.html.j2").render(items=items), encoding="utf-8")
    return out
