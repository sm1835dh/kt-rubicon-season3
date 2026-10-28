"""run_capture tests live apart from test_capture.py: its module-scoped browser would nest sync_playwright."""
from tools.site_compare import capture
from tools.site_compare.capture import run_capture
from tools.site_compare.model import Product, RunData

from .test_capture import WAIT, FakeDriver, _product


def test_run_capture_writes_data_json(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "get_driver", lambda name: FakeDriver())
    product = _product(n_contexts=2)
    run_dir = run_capture(product, tmp_path, only=None, headed=False, wait_ms=WAIT)
    run = RunData.from_json(run_dir / "data.json")
    assert len(run.results) == 6
    assert {r.context_id for r in run.results} == {"c0", "c1"}
    assert run.wait_ms == WAIT and run.viewport == [1440, 1000]


def test_run_capture_only_filters_contexts(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "get_driver", lambda name: FakeDriver())
    run_dir = run_capture(_product(n_contexts=2), tmp_path, only={"c1"}, headed=False, wait_ms=WAIT)
    assert {r.context_id for r in RunData.from_json(run_dir / "data.json").results} == {"c1"}


class FreshDriver(FakeDriver):
    fresh_page_per_combo = True

    def __init__(self):
        self.prepared = 0

    def prepare(self, page, ctx):
        self.prepared += 1
        return []


def test_fresh_page_per_combo_reloads_and_prepares_each_combo(tmp_path, monkeypatch):
    driver = FreshDriver()
    monkeypatch.setattr(capture, "get_driver", lambda name: driver)
    run_capture(_product(n_contexts=1), tmp_path, only=None, headed=False, wait_ms=WAIT)
    assert driver.prepared == 3  # one per combo (3 storages), not one per context


def test_reused_page_prepares_once_per_context(tmp_path, monkeypatch):
    driver = FreshDriver()
    driver.fresh_page_per_combo = False
    monkeypatch.setattr(capture, "get_driver", lambda name: driver)
    run_capture(_product(n_contexts=1), tmp_path, only=None, headed=False, wait_ms=WAIT)
    assert driver.prepared == 1


def test_run_capture_into_replaces_only_recaptured_contexts(tmp_path, monkeypatch):
    monkeypatch.setattr(capture, "get_driver", lambda name: FakeDriver())
    product = _product(n_contexts=3)
    run_dir = run_capture(product, tmp_path, only=None, headed=False, wait_ms=WAIT)
    old = RunData.from_json(run_dir / "data.json")
    for r in old.results:
        r.warnings = ["old"]
    old.to_json(run_dir / "data.json")
    again = run_capture(product, tmp_path, only={"c1"}, headed=False, wait_ms=WAIT, into=run_dir)
    run = RunData.from_json(again / "data.json")
    assert again == run_dir and len(run.results) == 9
    assert [r.context_id for r in run.results] == ["c0"] * 3 + ["c1"] * 3 + ["c2"] * 3  # context order kept
    assert all(("old" in r.warnings) == (r.context_id != "c1") for r in run.results)


def test_cli_into_resolves_latest_run(tmp_path, monkeypatch):
    from tools.site_compare import __main__ as cli
    seen = {}

    def fake_run(product, out_root, only, headed, wait_ms, into=None):
        seen.update(only=only, into=into)
        return into

    for name in ("20261029-051930", "20261029-060304"):
        (tmp_path / "tv_s95h" / name).mkdir(parents=True)
        (tmp_path / "tv_s95h" / name / "data.json").write_text("{}")
    monkeypatch.setattr(cli, "OUT_ROOT", tmp_path)
    monkeypatch.setattr(capture, "run_capture", fake_run)
    monkeypatch.setattr(cli, "_build", lambda product, run_dir: None)
    cli.main(["capture", "tv_s95h", "--only", "ca-fr-on", "--into", "latest"])
    assert seen == {"only": {"ca-fr-on"}, "into": tmp_path / "tv_s95h" / "20261029-060304"}


def _discover_product(tmp_path, spec_url=None, second_driver="pd"):
    from tools.site_compare.model import Context
    from .test_discover import FIXTURE, RULES
    c0 = Context("c0", "C0", "pd", FIXTURE, "en-GB", "GBP", ref_sku="P65B", spec_url=spec_url, spec_driver="pd")
    c1 = Context("c1", "C1", second_driver, FIXTURE, "en-GB", "GBP", ref_sku="P65B")
    return Product("fake", "Fake", [c0, c1], sections=RULES, mode="discover", axes=[])


def test_spec_page_failure_is_a_warning_not_an_abort(tmp_path, monkeypatch):
    from .test_discover import FakePdpDriver, WAIT as DWAIT
    svg = tmp_path / "spec.svg"  # a document without <body>: scrolling it throws inside the page
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>')
    monkeypatch.setattr(capture, "get_driver", lambda name: FakePdpDriver())
    run_dir = run_capture(_discover_product(tmp_path, spec_url=svg.as_uri()), tmp_path / "out", None, False, DWAIT)
    run = RunData.from_json(run_dir / "data.json")
    c0 = next(r for r in run.results if r.context_id == "c0")
    assert any(w.startswith("spec page failed") for w in c0.warnings), c0.warnings
    assert {r.context_id for r in run.results} == {"c0", "c1"}


def test_context_failure_keeps_the_run_going(tmp_path, monkeypatch):
    from .test_discover import FakePdpDriver, WAIT as DWAIT

    def drivers(name):
        if name == "broken":
            raise KeyError(name)
        return FakePdpDriver()

    monkeypatch.setattr(capture, "get_driver", drivers)
    run_dir = run_capture(_discover_product(tmp_path, second_driver="broken"), tmp_path / "out", None, False, DWAIT)
    run = RunData.from_json(run_dir / "data.json")
    c1 = [r for r in run.results if r.context_id == "c1"]
    assert len(c1) == 1 and c1[0].status == "error" and "KeyError" in c1[0].warnings[0]
    assert any(r.context_id == "c0" and r.status == "ok" for r in run.results)
