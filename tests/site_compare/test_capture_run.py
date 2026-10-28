"""run_capture tests live apart from test_capture.py: its module-scoped browser would nest sync_playwright."""
from tools.site_compare import capture
from tools.site_compare.capture import run_capture
from tools.site_compare.model import RunData

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
