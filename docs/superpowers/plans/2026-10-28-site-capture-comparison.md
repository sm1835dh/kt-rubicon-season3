# 국가별 Samsung.com 화면 비교 캡쳐 도구 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 국가·지역·옵션 조합별로 samsung.com 구매 페이지를 실제 렌더링해서 캡쳐하고, 차이점 카드 중심의 로컬 HTML 리포트를 만드는 재사용 도구를 만든다. 1차 대상은 Galaxy Z Fold8 Ultra다.

**Architecture:** 상품은 YAML 설정 하나로 정의하고, 조합 펼치기와 가격 파싱은 순수 함수로 만든다. 사이트별 동작은 `SiteDriver` 구현체가 맡는다(hubble = UK/CA/CA-FR, us = US). 캡쳐 오케스트레이터는 드라이버로 조합을 선택하고 검증한 뒤 스크린샷과 값을 `data.json`에 기록한다. 리포트 빌더는 `data.json`과 카드 메모 YAML을 합쳐 `report.html`을 만든다.

**Tech Stack:** Python 3.12 (uv venv `.venv`), Playwright 1.64 (`channel="chrome"`, 설치된 Google Chrome 사용), PyYAML, Jinja2, pytest

**Spec:** `docs/superpowers/specs/2026-10-28-site-capture-comparison-design.md`

## Global Constraints

- 대기: 페이지 로드 후 5초, 옵션 클릭 후 5초. `wait_ms` 기본값은 `5000`이고 테스트에서만 줄인다.
- 화면 크기: viewport `1440 x 1000`, 전체 페이지 캡쳐.
- 쿠키 배너는 거부·필수만 계열 버튼을 우선 누른다. UK·CA·CA-FR은 `#truste-consent-required`, US는 `.truste-banner-close`.
- 구매를 진행하지 않는다. Continue, Add to cart, 트레이드인 "Yes", 로그인, ID.me 버튼은 절대 클릭하지 않는다.
- 고정 색상은 `Graphite`다. 색상별 가격 확인은 `256GB`에서만 한다.
- US 통신사는 `Unlocked`, `Verizon` 두 가지이고, Verizon 하위 선택은 페이지 기본값으로 둔다.
- CA 주는 `CA-ON`, `CA-QC`다.
- 기준 가격(`base`)은 추가 옵션 없는 기기 일시불 가격이다. headline, 월 할부, 정가(was)는 따로 기록한다.
- 결과물은 `out/site_compare/<product>/<run_id>/`에 둔다(git 제외). `run_id`는 `YYYYmmdd-HHMMSS`(KST).
- 리포트는 한국어로 쓰고, 외부 CDN 없이 오프라인으로 열려야 한다. 관찰 문구에는 [사실]/[추정] 표기를 쓴다.
- 실행 명령은 저장소 루트에서 `.venv/bin/python -m tools.site_compare …` 형식이다.

## Review Focus

1. 옵션 조합이 존재하지 않는 경우(예: US Verizon + Green Shadow, CA 1TB Cream): 실행이 멈추지 않고 해당 조합을 `unavailable`로 기록하고 캡쳐를 남겨야 한다. → Task 3 `test_unavailable_option_recorded`
2. 5초 뒤에도 가격이 렌더링되지 않은 경우: 1회 재대기하고, 그래도 없으면 경고를 남겨야 한다. 빈 가격을 정상으로 처리하면 안 된다. → Task 3 `test_price_retry_then_warning`
3. 클릭 후 선택 상태가 의도와 다른 경우(라벨은 512GB인데 화면은 256GB): `mismatch` 상태와 경고로 남겨야 한다. → Task 3 `test_selection_mismatch_flagged`
4. CA 주 설정이 적용되지 않은 경우: `region` 불일치 경고를 남겨야 한다. → Task 3 `test_region_mismatch_warning`
5. 재실행 후 카드가 참조하는 조합·섹션·강조 텍스트가 없어진 경우: 리포트는 그대로 만들어지고, 해당 카드에 경고 배지가 붙어야 한다. → Task 4 `test_card_with_missing_refs_shows_warning`

---

## 파일 구조

```
.gitignore                         # .venv/, out/, .superpowers/, __pycache__/
requirements.txt                   # playwright, pyyaml, jinja2, pytest
pytest.ini                         # testpaths=tests, pythonpath=., markers: live
tools/__init__.py
tools/site_compare/__init__.py
tools/site_compare/__main__.py     # CLI: capture / build
tools/site_compare/model.py        # 데이터클래스 + JSON 직렬화
tools/site_compare/config.py       # 상품 YAML 로딩, 조합 펼치기, 섹션 매핑
tools/site_compare/prices.py       # 금액 토큰·파싱, JSON-LD offers 추출, 비교
tools/site_compare/capture.py      # 오케스트레이터 (드라이버 사용, 스크린샷, data.json)
tools/site_compare/sites/__init__.py   # get_driver(name)
tools/site_compare/sites/base.py   # SiteDriver Protocol, OptionUnavailable, Box
tools/site_compare/sites/hubble.py # UK/CA/CA-FR
tools/site_compare/sites/us.py     # US
tools/site_compare/report.py       # 카드 로딩·해석, report.html 생성
tools/site_compare/templates/report.html.j2
tools/site_compare/products/fold8_ultra.yaml
tools/site_compare/cards/fold8_ultra.yaml
tools/site_compare/README.md
tests/site_compare/test_config.py
tests/site_compare/test_prices.py
tests/site_compare/test_capture.py      # 로컬 fixture 페이지 + FakeDriver
tests/site_compare/test_report.py
tests/site_compare/test_live.py         # @pytest.mark.live, 실제 사이트
tests/site_compare/fixtures/fake_buy.html
```

---

### Task 1: 골격, 데이터 모델, 상품 설정, 조합 펼치기

**Files:**
- Create: `.gitignore`, `requirements.txt`, `pytest.ini`, `tools/__init__.py`, `tools/site_compare/__init__.py`, `tools/site_compare/model.py`, `tools/site_compare/config.py`, `tools/site_compare/products/fold8_ultra.yaml`
- Test: `tests/site_compare/test_config.py`

**Interfaces:**
- Produces (`model.py`, 전부 `@dataclass`):
  - `Context(id: str, label: str, driver: str, url: str, locale: str, currency: str, region: str | None = None)`
  - `Combo(id: str, context_id: str, kind: str, want: dict[str, str])`. `kind`은 `"main"` 또는 `"color_check"`, `want`의 키는 `storage`, `color`, (US만) `carrier`.
  - `SectionRule(id: str, label_ko: str, patterns: list[str])`
  - `Product(id: str, title: str, contexts: list[Context], storages: list[str], colors: dict[str, str], fixed_color: str, carriers: list[str], sections: list[SectionRule])`. `colors`는 색상명 → SKU 색상코드다.
  - `PriceTexts(base: str | None, monthly: str | None, headline: str | None, was: str | None)`
  - `State(storage: str | None, color: str | None, carrier: str | None, region: str | None, sku: str | None, prices: PriceTexts)`
  - `Money(value: float, currency: str)`, `Offer(sku: str, price: float, currency: str, strike: float | None)`
  - `TextBox(text: str, x: float, y: float, w: float, h: float)`. 좌표는 해당 스크린샷 기준 px다.
  - `Shot(title: str, section_id: str | None, order: int, path: str, width: int, height: int, texts: list[TextBox])`
  - `ComboResult(combo_id: str, context_id: str, kind: str, want: dict[str, str], got: State | None, url_final: str | None, status: str, base: Money | None, jsonld: Offer | None, price_match: bool | None, sections: list[Shot], extras: list[Shot], full_shot: str | None, warnings: list[str], captured_at: str)`. `status`는 `ok`, `unavailable`, `mismatch`, `error` 중 하나다.
  - `RunData(product_id: str, title: str, run_id: str, captured_at: str, viewport: list[int], wait_ms: int, contexts: list[Context], results: list[ComboResult])`
  - `RunData.to_json(path: Path) -> None`, `RunData.from_json(path: Path) -> RunData`
- Produces (`config.py`):
  - `load_product(path: Path) -> Product`. 알 수 없는 driver, 중복 context id, `fixed_color`가 `colors`에 없으면 `ValueError`.
  - `expand_combos(product: Product) -> list[Combo]`
  - `map_section(title: str, rules: list[SectionRule]) -> str | None`. 공백을 정리하고 대소문자를 무시한 regex `search`로 비교하고, 첫 번째로 맞는 규칙을 반환한다.
  - `slug(s: str) -> str`. 예: `"256GB"→"256gb"`, `"Violet Shadow"→"violet-shadow"`, `"1TB"→"1tb"`.

- [ ] **Step 1: 골격 파일 작성**

  - `requirements.txt`: `playwright==1.64.1`, `pyyaml==6.0.3`, `jinja2`, `pytest==9.2.0`
  - `pytest.ini`: `testpaths = tests`, `pythonpath = .`, `markers = live: hits real samsung.com`, `addopts = -m "not live"`
  - `.gitignore`: `.venv/`, `out/`, `.superpowers/`, `__pycache__/`
  - 실행: `uv pip install --python .venv/bin/python -r requirements.txt`

- [ ] **Step 2: `products/fold8_ultra.yaml` 작성** (값은 spec 3장 그대로)

```yaml
id: fold8_ultra
title: Galaxy Z Fold8 Ultra
storages: [256GB, 512GB, 1TB]
colors: {Graphite: ZK, Violet Shadow: ZV, Cream: ZW, Green Shadow: DG}
fixed_color: Graphite
carriers: [Unlocked, Verizon]        # driver == us 인 컨텍스트에만 적용
contexts:
  - {id: uk,       label: "UK",               driver: hubble, locale: en-GB, currency: GBP, url: "https://www.samsung.com/uk/smartphones/galaxy-z-fold8-ultra/buy/"}
  - {id: ca-en-on, label: "CA-EN · Ontario",  driver: hubble, locale: en-CA, currency: CAD, region: CA-ON, url: "https://www.samsung.com/ca/smartphones/galaxy-z-fold8-ultra/buy/"}
  - {id: ca-en-qc, label: "CA-EN · Quebec",   driver: hubble, locale: en-CA, currency: CAD, region: CA-QC, url: "https://www.samsung.com/ca/smartphones/galaxy-z-fold8-ultra/buy/"}
  - {id: ca-fr-on, label: "CA-FR · Ontario",  driver: hubble, locale: fr-CA, currency: CAD, region: CA-ON, url: "https://www.samsung.com/ca_fr/smartphones/galaxy-z-fold8-ultra/buy/"}
  - {id: ca-fr-qc, label: "CA-FR · Québec",   driver: hubble, locale: fr-CA, currency: CAD, region: CA-QC, url: "https://www.samsung.com/ca_fr/smartphones/galaxy-z-fold8-ultra/buy/"}
  - {id: us,       label: "US",               driver: us,     locale: en-US, currency: USD, url: "https://www.samsung.com/us/smartphones/galaxy-z-fold8-ultra/buy/"}
sections:   # 순서 = 우선순위
  - {id: device,          label_ko: 기기,            patterns: ["^device$", "^appareil$"]}
  - {id: storage,         label_ko: 용량,            patterns: ["^storage$", "^stockage$"]}
  - {id: color,           label_ko: 색상,            patterns: ["^colou?r$", "^couleur$"]}
  - {id: connectivity,    label_ko: 통신사,          patterns: ["^connectivity$"]}
  - {id: trade_in,        label_ko: 트레이드인,      patterns: ["trade-?in"]}
  - {id: upgrade_program, label_ko: 연간 업그레이드, patterns: ["annual upgrade", "mise à niveau"]}
  - {id: carrier_plans,   label_ko: 통신사 요금제,   patterns: ["pay monthly phone contracts"]}
  - {id: care,            label_ko: Care+,           patterns: ["care\\+"]}
  - {id: gifts,           label_ko: 사은품·할인,     patterns: ["gifts and savings", "cadeaux et économies"]}
  - {id: bundle,          label_ko: 번들 할인,       patterns: ["healthy habits", "achat groupé"]}
  - {id: buy_direct,      label_ko: 직접 구매 혜택,  patterns: ["buy direct", "achetez directement"]}
  - {id: purchase_option, label_ko: 결제 방식,       patterns: ["purchase option"]}
  - {id: price_bar,       label_ko: 상단 가격 바,    patterns: ["^price bar$"]}   # 드라이버가 붙이는 고정 제목
  - {id: summary,         label_ko: 주문 요약,       patterns: ["^summary$"]}     # 드라이버가 붙이는 고정 제목
```

- [ ] **Step 3: 실패하는 테스트 작성** (`tests/site_compare/test_config.py`)

```python
from pathlib import Path
import pytest
from tools.site_compare.config import load_product, expand_combos, map_section, slug

P = Path("tools/site_compare/products/fold8_ultra.yaml")

def test_load_product_fold8():
    p = load_product(P)
    assert [c.id for c in p.contexts] == ["uk", "ca-en-on", "ca-en-qc", "ca-fr-on", "ca-fr-qc", "us"]
    assert p.contexts[2].region == "CA-QC"
    assert p.contexts[5].driver == "us"
    assert p.fixed_color == "Graphite" and p.colors["Graphite"] == "ZK"

def test_load_product_rejects_unknown_driver(tmp_path):
    bad = P.read_text().replace("driver: us,", "driver: foo,")
    f = tmp_path / "bad.yaml"; f.write_text(bad)
    with pytest.raises(ValueError):
        load_product(f)

def test_expand_main_combos():
    main = [c for c in expand_combos(load_product(P)) if c.kind == "main"]
    assert len(main) == 21
    ids = {c.id for c in main}
    assert {"uk__256gb", "ca-fr-qc__1tb", "us__1tb__verizon", "us__256gb__unlocked"} <= ids
    us512 = next(c for c in main if c.id == "us__512gb__unlocked")
    assert us512.want == {"storage": "512GB", "color": "Graphite", "carrier": "Unlocked"}
    assert next(c for c in main if c.id == "uk__256gb").want == {"storage": "256GB", "color": "Graphite"}

def test_expand_color_checks():
    cc = [c for c in expand_combos(load_product(P)) if c.kind == "color_check"]
    assert len(cc) == 18                      # 6 contexts × 3 non-fixed colors
    c = next(c for c in cc if c.id == "us__256gb__color-cream")
    assert c.want == {"storage": "256GB", "color": "Cream", "carrier": "Unlocked"}
    assert not any(c.want["color"] == "Graphite" for c in cc)

@pytest.mark.parametrize("title,expected", [
    ("Samsung Trade-In", "trade_in"), ("Trade-in", "trade_in"), ("Couleur", "color"), ("Colour", "color"),
    ("Save more, upgrade sooner with the Annual Upgrade Program", "upgrade_program"),
    ("Économisez plus, mettez-vous à niveau plus tôt avec le programme de mise à niveau annuelle", "upgrade_program"),
    ("Samsung  Care+", "care"), ("Something new", None),
])
def test_map_section(title, expected):
    assert map_section(title, load_product(P).sections) == expected

def test_slug():
    assert [slug(s) for s in ["256GB", "Violet Shadow", "1TB"]] == ["256gb", "violet-shadow", "1tb"]
```

- [ ] **Step 4: 실패 확인** — `.venv/bin/pytest tests/site_compare/test_config.py -q` → `ModuleNotFoundError` 또는 ImportError로 FAIL

- [ ] **Step 5: `model.py`, `config.py` 구현**
  - 조합 id 규칙:
    - main: `"{ctx}__{slug(storage)}"`. US는 뒤에 `"__{slug(carrier)}"`를 붙인다.
    - color_check: `"{ctx}__{slug(storages[0])}__color-{slug(color)}"`. US carrier는 `carriers[0]`이다.
  - 순서: context 순서 → storage 순서 → carrier 순서. color_check는 main 뒤에 둔다.
  - `RunData.from_json`은 중첩 데이터클래스를 직접 복원한다(외부 라이브러리 없이).

- [ ] **Step 6: 통과 확인** — `.venv/bin/pytest tests/site_compare/test_config.py -q` → 전부 PASS. 직렬화 왕복은 `RunData` 샘플을 `to_json` → `from_json`해서 `==`로 확인하는 테스트 `test_rundata_roundtrip`을 같은 파일에 추가하고 PASS를 확인한다.

- [ ] **Step 7: 커밋** — `git add .gitignore requirements.txt pytest.ini tools tests && git commit -m "feat(site_compare): product config, data model, combo expansion"`

---

### Task 2: 가격 파싱과 JSON-LD offers

**Files:**
- Create: `tools/site_compare/prices.py`
- Test: `tests/site_compare/test_prices.py`

**Interfaces:**
- Consumes: `Money`, `Offer` (Task 1)
- Produces:
  - `money_tokens(text: str, locale: str) -> list[str]`: 텍스트 안의 금액 문자열을 등장 순서대로 반환한다.
  - `parse_money(token: str | None, locale: str, currency: str) -> Money | None`: 로캘이 `fr`로 시작하면 쉼표가 소수점이고, 공백·NBSP·좁은 NBSP는 천 단위 구분자다.
  - `extract_offers(html: str) -> dict[str, Offer]`: 키는 대문자 SKU다. `ProductGroup.hasVariant[*].offers`와 `Product.offers`(+ `priceSpecification.priceType` StrikethroughPrice → `strike`)를 읽는다.
  - `price_matches(base: Money | None, offer: Offer | None) -> bool | None`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
import json
from tools.site_compare.prices import money_tokens, parse_money, extract_offers, price_matches
from tools.site_compare.model import Money, Offer

def test_money_tokens_uk_label():
    assert money_tokens("256GB｜12GB £52.75/mo. or £1,899.00", "en-GB") == ["£52.75", "£1,899.00"]

def test_money_tokens_ca_fr_label():
    assert money_tokens("À partir de 75,00 $ /mo.‡ ou 2 699,99 $", "fr-CA") == ["75,00 $", "2 699,99 $"]

def test_money_tokens_us_was():
    assert money_tokens("was: $2099.99 $1,899.99", "en-US") == ["$2099.99", "$1,899.99"]

def test_parse_money():
    assert parse_money("£1,899.00", "en-GB", "GBP") == Money(1899.0, "GBP")
    assert parse_money("2 699,99 $", "fr-CA", "CAD") == Money(2699.99, "CAD")
    assert parse_money("$2099.99", "en-US", "USD") == Money(2099.99, "USD")
    assert parse_money("", "en-US", "USD") is None and parse_money(None, "en-US", "USD") is None

def _ld(obj):
    return f'<script type="application/ld+json">{json.dumps(obj)}</script>'

def test_extract_offers_product_group():
    html = _ld({"@type": "ProductGroup", "hasVariant": [
        {"sku": "SM-F976BZKBEUB", "offers": {"price": "1899", "priceCurrency": "GBP"}}]})
    assert extract_offers(html)["SM-F976BZKBEUB"] == Offer("SM-F976BZKBEUB", 1899.0, "GBP", None)

def test_extract_offers_us_strike():
    html = _ld({"@type": "Product", "sku": "SM-F976UDGAXAA", "offers": {"price": "1899.99", "priceCurrency": "USD",
        "priceSpecification": {"@type": "UnitPriceSpecification", "priceType": "https://schema.org/StrikethroughPrice", "price": 2099.99}}})
    assert extract_offers(html)["SM-F976UDGAXAA"] == Offer("SM-F976UDGAXAA", 1899.99, "USD", 2099.99)

def test_extract_offers_ignores_broken_json():
    assert extract_offers('<script type="application/ld+json">{oops</script>') == {}

def test_price_matches():
    assert price_matches(Money(1899.99, "USD"), Offer("X", 1899.99, "USD", None)) is True
    assert price_matches(Money(1899.0, "USD"), Offer("X", 1899.99, "USD", None)) is False
    assert price_matches(None, Offer("X", 1.0, "USD", None)) is None
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest tests/site_compare/test_prices.py -q` → FAIL (ImportError)
- [ ] **Step 3: `prices.py` 구현.** 금액 regex는 통화 기호(£, $, €)를 앞이나 뒤에 붙인 숫자 그룹이다. 천 단위 구분자는 `,` / 공백 / ` ` / ` `를 허용한다. JSON-LD는 `<script type="application/ld+json">`를 regex로 찾아 `json.loads`하고, 리스트·`@graph`도 순회한다.
- [ ] **Step 4: 통과 확인** — `.venv/bin/pytest tests/site_compare/test_prices.py -q` → PASS
- [ ] **Step 5: 커밋** — `git commit -am "feat(site_compare): money parsing and JSON-LD offers"` (새 파일은 `git add`)

---

### Task 3: 캡쳐 오케스트레이터, 드라이버 인터페이스, CLI

**Files:**
- Create: `tools/site_compare/sites/__init__.py`, `tools/site_compare/sites/base.py`, `tools/site_compare/capture.py`, `tools/site_compare/__main__.py`
- Test: `tests/site_compare/test_capture.py`, `tests/site_compare/fixtures/fake_buy.html`

**Interfaces:**
- Consumes: Task 1 모델·`expand_combos`·`map_section`·`slug`, Task 2 `parse_money`·`extract_offers`·`price_matches`
- Produces (`sites/base.py`):
  - `Box = tuple[float, float, float, float]` (페이지 좌표 x, y, w, h)
  - `class OptionUnavailable(Exception)`
  - `class SiteDriver(Protocol)`:
    - `prepare(self, page, ctx: Context) -> list[str]`: 배너 닫기, 지역 설정. 경고 목록을 반환한다.
    - `select(self, page, axis: str, value: str, product: Product) -> None`: 클릭한다. 고를 수 없으면 `OptionUnavailable`을 던진다.
    - `read_state(self, page, ctx: Context, product: Product) -> State`
    - `section_boxes(self, page) -> list[tuple[str, Box]]`: 구매 단계 섹션 (제목, 영역)을 페이지 순서대로 반환한다. 상단 고정 가격 바는 제목 `"Price bar"`, 주문 요약·장바구니 영역은 `"Summary"`라는 고정 제목으로 함께 반환한다(spec 3.3의 가격 영역 캡쳐).
    - `extra_shots(self, page) -> list[tuple[str, Box]]`: 레이어·팝업을 열고 영역을 반환한다. 오케스트레이터가 찍은 뒤 `close_extras(page)`를 호출한다.
    - `close_extras(self, page) -> None`
  - `get_driver(name: str) -> SiteDriver` (`sites/__init__.py`). `"hubble"`과 `"us"`이고, Task 5·6 전에는 `NotImplementedError` 스텁이다.
- Produces (`capture.py`):
  - `capture_combo(page, driver, product, ctx, combo, run_dir: Path, wait_ms: int, with_extras: bool) -> ComboResult`
  - `capture_context(browser, driver, product, ctx, combos: list[Combo], run_dir: Path, wait_ms: int) -> list[ComboResult]`: 컨텍스트당 페이지를 1번 열고 `prepare`한 뒤, 조합마다 옵션만 다시 선택한다. `with_extras`는 컨텍스트의 첫 main 조합에서만 `True`다.
  - `run_capture(product, out_root: Path, only: set[str] | None, headed: bool, wait_ms: int) -> Path`: `run_dir`을 반환하고 `data.json`을 기록한다.
  - `collect_text_boxes(page, box: Box) -> list[TextBox]`: 영역 안의 보이는 짧은 텍스트(줄바꿈 없음, 80자 이하) 요소와 그 좌표를 반환한다. 좌표는 영역 기준이다.
- Produces (`__main__.py`): `python -m tools.site_compare capture <product> [--only ctx,ctx] [--headed] [--wait-ms N]`. 캡쳐가 끝나면 build까지 실행한다. `build <product> [--run latest|<run_id>]`. 둘 다 마지막 줄에 `report.html`의 절대 경로를 출력한다.

`capture_combo` 규칙 (spec 4장):
1. `want`를 `storage → color → carrier` 순서로 `select`하고, 클릭할 때마다 `wait_ms`만큼 대기한다. `OptionUnavailable`이 나면 `status="unavailable"`로 하고 경고를 기록한다. 그래도 전체 캡쳐는 찍고 다음 조합으로 넘어간다.
2. `read_state`로 가격을 읽는다. `prices.base`에 금액 토큰이 없으면 `wait_ms`만큼 더 기다리고 다시 읽는다. 그래도 없으면 경고 `"price not rendered"`를 기록한다.
3. `want`의 각 축을 `got`과 비교한다(정규화: 소문자, 공백 제거, `｜` 앞부분만). 다르면 `status="mismatch"`이고 경고 `"selection mismatch: storage want=512GB got=256GB"` 형식으로 기록한다.
4. `ctx.region`이 있는데 `got.region` 정규화 값이 다르면 경고 `"region mismatch: want=CA-QC got=..."`를 기록한다. 비교 시 `CA-QC`는 `Quebec`/`Québec`와 같은 값으로 본다.
5. 섹션: `section_boxes` → `map_section`, 섹션별 클립 스크린샷(`page.screenshot(clip=..., full_page=True)`)과 `collect_text_boxes`. 섹션이 0개면 경고를 기록한다.
6. 전체 페이지 스크린샷, `page.url`, `extract_offers(page.content())[got.sku]`, `parse_money(prices.base)`, `price_matches`를 기록한다.
7. 예외가 나면 `status="error"`로 하고, 경고에 예외 메시지를 넣고, 가능하면 전체 캡쳐를 남긴다. 실행은 계속한다.
8. 최종 URL이 `https://www.samsung.com/{ctx.url의 첫 경로 세그먼트}/`로 시작하지 않으면 경고 `"redirected: <url>"`를 기록한다. 다른 국가 사이트로 넘어간 경우가 여기에 해당하고, US의 SKU URL 변경은 정상이다.
- 파일명은 `shots/{combo_id}__full.png`, `shots/{combo_id}__{order:02d}-{slug(title)[:40]}.png`, `shots/{combo_id}__extra-{n}.png`이다.

`fixtures/fake_buy.html`: hubble을 흉내 낸 작은 정적 페이지다.
- `<h2 class="t">Storage</h2>`, `Colour`, `Trade-in` 섹션이 있다.
- 용량 라디오 3개가 있고, `1TB`는 `data-unavailable`이다.
- 선택하면 300ms 뒤 `#price`에 `£1,899.00` 같은 값이 들어간다. `?noprice=1`이면 가격을 넣지 않는다.
- `?stuck=1`이면 클릭해도 선택이 바뀌지 않는다.
- `#region`에 `?region=` 값을 표시한다.
- JSON-LD `ProductGroup`에 SKU 3개가 있다.

테스트 안의 `FakeDriver`가 이 페이지를 조작한다.

- [ ] **Step 1: fixture와 실패하는 테스트 작성** (`wait_ms=50`, URL은 `file://` 절대 경로)

```python
def test_capture_ok_records_prices_sections_and_jsonld(tmp_path): ...
    # r.status == "ok"; r.got.storage == "256GB"; r.base == Money(1899.0, "GBP")
    # r.jsonld.price == 1899.0 and r.price_match is True
    # [s.section_id for s in r.sections] == ["storage", "color", "trade_in"]
    # (tmp_path / r.full_shot).exists() and all((tmp_path / s.path).exists() for s in r.sections)
    # any(t.text == "£1,899.00" for s in r.sections for t in s.texts)

def test_unavailable_option_recorded(tmp_path): ...
    # want storage=1TB → r.status == "unavailable"; r.full_shot is not None; 실행이 예외 없이 끝남

def test_price_retry_then_warning(tmp_path): ...
    # ?noprice=1 → "price not rendered" in r.warnings; r.base is None; r.price_match is None

def test_selection_mismatch_flagged(tmp_path): ...
    # ?stuck=1, want 512GB → r.status == "mismatch"; any(w.startswith("selection mismatch: storage") for w in r.warnings)

def test_region_mismatch_warning(tmp_path): ...
    # ctx.region="CA-QC", 페이지 region=Ontario → any(w.startswith("region mismatch") for w in r.warnings)

def test_run_capture_writes_data_json(tmp_path, monkeypatch): ...
    # get_driver를 FakeDriver로 바꾼 뒤 2개 컨텍스트 → RunData.from_json(run_dir/"data.json").results 길이 == 조합 수
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest tests/site_compare/test_capture.py -q` → FAIL
- [ ] **Step 3: `sites/base.py`, `sites/__init__.py`, `capture.py`, `__main__.py` 구현.** 브라우저는 `chromium.launch(channel="chrome", headless=not headed)`, context는 `viewport={"width":1440,"height":1000}`. 전체 캡쳐 전에 800px씩 끝까지 스크롤해서 지연 로딩을 풀고 맨 위로 돌아온다. `captured_at`은 KST ISO 문자열이다.
- [ ] **Step 4: 통과 확인** — `.venv/bin/pytest tests/site_compare/test_capture.py -q` → PASS
- [ ] **Step 5: 커밋** — `git add tools tests && git commit -m "feat(site_compare): capture orchestrator, driver protocol, CLI"`

---

### Task 4: 리포트 생성 (A안 + 요약 가격표)

**Files:**
- Create: `tools/site_compare/report.py`, `tools/site_compare/templates/report.html.j2`, `tools/site_compare/cards/fold8_ultra.yaml`(빈 `cards: []`)
- Test: `tests/site_compare/test_report.py`

**Interfaces:**
- Consumes: `RunData.from_json`, `Product`, `load_product`, `map_section`
- Produces:
  - `Panel(combo: str, section: str, highlight: list[str], caption: str | None)`. `section`은 section_id, `"full"`, 또는 `"extra-{n}"`이다.
  - `Card(id: str, title: str, tags: list[str], panels: list[Panel], observation: str, note: str)`. tags 허용값은 `국가별 구성 차이`, `사이트 데이터 오류`, `소스 vs 화면 불일치`, `CA-FR 번역`이다.
  - `load_cards(path: Path) -> list[Card]`
  - `resolve_panel(panel: Panel, run: RunData) -> dict`: 이미지 경로, 크기, 하이라이트 박스(%), 컨텍스트 라벨, URL, got, 경고 목록을 담는다. 강조 텍스트는 해당 Shot의 `texts`에서 공백을 정규화한 뒤 포함 여부로 찾는다. 없으면 경고 `"highlight not found: …"`를 붙인다.
  - `build_report(run_dir: Path, product: Product, cards_path: Path) -> Path`: `run_dir/"report.html"`을 쓴다.

리포트 구성 (spec 5장 순서):
1. 머리말: 제목, `captured_at`, viewport, 캡쳐 규칙 요약(5초 대기, 쿠키 거부, 접힌 영역 펼침, Graphite 고정, US Unlocked·Verizon), 컨텍스트별 URL 표, 상태별 개수(ok, unavailable, mismatch, error), 전체 경고 수.
2. 요약
   - 가격 표: 행은 storage, 열은 컨텍스트이고 US는 `US · Unlocked`, `US · Verizon` 2열이다. 칸에는 `base` 텍스트를 넣는다. `price_match is False`면 `class="diff"`로 빨갛게 하고, `title`에 headline·monthly·was·JSON-LD를 넣는다. 칸을 누르면 `#combo-{id}`로 이동한다.
   - 메뉴 구성 표: 행은 product.sections 순서이고 매핑 안 된 제목은 원문 그대로 행으로 추가한다. 열은 각 컨텍스트의 첫 main 조합이고 US는 Unlocked·Verizon 2열이다. 칸은 `✓ n`(페이지 내 순서) 또는 `—`.
   - 카드 목차: 제목과 태그.
3. 카드: 패널을 가로로 나란히 둔다. 이미지는 `<a href=원본 target=_blank>`로 감싸고, 하이라이트는 `position:absolute` 빨간 테두리 박스(% 좌표)다. 캡션에는 컨텍스트 라벨, URL, 선택 상태를 넣는다. 관찰과 메모는 줄바꿈을 유지하고, 경고가 있으면 카드 상단에 노란 배지를 단다.
4. 부록: 컨텍스트별 조합 카드(`id="combo-{id}"`)를 둔다. 전체 캡쳐 썸네일, 상태, 가격 4종, JSON-LD, 경고를 담고, 섹션·extra 캡쳐는 접어서(`<details>`) 넣는다. 색상 확인(color_check) 표와 `data.json` 링크도 넣는다.
- CSS는 템플릿 안에 인라인으로 넣는다. 라이트·다크 대응(`prefers-color-scheme`), 폭 1200px 이상 기준, 좁은 화면에서는 패널을 세로로 쌓는다.

- [ ] **Step 1: 실패하는 테스트 작성.** fixture `RunData`는 테스트 안에서 만든다(1x1 PNG를 base64로 쓰고, uk·us 2개 컨텍스트, us 하나는 `price_match=False`).

```python
def test_report_has_sections_and_price_table(tmp_path): ...
    # html에 "차이점 카드", "부록", "US · Verizon" 포함; price_match False 칸에 class="diff"
def test_menu_table_marks_missing_section(tmp_path): ...
    # uk에는 trade_in 섹션 있음, us에는 없음 → 해당 행에 "✓" 와 "—" 모두 존재
def test_card_highlight_resolved(tmp_path): ...
    # Panel(highlight=["£1,899.00"]) → resolve_panel(...)["boxes"] 길이 1, 경고 없음
def test_card_with_missing_refs_shows_warning(tmp_path): ...
    # combo 없음 / section 없음 / 텍스트 없음 각각 → 경고 문자열; build_report는 예외 없이 html 생성, html에 "card-warn" 포함
def test_report_has_no_external_urls(tmp_path): ...
    # html에 "<script src=\"http" 와 "<link href=\"http" 없음
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest tests/site_compare/test_report.py -q` → FAIL
- [ ] **Step 3: `report.py`, 템플릿 구현** (Jinja2 `autoescape=True`)
- [ ] **Step 4: 통과 확인** — `.venv/bin/pytest -q` → 전체 PASS (live 제외)
- [ ] **Step 5: 커밋** — `git add tools tests && git commit -m "feat(site_compare): HTML report with difference cards"`

---

### Task 5: hubble 드라이버 (UK / CA-EN / CA-FR)

**Files:**
- Create: `tools/site_compare/sites/hubble.py`
- Modify: `tools/site_compare/sites/__init__.py` (`"hubble"` 연결)
- Test: `tests/site_compare/test_live.py` (`@pytest.mark.live`)

**Interfaces:**
- Consumes: `SiteDriver`, `OptionUnavailable`, `Box` (Task 3), `money_tokens` (Task 2)
- Produces: `HubbleDriver` (SiteDriver 구현)

2026-10-28 탐색에서 확인한 DOM (시작점이며, 실제 동작 확인이 우선):
- **쿠키:** `#truste-consent-required`. UK는 "Decline All", CA는 "Continue without accepting", CA-FR은 "Continuer sans accepter"다.
- **국가 안내 바:** 상단 `button[data-action=countrySelectorContinue]`. 누르면 다른 사이트로 이동할 수 있으므로 누르지 말고 닫기 버튼만 쓴다. 닫기 버튼이 없으면 그대로 두고, URL이 바뀌지 않았는지 확인한다.
- **CA 주**
  - 표시 버튼: `button.menu__select-field[data-aria-label="change region"]`. 텍스트가 현재 주다.
  - 옵션: `select.menu__select`에 `CA-ON`, `CA-QC` 값이 있고, 라벨은 Quebec(EN) / Québec(FR)이다.
  - 주를 바꾸면 새로고침된다. 새로고침이 끝나면 `wait_ms` 대기한 뒤 버튼 텍스트로 확인한다.
- **용량:** `input.hubble-pd-radio__input[name^="memory-rdo"]`. `data-englishname`은 `"256GB-12GB"` 형식이고 CA는 공백이 있을 수 있으니 정규화한다. `data-modelcode`, `data-price`가 있다. 클릭 대상은 연결된 `label.hubble-pd-radio__label`이고, label 텍스트는 `"256GB｜12GB £52.75/mo. or £1,899.00"`이다.
- **색상:** 색상 라디오 그룹이다. 같은 클래스 계열이며 name은 탐색해서 확인한다. 언어별 색상명이 다르므로 `data-modelcode`의 색상코드(`SM-F976?{ZK|ZV|ZW|DG}…`)로 고르고 판정한다.
- **가격**
  - `base`: 선택된 용량 label의 마지막 금액 토큰
  - `monthly`: 첫 번째 `/mo` 토큰
  - `headline`: 상단 고정 가격 바 텍스트. `with trade-in` 문구가 섞일 수 있으므로 원문 그대로 둔다.
  - `was`: 취소선 요소가 있을 때만
  - `sku`: `.price-bar-cart-btn[data-modelcode]` 또는 체크된 라디오
- **섹션:** 구매 도구 안의 보이는 `h2.s-option-title, h2.s-sub-title`. 영역은 제목 top부터 다음 제목 top까지이고, 가로는 구매 도구 오른쪽 열 컨테이너 폭이다.
- **extra_shots:** 상단 오퍼 바(`button.s-offer-open`, "Pay as low as …" / "Get £30 - £730 off …")를 펼친 레이어. 트레이드인 "Yes"는 누르지 않는다.
- **구매 단계 제목(탐색 결과):**
  - UK: Device, Storage, Colour, Trade-in, Pay monthly phone contracts, Samsung Care+, Gifts and Savings, Buy direct. Get more.
  - CA: Device, Storage, Colour, Samsung Trade-In, Save more, upgrade sooner with the Annual Upgrade Program, Samsung Care+, Gifts and Savings, Buy direct. Get more.
  - CA-FR: Appareil, Stockage, Couleur, …, Offre d'achat groupé

- [ ] **Step 1: live 테스트 작성**

```python
@pytest.mark.live
@pytest.mark.parametrize("ctx_id,storage", [("uk", "512GB"), ("ca-fr-qc", "1TB")])
def test_hubble_live_combo(tmp_path, ctx_id, storage): ...
    # 실제 사이트에서 capture_combo 1회 (wait_ms=5000)
    # r.status == "ok"; r.got.storage == storage; r.got.color == "Graphite"
    # r.base is not None and r.price_match is True
    # {"storage", "color", "trade_in", "care", "price_bar", "summary"} <= {s.section_id for s in r.sections}
    # ca-fr-qc: r.got.region 정규화 == "CA-QC" 이고 region 경고 없음
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest -m live tests/site_compare/test_live.py -k hubble -q` → FAIL (NotImplementedError)
- [ ] **Step 3: `HubbleDriver` 구현.** 실패하면 `--headed` 실행과 스크린샷으로 원인을 찾는다(systematic-debugging).
- [ ] **Step 4: 통과 확인** — 같은 명령으로 PASS 확인. 저장된 섹션 캡쳐 3장 이상을 Read로 열어 로딩 중 화면이 아닌지, 주 표시가 맞는지 눈으로 확인한다.
- [ ] **Step 5: 커밋** — `git add tools tests && git commit -m "feat(site_compare): hubble driver for UK/CA/CA-FR"`

---

### Task 6: US 드라이버

**Files:**
- Create: `tools/site_compare/sites/us.py`
- Modify: `tools/site_compare/sites/__init__.py` (`"us"` 연결)
- Test: `tests/site_compare/test_live.py`

**Interfaces:**
- Consumes: Task 3 인터페이스, `money_tokens`
- Produces: `UsDriver` (SiteDriver 구현)

2026-10-28 탐색에서 확인한 DOM:
- **배너**
  - 쿠키: `.truste-banner-close` ("Continue")
  - 좌하단 채팅 팝업: 닫기 버튼으로 닫는다.
  - 상단 프로모 바("Get up to $800 instant trade-in credit…"): 펼친 상태를 유지한다.
- **첫 진입:** 기본값은 Green Shadow·Unlocked SKU URL로 리다이렉트된다.
- **선택마다 URL이 SKU URL로 바뀝니다.** 예: `…/buy/galaxy-z-fold8-ultra-256gb-verizon-sku-sm-f976uzkavzw/`
- **선택자**
  - 용량: `[data-testid=handleRelationSelect][data-modeldisplay="256gb"]` (소문자)
  - 색상: `[aria-label="Color Variant: Graphite"]`
  - 통신사: `[aria-label="Carrier: Verizon"]`, `[aria-label="Carrier: Unlocked"]`
- **선택 불가 판정:** 클릭 후 URL의 SKU가 기대값과 다르면 선택 불가로 본다. 기대 SKU는 `SM-F976U` + 색상코드 + 용량코드 + 통신사 접미사이고, 통신사 접미사는 Unlocked=`XAA`, Verizon=`VZW`다. "is unavailable for Verizon devices" 같은 문구가 보일 때도 선택 불가다. 이 경우 `OptionUnavailable`을 던진다.
- **상태(요약 블록)**
  - `"256GB | Graphite | Verizon"` 줄 → storage, color, carrier
  - `"SM-F976U / SM-F976UZKAVZW"` → sku. URL의 sku와 교차 확인한다.
- **가격**
  - `base`: 요약 `Total` 금액
  - `was`: 요약의 `was $…`
  - `headline`: 상단 고정 바 텍스트(`… /mo for 24 mos at 0% APR`)
  - `monthly`: 그 바의 `/mo` 토큰
- **섹션:** h2가 없습니다. 메인 영역에서 글자가 크고 굵은 짧은 텍스트(예: 20px 이상, weight 600 이상)를 섹션 제목 후보로 잡고, 리뷰·푸터 영역은 제외합니다. 확인된 제목은 Storage, Color, Connectivity, Samsung Trade-in, Samsung Care+, Start building healthy habits with Galaxy, Choose your purchase option입니다. 영역은 제목 top부터 다음 제목 top까지이고, 가로는 제목이 속한 열의 폭입니다. 앞 3개는 오른쪽 열, 나머지는 가운데 넓은 열입니다.
- **Verizon 선택 시:** "Choose your purchase option"에 "Verizon Financing (Pay Monthly) … for 36 mos"가 추가됩니다. 이 섹션 캡쳐에 그대로 담기면 됩니다.
- **extra_shots**
  - Connectivity의 "See all deals"(통신사 bill credit 레이어)
  - Care+ 첫 번째 "Details" 레이어
  - "Check Eligibility for Exclusive Offers"는 로그인·인증으로 이어지므로 열지 않습니다.

- [ ] **Step 1: live 테스트 작성**

```python
@pytest.mark.live
@pytest.mark.parametrize("carrier,suffix", [("Unlocked", "XAA"), ("Verizon", "VZW")])
def test_us_live_combo(tmp_path, carrier, suffix): ...
    # want storage=512GB, color=Graphite, carrier
    # r.status == "ok"; r.got.sku == f"SM-F976UZKE{suffix}"; r.got.carrier == carrier
    # r.base is not None; Unlocked면 r.price_match is True (JSON-LD 존재), Verizon은 None 또는 bool
    # {"storage", "color", "connectivity", "trade_in", "care", "purchase_option", "price_bar", "summary"} <= section ids
    # Verizon: purchase_option 섹션 texts 중 "Verizon Financing" 포함

@pytest.mark.live
def test_us_live_unavailable(tmp_path): ...
    # want color=Green Shadow, carrier=Verizon → r.status == "unavailable"
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest -m live tests/site_compare/test_live.py -k us -q` → FAIL
- [ ] **Step 3: `UsDriver` 구현**
- [ ] **Step 4: 통과 확인** — 같은 명령으로 PASS 확인. Verizon 결제 방식 섹션 캡쳐를 Read로 열어 눈으로 확인한다.
- [ ] **Step 5: 커밋** — `git add tools tests && git commit -m "feat(site_compare): US driver with carrier selection"`

---

### Task 7: 전체 실행, 카드 작성, 육안 검증

**Files:**
- Modify: `tools/site_compare/cards/fold8_ultra.yaml`
- Create: `tools/site_compare/README.md`

**Interfaces:**
- Consumes: CLI(Task 3), `Card`/`Panel` 형식(Task 4)

- [ ] **Step 1: 전체 캡쳐 실행** — `.venv/bin/python -m tools.site_compare capture fold8_ultra`. 기대 결과: 결과 39개(main 21 + color_check 18), `error` 0개. `unavailable`은 실제 사이트 사정이므로 허용한다. 마지막 줄에 report 경로가 출력된다.
- [ ] **Step 2: 경고 점검** — `data.json`의 `mismatch`·`error`·`price not rendered`·`region mismatch`를 모두 확인한다. 드라이버 문제면 Task 5·6으로 돌아가 고치고 다시 실행한다. 사이트 사정이면 카드 후보로 메모한다.
- [ ] **Step 3: 캡쳐 검토** — 컨텍스트별로 storage, connectivity, trade_in, care, purchase_option(US) 섹션 캡쳐와 extra 캡쳐를 Read로 열어 차이를 메모한다.
- [ ] **Step 4: 카드 작성** — spec 5장 후보 표를 기준으로 실제로 차이가 확인된 것만 `cards/fold8_ultra.yaml`에 쓴다. 각 카드의 요건은 다음과 같다.
  - 패널 2개 이상
  - 강조 텍스트 1개 이상
  - 관찰은 [사실]/[추정] 표기
  - 메모는 정규화·파이프라인 관점(필드명·처리 규칙)

  탐색에서 이미 확인한 후보는 다음과 같다.
  - US Verizon 선택 시 결제 방식에 Verizon Financing 36개월 추가
  - Green Shadow는 Verizon 불가
  - UK "Pay monthly phone contracts" 단계는 UK에만 있음
  - CA "Annual Upgrade Program"
  - CA-FR 주 이름 오탈자("Colombie-Britiannique", "Îie-du-Price-Édouard"): CA-FR 지역 표시 바 캡쳐가 필요하면 hubble `extra_shots`에 지역 선택 목록 레이어를 추가한다.
  - 제목 색상명 "Shadow Violet" vs 옵션 "Violet Shadow"
  - 가격 표기 형식 차이(UK `/mo. or`, CA `From …/mo.‡ or`, CA-FR `À partir de … ou 2 699,99 $`, US `was:` + 할인가)
- [ ] **Step 5: 리포트 재생성** — `.venv/bin/python -m tools.site_compare build fold8_ultra --run latest`. 기대 결과: 카드 경고 0개.
- [ ] **Step 6: 브라우저로 확인** — `open <report.html 경로>`. 다음을 확인한다.
  - 빨간 박스 위치가 맞는지
  - 이미지를 누르면 원본이 열리는지
  - 가격표 칸을 누르면 부록으로 이동하는지
  - 다크 모드
- [ ] **Step 7: README 작성** — 설치(uv venv, requirements), 실행(capture/build/--only/--headed), 상품 추가 방법(YAML 필드 설명, 섹션 규칙, 카드 형식), 결과 해석(status 4종, 경고 종류), 문제 해결(봇 차단 시 `--headed`, 셀렉터 변경 시 드라이버 위치). 1페이지 분량이다.
- [ ] **Step 8: 커밋** — `git add tools && git commit -m "feat(site_compare): Fold8 Ultra cards and README"`
