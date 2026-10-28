"""CLI: python -m tools.site_compare capture|build <product> ..."""
from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_product

HERE = Path(__file__).parent
OUT_ROOT = Path("out/site_compare")


def _product_path(name: str) -> Path:
    return HERE / "products" / f"{name}.yaml"


def _resolve_run(product_id: str, run: str) -> Path:
    root = OUT_ROOT / product_id
    if run != "latest":
        return root / run
    runs = sorted(d for d in root.iterdir() if (d / "data.json").exists())
    if not runs:
        raise SystemExit(f"no runs under {root}")
    return runs[-1]


def _build(product, run_dir: Path) -> None:
    from .report import build_index, build_report
    out = build_report(run_dir, product, HERE / "cards" / f"{product.id}.yaml")
    print(f"index: {build_index(OUT_ROOT).resolve()}")
    print(out.resolve())


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m tools.site_compare")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture", help="capture all combos, then build the report")
    c.add_argument("product")
    c.add_argument("--only", help="comma-separated context ids")
    c.add_argument("--headed", action="store_true", help="show the browser (use when bot-blocked)")
    c.add_argument("--wait-ms", type=int, default=5000)
    b = sub.add_parser("build", help="rebuild report.html from a captured run")
    b.add_argument("product")
    b.add_argument("--run", default="latest")
    s = sub.add_parser("snapshot", help="save trimmed DOM fixtures + expected driver output for offline tests")
    s.add_argument("product")
    s.add_argument("--only", help="comma-separated context ids")
    s.add_argument("--wait-ms", type=int, default=5000)
    args = ap.parse_args(argv)

    product = load_product(_product_path(args.product))
    if args.cmd == "capture":
        from .capture import run_capture
        only = set(args.only.split(",")) if args.only else None
        run_dir = run_capture(product, OUT_ROOT, only, args.headed, args.wait_ms)
        print(f"data: {(run_dir / 'data.json').resolve()}")
        _build(product, run_dir)
    elif args.cmd == "snapshot":
        from .snapshot import snapshot_product
        snapshot_product(product, set(args.only.split(",")) if args.only else None, args.wait_ms)
    else:
        _build(product, _resolve_run(product.id, args.run))


if __name__ == "__main__":
    main()
