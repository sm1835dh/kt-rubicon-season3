# 카테고리 확장(TV·세탁기·냉장고·노트북·워치) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 `tools/site_compare`를 5개 카테고리로 넓힙니다. 조합 발견, 스펙 수집, 템플릿별 드라이버(pd·us_pdp·watchbc 신규, hubble·us 일반화), 템플릿별 오프라인 픽스처 테스트, 주요 스펙 비교 리포트, 목차를 추가합니다. Fold8 수집은 그대로 동작해야 합니다.

**Architecture:** 상품 YAML은 두 모드를 지원합니다.
- `click` 모드: 기존 Fold8 방식입니다.
- `discover` 모드: 축 이름만 적습니다. 오케스트레이터가 기본 페이지에서 `driver.options()`로 옵션 트리를 발견합니다. 그런 다음 리프 조합마다 새 페이지를 열어 직접 진입(`goto_sku`)하거나, 기록된 클릭 경로로 해당 상태를 만들고 SKU를 검증합니다.

드라이버는 템플릿 단위입니다. 스펙 추출은 공통 함수(`pdd32`, US Next.js)로 둡니다. 오프라인 테스트는 `snapshot` 명령이 저장한 축약 DOM 픽스처와 기대값(golden)으로 드라이버 파싱을 검증합니다.

**Tech Stack:** Python 3.12, Playwright 1.64(`channel="chrome"`), PyYAML, Jinja2, pytest

**Spec:** `docs/superpowers/specs/2026-10-28-site-compare-categories-design.md`(근거: `docs/superpowers/research/2026-10-28-categories-recon.md`)

## Global Constraints

- 6개 컨텍스트(`uk`, `ca-en-on`, `ca-en-qc`, `ca-fr-on`, `ca-fr-qc`, `us`)를 씁니다. 세탁기만 `uk-f`를 더 둡니다(스펙 전용, 판매 종료).
- 대기: 로드 후 5초, 옵션 클릭 후 5초(`wait_ms=5000`). 테스트에서만 줄입니다.
- 구매 진행 금지: Add to cart, Buy now, Continue, 트레이드인·트레이드업 "Yes", Care+ "Confirm", 로그인, "Pre-qualify now"는 누르지 않습니다.
- 페이지를 열기 전에 쿠키를 넣습니다.
  - 동의: `notice_preferences=0:`, `notice_gdpr_prefs=0::implied,eu`, `notice_behavior=implied,eu`, `cmapi_cookie_privacy=permit 1 required`(모두 `.samsung.com`)
  - CA 주: `country_region=<region>`
  - US: `eddzipcode=10001`
- 전체 캡쳐는 8,000px 이하 조각으로 찍습니다. 클립은 페이지 폭 안으로 제한하고, 실제 PNG 크기를 기록합니다.
- 조합: TV 크기 전부, 세탁기 색상 전부, 냉장고 UK 색상·US 깊이, 노트북 기준 구성 1개, 워치 크기×연결(색상 Graphite 고정).
- 기준 SKU는 설계 3장을 따릅니다. 주요 스펙 비교 표는 기준 SKU 값입니다.
- Fold8 `click` 모드의 조합 id·카드·리포트는 바뀌면 안 됩니다. 기존 `data.json`(20261028-100623)으로 다시 빌드해도 리포트가 만들어져야 합니다.
- 결과물은 `out/`, 픽스처는 `tests/site_compare/fixtures/<template>/`(gzip)에 둡니다.

## Review Focus

1. **발견한 옵션 중 판매 불가가 섞인 경우**(UK 세탁기 Dark steel "No longer available", US 냉장고 RF23 + 우편번호 문제): 해당 조합을 `unavailable`로 남기고 다음 조합으로 진행해야 합니다. → Task 2 `test_discover_unavailable_leaf_recorded`
2. **가격·섹션·스펙이 모두 비어 있는데 `ok`가 되는 경우**(조사에서 기존 드라이버가 반복해서 거짓 ok를 냄): `error`여야 합니다. → Task 2 `test_nothing_captured_is_error`
3. **직접 진입 후 화면 SKU가 기대 SKU와 다른 경우**(워치 44mm 케이스 전용 코드, CA-FR LTE 미반영): `mismatch`로 기록해야 합니다. → Task 2 `test_leaf_sku_mismatch_flagged`
4. **16,384px보다 긴 페이지의 전체 캡쳐**: 조각이 여러 장 생기고, 각 조각의 높이가 8,000 이하여야 합니다. → Task 2 `test_full_shots_are_sliced`
5. **구 형식 `data.json`(Fold8)을 새 코드로 다시 빌드하는 경우**: 예외 없이 리포트가 나오고, 카드 경고가 0이어야 합니다. → Task 1 `test_legacy_rundata_loads` + Task 7 `test_fold8_rebuild_from_legacy_run`

---

## 파일 구조

```
tools/site_compare/model.py          # 수정: AxisSpec, Option, SpecItem, State.selection, ComboResult.full_shots/specs/spec_shots/key/is_ref, 구 형식 변환
tools/site_compare/config.py         # 수정: discover 모드 로딩, context 축·ref_sku·spec_url·cookies, key_specs, legacy expand_combos 유지
tools/site_compare/capture.py        # 수정: 쿠키 사전 설정, 조각 캡쳐, PNG 크기, 상태 규칙, 스펙 수집, discover 오케스트레이션
tools/site_compare/pngsize.py        # 신규: PNG IHDR에서 (w, h)
tools/site_compare/snapshot.py       # 신규: 축약 DOM 픽스처 + golden 기대값 저장
tools/site_compare/report.py         # 수정: discover 열·행, 주요 스펙 표, 스펙 부록, 조각 캡쳐, 판매 종료 표시, build_index
tools/site_compare/templates/report.html.j2   # 수정
tools/site_compare/templates/index.html.j2    # 신규
tools/site_compare/__main__.py       # 수정: snapshot 서브커맨드, index 갱신
tools/site_compare/sites/base.py     # 수정: Protocol 확장(options/choose/goto_sku/specs), BaseDriver 기본 구현
tools/site_compare/sites/common.py   # 신규: pdd32_specs, us_specs, layer_box, close_geo_bar, js_click
tools/site_compare/sites/pd.py       # 신규
tools/site_compare/sites/us_pdp.py   # 신규
tools/site_compare/sites/watchbc.py  # 신규
tools/site_compare/sites/hubble.py   # 수정: 노트북 대응 + discover 인터페이스
tools/site_compare/sites/us.py       # 수정: SKU 일반화, 선택 상태, 월 할부 $ 생략, 스펙 아코디언 + discover 인터페이스
tools/site_compare/products/{tv_s95h,washer_flagship,fridge_t_style,laptop_book6_pro,watch9}.yaml  # 신규
tools/site_compare/cards/{...}.yaml  # 신규(캡쳐 후)
tests/site_compare/test_model_v2.py, test_discover.py, test_drivers_offline.py, test_report_v2.py, test_snapshot.py  # 신규
tests/site_compare/test_live_categories.py   # 신규(@live)
tests/site_compare/fixtures/fake_pdp.html     # 신규(오케스트레이터 테스트용 가짜 PDP)
tests/site_compare/fixtures/<template>/<product>__<ctx>.html.gz + .expected.json   # snapshot이 생성
```

---

### Task 1: 데이터 모델 v2와 설정 v2 (Fold8 호환 유지)

**Files:**
- Modify: `tools/site_compare/model.py`, `tools/site_compare/config.py`, `tools/site_compare/capture.py`(selection 비교), `tools/site_compare/report.py`(selection 표시), `tools/site_compare/sites/hubble.py`·`sites/us.py`(read_state가 selection을 반환)
- Test: `tests/site_compare/test_model_v2.py`; 기존 테스트는 selection 기준으로 수정합니다.

**Interfaces:**
- Produces (`model.py`):
  - `AxisSpec(name: str, iterate: bool = False, fixed: str | None = None)`
  - `Option(axis: str, value: str, label: str, sku: str | None = None, url: str | None = None, available: bool = True, handle: str | None = None)`. `value`는 비교용 정규화 값(소문자, 공백·따옴표 제거)이고, `handle`은 드라이버 내부 선택 단서(input id, an-la 등)입니다.
  - `SpecItem(group: str, label: str, value: str)`
  - `State(selection: dict[str, str], region: str | None, sku: str | None, prices: PriceTexts, available: bool | None = None)`
  - `Combo(id, context_id, kind, want: dict[str, str], path: list[Option] = [], target_sku: str | None = None, key: str = "", is_ref: bool = False)`
  - `ComboResult`
    - `full_shot`를 `full_shots: list[str]`로 바꿉니다.
    - 추가 필드: `specs: list[SpecItem]`, `spec_shots: list[Shot]`, `key: str`, `is_ref: bool`
    - 나머지 필드는 기존과 같습니다.
  - `Context` 추가 필드: `axes: list[AxisSpec] | None = None`, `ref_sku: str | None = None`, `spec_url: str | None = None`, `spec_driver: str | None = None`, `cookies: dict[str, str] | None = None`, `spec_only: bool = False`
  - `Product` 추가 필드: `mode: str = "click"`, `axes: list[AxisSpec] = []`, `key_specs: list[SectionRule] = []`. 기존 필드(storages, colors, fixed_color, carriers)는 기본값을 비워 둡니다.
  - `RunData.from_json`: 구 형식을 읽습니다. `got.storage/color/carrier`는 `selection`으로, `full_shot`은 `[full_shot]`으로 바꾸고, `specs`·`spec_shots`·`key`·`is_ref`는 기본값으로 둡니다. 구 형식에서 `key`는 `want` 값을 `" · "`로 이은 문자열, `is_ref`는 False입니다.
- Produces (`config.py`):
  - `load_product(path)`: `storages` 키가 있으면 `mode="click"`입니다(Fold8, 기존 검증 유지). 없으면 `mode="discover"`이고 다음을 검증합니다.
    - `axes`(product 또는 context)
    - `contexts[*].ref_sku` 필수
    - driver ∈ {hubble, us, pd, us_pdp, watchbc}
    - `spec_url`이 있으면 `spec_driver` 기본값은 `pd`
  - `expand_combos(product)`: click 모드는 기존과 같습니다. discover 모드는 `ValueError`입니다(발견은 capture가 합니다).
  - `context_axes(product, ctx) -> list[AxisSpec]`: context 축이 있으면 그것을, 없으면 product 축을 씁니다.
  - `combo_key(path: list[Option]) -> str`: 라벨을 `" · "`로 이은 문자열입니다. path가 비면 `"기준 구성"`입니다.
  - `combo_id(ctx_id, path) -> str`: `f"{ctx_id}__" + "__".join(slug(o.value) for o in path)`입니다. path가 비면 `f"{ctx_id}__ref"`입니다.
- Consumers 수정: `capture._norm` 비교와 report의 `_got_text`·부록·`_main`(`want["storage"]` 등)은 `selection`·`want`를 씁니다. `HubbleDriver`·`UsDriver`의 `read_state`는 `selection={"storage":…, "color":…, "carrier":…}`(값이 있는 키만)을 반환합니다.

- [ ] **Step 1: 실패 테스트 작성** (`test_model_v2.py`)

```python
def test_legacy_rundata_loads():
    run = RunData.from_json(Path("tests/site_compare/fixtures/legacy_fold8_data.json"))  # 실제 100623 run의 data.json 복사본(축약 2개 결과)
    r = run.results[0]
    assert r.got.selection == {"storage": "256GB", "color": "Graphite"} and r.full_shots == ["shots/uk__256gb__full.png"]
    assert r.specs == [] and r.key == "256GB · Graphite"
def test_rundata_v2_roundtrip(tmp_path): ...   # selection/specs/spec_shots/key/is_ref 포함 왕복 ==
def test_load_discover_product(tmp_path):      # 아래 YAML로 load → mode == "discover"; context_axes(us) == [AxisSpec("depth", iterate=True)]
def test_discover_requires_ref_sku(tmp_path):  # ref_sku 없음 → ValueError
def test_expand_combos_rejects_discover(tmp_path): ...
def test_combo_id_and_key():
    path = [Option("size", "77", '77"'), Option("connectivity", "lte", "LTE")]
    assert combo_id("uk", path) == "uk__77__lte" and combo_key(path) == '77" · LTE'
    assert combo_id("us", []) == "us__ref" and combo_key([]) == "기준 구성"
def test_fold8_product_still_click_mode(): load fold8_ultra.yaml → mode "click", expand_combos 39
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest tests/site_compare/test_model_v2.py -q` → FAIL
- [ ] **Step 3: 구현.** `legacy_fold8_data.json` 픽스처는 `out/site_compare/fold8_ultra/20261028-100623/data.json`의 앞 2개 결과로 만듭니다. 기존 테스트에서 `State(storage, color, carrier, …)` 생성부를 `selection`으로 바꾸고, `full_shot`은 `full_shots`로 바꿉니다.
- [ ] **Step 4: 전체 확인** — `.venv/bin/pytest -q` → 전부 PASS. 기존 53개는 수정 반영 후 PASS여야 합니다.
- [ ] **Step 5: 회귀 확인** — `.venv/bin/python -m tools.site_compare build fold8_ultra --run 20261028-100623`이 성공하고, 카드 경고가 0입니다(Task 7에서 테스트로 고정).

---

### Task 2: 캡쳐 공통 기반과 discover 오케스트레이션

**Files:**
- Create: `tools/site_compare/pngsize.py`, `tests/site_compare/fixtures/fake_pdp.html`, `tests/site_compare/test_discover.py`
- Modify: `tools/site_compare/capture.py`, `tools/site_compare/sites/base.py`

**Interfaces:**
- Consumes: Task 1 모델·`context_axes`·`combo_id`·`combo_key`
- Produces (`sites/base.py`):
  - `SiteDriver`에 메서드 4개를 추가합니다.
    - `options(page, ctx, axis) -> list[Option]`: 현재 상태에서 그 축의 옵션 목록. `Option.sku`는 그 옵션을 고르면 바뀔 SKU(알 수 있을 때)
    - `choose(page, ctx, option) -> None`: 클릭 후 상태 반영까지 대기
    - `goto_sku(page, ctx, sku) -> bool`: 직접 진입을 지원하면 이동하고 True
    - `specs(page) -> tuple[list[SpecItem], list[tuple[str, Box]]]`: 펼치기 → 추출 → 캡쳐 영역
  - `BaseDriver` 기본 구현:
    - `goto_sku`는 False
    - `specs`는 `([], [])`
    - `options`는 `[]`
    - `choose`는 `OptionNotFound`
    - `extra_shots`·`close_extras`는 빈 동작
    - `prepare`는 `[]`
- Produces (`capture.py`):
  - `CONSENT_COOKIES: dict[str, str]`(Global Constraints 값)
  - `preset_cookies(browser_context, ctx) -> None`: 동의 쿠키, `country_region`(ctx.region이 있을 때), `ctx.cookies`를 `.samsung.com`에 넣습니다.
  - `full_shots(page, run_dir, name, slice_px=8000) -> list[str]`: `scroll_through(limit=80000)` 후 `document.documentElement.scrollHeight`·`scrollWidth` 기준으로 클립 조각을 찍습니다. 파일명은 `{name}__full-{n:02d}.png`입니다.
  - `_shot`
    - 클립은 `[0, scrollWidth] × [0, scrollHeight]`로 자릅니다. 폭이나 높이가 0 이하면 `None`을 돌려주고 경고를 남깁니다.
    - `Shot.width/height`는 `pngsize.png_size(path)`로 실제 크기를 넣습니다.
  - `discover_leaves(browser_context, driver, ctx, axes, wait_ms) -> list[Combo]`
    - 동작: 기본 URL을 연 뒤(`goto_sku(ref_sku)`를 지원하면 그 상태로) 축 순서대로 트리를 탐색합니다.
    - 마지막 축에서는 옵션의 `sku`를 리프 `target_sku`로 씁니다. 중간 축은 새 페이지에서 경로를 `choose`한 뒤 다음 축의 옵션을 읽습니다.
    - `fixed` 축은 `value`가 일치하는 옵션 하나만 씁니다. 일치하는 옵션이 없으면 경로를 버리고 경고를 남깁니다.
    - 축이 없으면 `[Combo(id=f"{ctx.id}__ref", target_sku=ctx.ref_sku, is_ref=True, key="기준 구성")]`입니다.
    - `is_ref`는 `target_sku == ctx.ref_sku`인 리프입니다. SKU를 모르면 경로 값이 기준 SKU 상태와 같은 리프입니다.
  - `capture_leaf(page, driver, product, ctx, combo, run_dir, wait_ms, with_extras) -> ComboResult`
    - 새 페이지에서 이동합니다: `goto_sku(target_sku)`가 되면 그것을, 아니면 기본 URL + 경로 `choose`를 씁니다.
    - 나머지 흐름은 `capture_combo`와 같습니다: 상태 읽기, 가격 재대기, 섹션·레이어 캡쳐, 조각 캡쳐, JSON-LD.
    - 추가로 같은 페이지에서 `driver.specs()`를 호출해 `specs`·`spec_shots`를 채웁니다.
    - 상태 판정 순서:
      1. 선택·이동 예외는 기존 규칙(`OptionUnavailable`은 근거, 최종 상태로 판정; `OptionNotFound`는 error)
      2. `got.available is False` → `unavailable`(경고 `not available: …`, 이때 `price not rendered` 경고는 남기지 않음)
      3. `target_sku`가 있는데 `got.sku != target_sku` → `mismatch`(경고 `sku mismatch: want=… got=…`)
      4. 경로 값과 `got.selection` 불일치 → `mismatch`
      5. 가격 없음 + 섹션 0개 + 스펙 0개 → `error`(경고 `nothing captured`)
  - `capture_specs_page(browser_context, ctx, result, run_dir, wait_ms)`: `ctx.spec_url`이 있으면 기준 리프 결과에만, 그 URL을 `get_driver(ctx.spec_driver)`로 열어 `specs`를 채웁니다. 스펙 캡쳐 파일명은 `{combo_id}__spec-{n}.png`입니다.
  - `run_capture`: product.mode가 discover면 컨텍스트마다 `discover_leaves` → 리프별 `capture_leaf`(US처럼 `fresh_page_per_combo`와 관계없이 항상 새 페이지) → `capture_specs_page`를 실행합니다. 리프 수는 `print`로 남기고 `RunData.discovered: dict[ctx_id, int]`에 기록합니다(Task 1 모델에 필드 추가). click 모드는 기존과 같고, 쿠키 사전 설정과 조각 캡쳐만 공통 적용합니다.

`fixtures/fake_pdp.html`: pd를 흉내 낸 정적 페이지입니다.
- 크기 라디오 3개(`data-modelcode`). 하나는 `data-soldout`이고, 고르면 `#avail`에 "No longer available"이 표시됩니다.
- 색상 라디오 2개(크기마다 SKU가 다름).
- `?broken=1`이면 고른 크기와 다른 SKU를 표시합니다.
- 가격 `#price`, SKU `#sku`, 섹션 `h3.t` 3개, 스펙 `dl#specs`(항목 4개).
- 높이 20,000px(조각 테스트용).

테스트 안의 `FakePdpDriver`가 이 페이지를 조작합니다.

- [ ] **Step 1: 실패 테스트 작성** (`test_discover.py`, `wait_ms=300`, 브라우저는 모듈 fixture)

```python
def test_discover_single_axis_leaves(...): axes=[AxisSpec("size", iterate=True)] → 3개, target_sku 3종, ref 하나 is_ref True
def test_discover_two_axes_with_fixed(...): axes=[size iterate, color fixed="Black"] → 3개(크기별 Black), 경로 길이 2
def test_discover_no_axes_uses_ref(...): axes=[] → 1개 id "c0__ref", target_sku == ref_sku
def test_discover_unavailable_leaf_recorded(...): soldout 크기 리프 → capture_leaf status "unavailable", 경고 "not available"
def test_leaf_sku_mismatch_flagged(...): ?broken=1 → status "mismatch", "sku mismatch" 경고
def test_nothing_captured_is_error(...): 가격·섹션·스펙을 돌려주지 않는 드라이버 → status "error", "nothing captured"
def test_specs_collected(...): r.specs 4개, (group,label,value) 첫 항목 일치, r.spec_shots 1장 존재
def test_full_shots_are_sliced(...): 높이 20,000 → full_shots 3장, 각 png_size 높이 ≤ 8000
def test_clip_clamped_to_page_width(...): 페이지 폭 밖 box → _shot None + 경고, 예외 없음
def test_preset_cookies(...): ctx.region="CA-QC", cookies={"eddzipcode": "10001"} → context.cookies()에 4개 동의 + country_region + eddzipcode
def test_png_size(tmp_path): 1x1 PNG → (1, 1)
```

- [ ] **Step 2: 실패 확인** — `.venv/bin/pytest tests/site_compare/test_discover.py -q` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** — `.venv/bin/pytest -q` → 전체 PASS(Fold8 기존 테스트 포함)

---

### Task 3: 공통 스펙 추출, pd 드라이버, snapshot 기반

**Files:**
- Create: `tools/site_compare/sites/common.py`, `tools/site_compare/sites/pd.py`, `tools/site_compare/snapshot.py`, `tests/site_compare/test_snapshot.py`, `tests/site_compare/test_drivers_offline.py`, `tools/site_compare/products/{tv_s95h,washer_flagship,fridge_t_style}.yaml`(UK·CA 컨텍스트 먼저, US는 Task 4)
- Modify: `tools/site_compare/sites/__init__.py`(pd 연결), `tools/site_compare/__main__.py`(snapshot 서브커맨드)
- Test: `tests/site_compare/test_live_categories.py`(pd 부분)

**Interfaces:**
- Produces (`sites/common.py`):
  - `pdd32_specs(page) -> tuple[list[SpecItem], list[tuple[str, Box]]]`: `.pdd32-product-spec__expand-cta button`을 누른 뒤(이미 펼쳐져 있으면 건너뜀) 그룹 제목과 `.pdd32-product-spec__content-item-title`/`-desc` 쌍을 추출합니다. 캡쳐 영역은 `#specs` 전체입니다.
  - `us_specs(page) -> …`: `[class*=Specs_subSpecItemName]`/`[class*=Specs_subSpecsItemValue]`를 읽습니다. 그 전에 `a[class*=Specs_expandBtn]`를 누르거나, 아코디언 `[data-testid=accordion-title]`(텍스트 Specs)을 누릅니다.
  - `js_click(locator)`, `close_geo_bar(page)`(`.nv16-country-selector__close`), `layer_box(page, selectors: list[str], exclude: list[str]) -> Box | None`
- Produces (`sites/pd.py`): `PdDriver(BaseDriver)`
  - `prepare`: 동의 배너가 보이면 JS 클릭 후 `wait_for_load_state`, 지역 바 닫기, 주 확인(hubble과 같은 문구 규칙). `{{`가 남아 있으면 최대 10초까지 기다립니다.
  - `options(axis)`
    - `size` → `input[name='pd-size']`
    - `color` → `input[name='pd-color']`
    - 그 밖 → `input[name^='pd-others-']`
    - 값·SKU·handle 출처: `value`=라벨 텍스트 정규화(`77"`→`77`), `sku`=`data-modelcode`, `handle`=input id
  - `choose`: `label[for=handle]`을 클릭합니다. URL이 바뀌면 `wait_for_load_state` 후 `prepare`를 다시 합니다. 그다음 `.pdd39-anchor-nav__info-sku` 또는 CTA `data-modelcode`가 `option.sku`가 될 때까지 최대 10초 기다립니다.
  - `read_state`
    - `sku`: `.pdd39-anchor-nav__info-sku` → CTA `[data-modelcode]` 순
    - `selection`: 체크된 각 축 input의 라벨
    - `prices.base`: `.pd-buying-price__new-price-currency`(또는 `__new-price` 마지막 금액 토큰)
    - `prices.monthly`: `__new-price-inner` 자체 텍스트에 `/mo`가 있을 때 첫 토큰
    - `prices.was`: `.pd-buying-price__was` 또는 `__text-saving-info` 첫 토큰(숨은 "RRP:" 제거)
    - `prices.headline`: `.pdd39-anchor-nav` 가격 영역 텍스트
    - `available`: CTA나 가격 바에 "No longer available"/"Out of Stock"이 있으면 False
  - `section_boxes`: "Price bar"(`.pdd39-anchor-nav`, 스크롤 0, 안정화 대기) → `.hdd02-buying-tool__option`의 보이는 자식들(제목은 `h3.pd-select-option__headline` / `.pd-select-option__headline-wrap` / `p.pd-sellout-option__headline`, 제목이 없으면 "Offers") → "Summary"(`.hdd02-buying-tool__summary`)
  - `extra_shots`: 레이어를 하나씩 엽니다(`.layer-popup` 열린 것의 `__inner`).
    - UK 금융: `a[data-target-popup=eipPopup]`
    - 트레이드업·인 Learn more: `button[an-la='trade-up:learn more']`, `#trade-in .pd-select-option__cta-wrap button`
    - 치수: `a[data-target-popup=dimensionsPopup]`
    - CA Care+: `label[for='pd-extended-warranty-option-0']`, 닫기는 `.layer-popup__close`. Confirm 금지

    추가 상품 "View more"(`button[data-js-action=offerListViewMore]`)는 펼친 뒤 해당 섹션을 다시 캡쳐합니다.
  - `specs`: `pdd32_specs`
  - `SNAPSHOT_KEEP`: `.pdd39-anchor-nav`, `section.hdd02-buying-tool`, `#specs`, `button.menu__select-field[data-aria-label="change region"]`, `script[type="application/ld+json"]`
- Produces (`snapshot.py`):
  - `save_snapshot(page, driver, product, ctx, out_dir) -> Path`: 계산 스타일로 숨겨진 요소에 `style="display:none"`을 박은 뒤, `SNAPSHOT_KEEP` 하위 트리만 순서대로 모은 HTML을 `fixtures/<driver>/<product>__<ctx>.html.gz`로 저장합니다(script는 ld+json만 남김). 같은 자리에 `.expected.json`도 씁니다.
  - expected 내용: `options`(축별 `[value, label, sku]`), `state`(selection/sku/prices/available), `sections`(제목 목록), `spec_count`, `spec_sample`(앞 5개), `offers`(`extract_offers` 키 목록)
  - `load_fixture(page, path) -> dict`: `page.set_content(gunzip)`. expected dict를 반환합니다.
  - CLI: `python -m tools.site_compare snapshot <product> [--only ctx,…]`는 컨텍스트마다 기준 SKU 상태로 연 뒤 저장합니다.
- 상품 YAML(UK·CA 4~5개 컨텍스트): URL·ref_sku·축은 조사 결과 문서를 따릅니다.

| 상품 | 축 | 비고 |
|---|---|---|
| `tv_s95h` | `[{name: size, iterate: true}]` | |
| `washer_flagship` | `color` iterate | `uk-f`는 `spec_only: true`, 축 없음 |
| `fridge_t_style` | `color` iterate | US 축은 Task 4 |

  `sections`·`key_specs` 규칙은 조사 문서의 섹션 제목·스펙 라벨로 작성합니다. 예: `key_specs`의 `capacity: ["washing capacity", "capacité de lavage", "washer capacity", "gross total", "net total", "total capacity", "volume"]`.

- [ ] **Step 1: snapshot 오프라인 테스트 작성** (`test_snapshot.py`): `fake_pdp.html`을 `FakePdpDriver`로 → `save_snapshot` → `load_fixture` 후 같은 드라이버의 `read_state`·`options` 결과가 expected와 같습니다. 숨김 요소에 `display:none`이 박혀 있는지도 확인합니다.
- [ ] **Step 2: 실패 확인 → `snapshot.py` 구현 → 통과 확인** — `.venv/bin/pytest tests/site_compare/test_snapshot.py -q`
- [ ] **Step 3: pd live 테스트 작성** (`test_live_categories.py`, `@pytest.mark.live`)

```python
@pytest.mark.parametrize("product,ctx_id,sku", [("tv_s95h","uk","QE77S95HFTXXU"), ("tv_s95h","ca-en-qc","QN77S95HAFXZC"),
    ("washer_flagship","uk","WF90H11C4WT1"), ("washer_flagship","ca-fr-on","WF90F53ADSA5"), ("fridge_t_style","uk","RF65DG960ESREU")])
def test_pd_live_ref(tmp_path, product, ctx_id, sku):
    # 기준 리프 capture_leaf → status ok, got.sku == sku, base 금액 있음,
    # 섹션에 price_bar·summary 포함 + 구매 섹션 ≥ 3, specs ≥ 30, spec_shots ≥ 1
def test_pd_live_tv_sizes_uk(tmp_path): discover_leaves(uk) → 크기 value 집합 == {"48","55","65","77"}
def test_pd_live_tv_quebec_price(tmp_path): ca-en-qc 기준 리프 base == "$4,521.09"이 아니면 실패 대신 경고 출력(가격은 변동) — base 존재 + region "Quebec"만 단언
def test_pd_live_washer_uk_f_spec_only(tmp_path): uk-f → status "unavailable", specs ≥ 30
```

- [ ] **Step 4: 실패 확인** — `.venv/bin/pytest -m live tests/site_compare/test_live_categories.py -k pd -q` → FAIL
- [ ] **Step 5: `common.py`, `pd.py` 구현.** live로 확인하며 선택자를 조정합니다. 캡쳐 이미지는 Read로 눈으로 확인합니다(가격 바, 구매 섹션 2개, 스펙, 레이어 1개).
- [ ] **Step 6: 통과 확인** — 같은 live 명령 → PASS
- [ ] **Step 7: 픽스처 저장** — `.venv/bin/python -m tools.site_compare snapshot tv_s95h`(washer·fridge도). `fixtures/pd/*.html.gz` 크기는 개당 300KB 이하여야 하고, 넘으면 `SNAPSHOT_KEEP`을 줄입니다.
- [ ] **Step 8: 오프라인 드라이버 테스트 작성** (`test_drivers_offline.py`): `fixtures/*/*.expected.json`을 모두 매개변수로 삼아 `load_fixture` → `get_driver(<template>)`의 `read_state`·`options`·`specs`(추출 부분만) 결과가 expected와 같은지 봅니다. 섹션은 오프라인에서 기하가 없으므로 제목 목록만 비교합니다(`section_titles(page)` 보조 함수를 드라이버에 둡니다). 손으로 쓴 단언도 넣습니다(조사 사실).
  - TV UK 크기 `{48,55,65,77}`
  - TV CA 크기 `{55,65,77,83}`
  - 세탁기 UK `uk` 기준 SKU WF90H11C4WT1
  - 냉장고 UK 색상 2개
- [ ] **Step 9: 통과 확인** — `.venv/bin/pytest -q` → PASS

---

### Task 4: us_pdp 드라이버 (US TV·세탁기·냉장고)

**Files:**
- Create: `tools/site_compare/sites/us_pdp.py`
- Modify: `sites/__init__.py`, 상품 YAML 3개에 `us` 컨텍스트 추가(`cookies: {eddzipcode: "10001"}`; TV 축 size, 세탁기 color, 냉장고 `axes: [{name: depth, iterate: true}]`), `test_live_categories.py`, `test_drivers_offline.py`(US 단언)

**Interfaces:**
- Produces: `UsPdpDriver(BaseDriver)`
  - `prepare`: 동의 배너가 보이면 JS 클릭(타임아웃 무시)하고, 채팅 위젯 닫기를 시도합니다.
  - `options(axis)`
    - `size` → `[data-testid=sizeTileSelect][role=radio]`(aria-label `Size: 77"`)
    - `color` → `[aria-label^='Color Variant:']`
    - `depth` 등 → `[data-testid=SeriesTile][role=radio][an-la^='<axis>:']`
    - `sku`는 `data-modelcode`(대문자)가 있을 때만 채웁니다.
  - `choose`: `click(no_wait_after=True)` → URL의 `-sku-`가 바뀌거나 `aria-checked=true`가 될 때까지 최대 15초 기다립니다.
  - `read_state`
    - SKU: URL `-sku-([a-z0-9-]+)/?$` 또는 `[class*=ModelInfo_modalInfo]`의 `X / Y` 오른쪽
    - selection: 각 축의 `aria-checked=true` 타일 라벨
    - base: `[class*=Summary_totalprice]` → 결제 카드 "One-time Payment" → 헤더 첫 금액 순
    - was: 헤더 `was $…` 또는 `Comp. Value: $…`
    - monthly: 결제 카드 "Pay Monthly"(`$` 없는 숫자도 허용 → `$`를 붙여 저장)
    - headline: 헤더 `[class*=PriceInfoText_]`
    - available: "not available in your area"/"Out of stock"이면 False
  - `section_boxes`: 먼저 "Price bar"(헤더 컨테이너), 이어서 `[role=heading][aria-level="2"]` 제목들을 `#product-summary`(또는 `[class*=Summary_container]`) 상단 전까지, 끝으로 "Summary"를 넣습니다. 제목이 공백이거나 x ≥ scrollWidth면 버립니다.
  - `extra_shots`: Care+ Terms(`button[class*=CarePlus_ux2Anchor]`), Delivery Learn More(`#delivery button[class*=ScrollableButtonGroup_ux2Anchor]`), Start Measuring(`button[class*=Measurement_startMesaureCta]`)입니다. 레이어 영역은 `[class*=Overlay_dialog]` 또는 `[class*=Overlay_wrapper] [role=dialog]`이고, `SupportedLanguagesPopup`은 제외합니다. Escape로 닫습니다.
  - `specs`: `us_specs`
  - `SNAPSHOT_KEEP`: 헤더 컨테이너, 각 h2 섹션 부모, `#product-summary`, `#\\#specs` 또는 Specs 컨테이너, ld+json

- [ ] **Step 1: live 테스트 작성**

```python
@pytest.mark.parametrize("product,sku", [("tv_s95h","QN77S95HAFXZA"), ("washer_flagship","WF90F53ADSA5"), ("fridge_t_style","RF23DB9600QLAA")])
def test_us_pdp_live_ref(tmp_path, product, sku): status ok; got.sku == sku; base·was 존재; monthly "$"로 시작; price_match True;
    # 섹션에 summary 포함, "Highlights" 없음; specs ≥ 50; delivery 섹션 텍스트에 "not available in your area" 없음(우편번호 쿠키 확인)
def test_us_pdp_live_fridge_depth_options(tmp_path): discover_leaves → depth 값 집합 == {"counterdepth","fulldepth"}, target sku에 RF29DB9600QLAA 포함
```

- [ ] **Step 2: 실패 확인** → **Step 3: 구현**(live로 조정, 캡쳐를 눈으로 확인) → **Step 4: 통과 확인**
- [ ] **Step 5: 픽스처 저장**(`snapshot … --only us`)과 오프라인 단언 추가(TV US 크기 `{55,65,77,83}`, 세탁기 US 색상 `{darksteel, ivory}`). 그다음 `.venv/bin/pytest -q` → PASS

---

### Task 5: watchbc 드라이버와 hubble 노트북 대응

**Files:**
- Create: `tools/site_compare/sites/watchbc.py`, `tools/site_compare/products/{watch9,laptop_book6_pro}.yaml`(UK·CA 컨텍스트)
- Modify: `sites/hubble.py`, `sites/__init__.py`, `test_live_categories.py`, `test_drivers_offline.py`

**Interfaces:**
- Produces: `WatchBcDriver(BaseDriver)`
  - `goto_sku`: `<base buy url>?modelCode=<sku>`로 이동하고 True를 돌려줍니다.
  - `options(axis)`
    - 섹션 매핑: `size`→`C-SIZ`, `connectivity`→`C-CON`, `color`→`C-CLR`
    - 대상: `.watch-bc-option__option[data-type-code=<code>] input`
    - `value`=`data-modeldisplay` 정규화, `sku`=`data-modelcode`, `handle`=id. 숨김·비활성이면 `available=False`입니다.
  - `choose`: `label.option-select[for]`를 클릭합니다. 그다음 `.bar-total-price`가 채워지고 `.total-summary .model-code`가 바뀔 때까지 기다립니다.
  - `read_state`
    - SKU: `.total-summary .model-code`
    - selection: 체크된 input의 `data-modeldisplay`(축별)
    - base: `strong.bar-total-price`
    - was: `.bar-was-price`(보일 때)
    - headline: 가격 바 텍스트
    - available: "Out of Stock"이 CTA에 있으면 False
  - `section_boxes`: "Price bar"(`.watch-bc-price-bar`, 스크롤 0) → "Offer banner"(`.watch-bc-offer-banner-wrap`) → 각 `.watch-bc-option__option[data-type-code]`(제목 `h2.watch-bc-option__option-title`) → 보이는 `.watch-bc-buyflow`(제목 `.watch-bc-buyflow__headline-title`) → "Summary"(`.total-summary`)
  - `extra_shots`: x ≥ 0인 `button.s-offer-open`을 JS 클릭 → `.watch-bc-offer-banner-wrap`
  - `specs`: 없음. 컨텍스트 `spec_url`(PDP)과 `spec_driver: pd`로 수집합니다.
  - `SNAPSHOT_KEEP`: 가격 바, 옵션 컨테이너, buyflow들, `.total-summary`, ld+json
- hubble 수정(`HubbleDriver`)
  - `goto_sku`: `?modelCode=`로 이동합니다(Fold8에서는 쓰지 않음, click 모드).
  - `options(axis)`: 축 이름 → 라디오 name을 `strip()` 비교로 찾습니다.

    | 축 | name |
    |---|---|
    | storage | `memory-rdo` |
    | memory | `memories-rdo` |
    | color | `basic-color` |
    | screen | `screensize-rdo` |
    | processor | `processor-rdo` |
    | graphic | `graphic-rdo` |
    | device | `device-rdo` |
    | os | `sim-rdo` |
    | connectivity | `connectivity-rdo` |

    `label`은 `html.unescape(displayname)`입니다. 숨겨진 label은 `available=False`입니다.
  - 색상 판정 순서: `data-color` → SKU 색상코드 → 영어명. 예전의 `code[8:10]` 고정 위치는 Fold8 SKU에만 씁니다.
  - `read_state.prices.was`: `.hubble-price-bar__price-total-save-inner`의 첫 금액. `selection`에 memory/storage/screen/processor/graphic/color를 담습니다.
  - CA 자체 재로드 대비: `prepare` 앞에 `wait_for_load_state("networkidle", timeout=10000)`을 넣습니다(실패는 무시).
- 상품 YAML
  - `watch9`: 축 `size`·`connectivity` iterate, `color` fixed `Graphite`. UK·CA `spec_url` = PDP(조사 문서)
  - `laptop_book6_pro`: 축 없음(기준 구성). UK·CA `spec_url` = PDP

- [ ] **Step 1: live 테스트 작성**

```python
@pytest.mark.parametrize("ctx_id,sku", [("uk","SM-L340NZKAEUB"), ("ca-fr-qc","SM-L340NZKAXAC")])
def test_watchbc_live_ref(...): status ok; sku 일치; base 존재; 섹션 ≥ 8(Case size 포함 → section id case_size); specs ≥ 20(spec_url 경유)
def test_watchbc_live_leaves_uk(...): discover → 리프 4개, target sku 집합 == {SM-L340NZKAEUB, SM-L345FZKAEUB, SM-L350NZKAEUB, SM-L355FZKAEUB}
@pytest.mark.parametrize("ctx_id,sku", [("uk","NP960XJG-KGAUK"), ("ca-fr-on","NP960XJG-KG1CA")])
def test_hubble_laptop_live_ref(...): status ok; got.selection["color"] 존재; base 존재; CA는 was 존재; specs ≥ 20(spec_url)
```

  리프 SKU 집합은 발견 결과로 확인하고, 다르면 실제 값으로 고칩니다. 조사 문서의 SKU 규칙은 [추정]입니다.
- [ ] **Step 2: 실패 확인** → **Step 3: 구현** → **Step 4: 통과 확인.** Fold8 hubble live(`-k hubble_live_combo`)도 다시 PASS여야 합니다.
- [ ] **Step 5: 픽스처 저장**(watch9·laptop UK/CA)과 오프라인 단언(워치 UK 크기 `{40mm,44mm}`, 노트북 CA-FR 색상 판정 "Gris"→표준 색상). 그다음 `.venv/bin/pytest -q` → PASS

---

### Task 6: us 드라이버 일반화 (US 노트북·워치, Fold8 회귀)

**Files:**
- Modify: `sites/us.py`, 상품 YAML 2개에 `us` 컨텍스트 추가(워치 기준 URL은 40mm `-sku-`, 노트북은 조사 문서 URL), `test_live_categories.py`, `test_drivers_offline.py`

**Interfaces:**
- `UsDriver` 수정(Fold8 동작 유지)
  - SKU 정규식 일반화: URL `-sku-([a-z0-9-]+)/?$`, 요약 `^[A-Z0-9-]+\s*/\s*([A-Z0-9-]+)$`. 요약 블록 감지도 이 패턴을 씁니다.
  - `options(axis)`
    - `an-la` 접두 사용: `case size:`, `card:`(connectivity), `case color:`, `color:`
    - `[data-modeldisplay]` 그룹: 그룹 제목 `span[class*=Label_sharpSansBold][class*=Label_large]` 아래 타일
    - `Color Variant:` aria
    - `sku`=`data-modelcode`(대문자)
  - `choose`: 클릭 후 URL `-sku-` 변경 대기(최대 15초)
  - `read_state.selection`
    - Fold8 축(storage/color/carrier)은 기존처럼 읽습니다.
    - 그 밖의 축은 선택된 타일(클래스에 `selected` 포함, `aria-pressed`/`aria-checked`="true")의 라벨입니다.
    - 요약 줄은 위치로 해석하지 않습니다(워치 "Wifi" 오독 방지).
  - 월 할부: 헤더의 `or 15.83/mo`처럼 `$`가 없는 경우도 토큰으로 인정합니다. 저장 시 통화 기호를 붙입니다(`prices.py`의 `money_tokens`에 `allow_bare_before_mo` 처리 추가, 테스트 포함).
  - `specs`: `us_specs`(아코디언 클릭)
  - `goto_sku`: False. US는 기본 URL + 경로 클릭입니다.
- `prices.py`: `money_tokens(text, locale, bare_monthly=False)`. True면 `(?<![\d$])(\d+\.\d{2})/mo` 같은 `$` 없는 월 금액도 `"$15.83"` 형태로 돌려줍니다.

- [ ] **Step 1: 테스트 작성**
  - 오프라인 `test_prices.py`: `money_tokens("$379.99 or 15.83/mo for 24 mos", "en-US", bare_monthly=True) == ["$379.99", "$15.83"]`
  - live:

```python
def test_us_watch_live_ref(...): sku SM-L340NZKAXAA, selection["connectivity"] == "Bluetooth"(색상 오독 없음), monthly "$15.83" 형식, specs ≥ 20
def test_us_watch_live_leaves(...): 리프 4개(40/44 × BT/LTE)
def test_us_laptop_live_ref(...): sku NP960XJG-KG1US, base/was 존재, specs ≥ 20
```

  Fold8 US live 3개(`-k us_live`)도 그대로 PASS여야 합니다.
- [ ] **Step 2: 실패 확인** → **Step 3: 구현** → **Step 4: 통과 확인**(신규 live와 Fold8 US live)
- [ ] **Step 5: 픽스처 저장**(watch9·laptop `--only us`, 그리고 `fold8_ultra --only us`도 저장해 Fold8 회귀 픽스처로 씁니다). 그다음 `.venv/bin/pytest -q` → PASS

---

### Task 7: 리포트 v2와 목차

**Files:**
- Modify: `tools/site_compare/report.py`, `templates/report.html.j2`, `__main__.py`
- Create: `templates/index.html.j2`, `tests/site_compare/test_report_v2.py`

**Interfaces:**
- 열(`_columns`): click 모드는 기존과 같습니다(US 통신사별). discover 모드는 컨텍스트당 1열입니다.
- 가격 표 행
  - click: storage
  - discover: `combo.key` 합집합. 정렬은 컨텍스트 순서상 처음 나온 순서이고, 크기 같은 숫자 키는 숫자순입니다.
  - 칸: 그 컨텍스트에 해당 키 조합이 없으면 `—`(미제공)입니다. `unavailable`이면서 `got.available is False`면 "판매 종료"로, 그 밖의 `unavailable`은 "선택 불가"로 표시합니다.
  - `spec_only` 컨텍스트 열은 가격 표에서 회색 처리합니다.
- 메뉴 구성 표: 열마다 `is_ref` 조합(없으면 첫 조합)을 씁니다.
- **주요 스펙 비교 표**(discover 모드)
  - 행: `product.key_specs`
  - 칸: 각 컨텍스트 `is_ref` 결과의 `specs`에서 `label`이 규칙에 처음 맞는 항목의 `value`. 원문 그대로 두고, `title`에 원래 라벨을 넣습니다.
  - 값이 없으면 `—`입니다.
- 부록: 조합마다 스펙 원문 표(`<details>`, 그룹별)와 스펙 캡쳐, 전체 캡쳐 조각 목록(첫 조각을 썸네일로)을 둡니다.
- `build_index(out_root: Path, products_dir: Path) -> Path`: 상품마다 최신 완전 실행(`data.json`이 있고, 결과 수가 리프 합계 이상)의 상태 요약과 리포트 링크를 `out_root/index.html`에 씁니다. `capture`·`build`가 끝날 때 호출합니다.
- 카드 `Panel.section`에 `"spec"`(스펙 캡쳐 첫 장)과 `"spec-{n}"`을 허용합니다. 강조 텍스트는 스펙 캡쳐의 texts에서 찾습니다.

- [ ] **Step 1: 실패 테스트 작성** (`test_report_v2.py`, 테스트 안에서 discover RunData 생성)

```python
def test_discover_price_table_rows_union_and_missing_cells(...): uk 크기 48~77, us 55~83 → 행 48,55,65,77,83; uk 83 칸 "—", us 48 칸 "—"
def test_discontinued_cell_label(...): available False unavailable → "판매 종료"
def test_key_spec_table_uses_ref_combo(...): ref와 비-ref의 capacity 값이 다름 → 표에는 ref 값만, title에 라벨
def test_spec_appendix_and_slices(...): html에 스펙 원문 행 수 일치, 전체 캡쳐 조각 링크 3개
def test_card_spec_panel(...): Panel(section="spec", highlight=["6.1 cu.ft"]) → 박스 1개
def test_index_lists_products(...): out_root에 두 상품 run → index.html에 두 리포트 상대 링크와 ok 개수
def test_fold8_rebuild_from_legacy_run(...): legacy_fold8_data.json로 만든 run_dir + 실제 cards/fold8_ultra.yaml 일부 카드 → 예외 없음
```

- [ ] **Step 2: 실패 확인** → **Step 3: 구현** → **Step 4: 통과 확인** — `.venv/bin/pytest -q` → PASS
- [ ] **Step 5: 실제 Fold8 재빌드** — `.venv/bin/python -m tools.site_compare build fold8_ultra --run 20261028-100623` → 성공, 카드 경고 0. 브라우저 캡쳐로 기존과 같은 모습인지 확인합니다.

---

### Task 8: 전체 실행, 카드, 육안 검증, 문서

**Files:**
- Create: `tools/site_compare/cards/{tv_s95h,washer_flagship,fridge_t_style,laptop_book6_pro,watch9}.yaml`
- Modify: `tools/site_compare/README.md`

- [ ] **Step 1: 상품별 전체 캡쳐** — `.venv/bin/python -m tools.site_compare capture <product>`를 5개 상품 각각 백그라운드로 실행합니다. 동시에 2개까지만 돌립니다(사이트 부하와 클릭 타이밍 때문).
  - 기대 결과: 컨텍스트별 발견 리프 수가 기대와 같습니다(TV UK 4, CA 4×4, US 4; 워치 4×6; 세탁기 UK 2 + uk-f 1 + CA 1×4 + US 2; 냉장고 UK 2 + CA 4 + US 2; 노트북 6).
  - `error` 0개. `unavailable`은 근거가 있는 것만 허용합니다.
- [ ] **Step 2: 경고 점검** — `mismatch`·`error`·`nothing captured`·`sku mismatch`를 모두 확인합니다. 드라이버 문제면 해당 Task로 돌아가 고치고(테스트 추가), 다시 실행합니다.
- [ ] **Step 3: 캡쳐 검토** — 상품마다 기준 조합의 가격 바, 구매 섹션, 스펙, 레이어 캡쳐를 Read로 확인합니다. 설계 8장의 카드 후보가 실제로 보이는지 메모합니다.
- [ ] **Step 4: 카드 작성** — 상품마다 5~10개를 씁니다. 요건은 Fold8과 같습니다(패널 2개 이상, 강조 텍스트, [사실]/[추정], 정규화 메모). 세탁기·노트북·TV 카드에는 "동일 모델 아님"을 적습니다.
- [ ] **Step 5: 리포트 재생성과 목차** — `build <product>` 5회 → 카드 경고 0, `out/site_compare/index.html` 갱신
- [ ] **Step 6: 브라우저 확인** — 상품마다 리포트 첫 화면, 주요 스펙 표, 카드 2개를 스크린샷으로 확인합니다(라이트·다크).
- [ ] **Step 7: README 갱신** — 다음 내용을 1~2쪽으로 씁니다.
  - discover 모드 YAML 작성법(축, ref_sku, spec_url, cookies, key_specs)
  - 템플릿 → 드라이버 표
  - `snapshot` 명령과 오프라인 테스트 흐름("사이트가 바뀌면: snapshot → pytest → 깨진 단언 확인 → 드라이버 수정")
  - 새 상품 추가 체크리스트
