# site_compare: 국가별 Samsung.com 화면 비교 캡쳐

같은 상품을 국가·지역·옵션 조합별로 실제 브라우저에서 열어 캡쳐하고, 차이점 카드가 들어간 `report.html`을 만드는 도구입니다.

- 설계: `docs/superpowers/specs/2026-10-28-site-capture-comparison-design.md`(Fold8), `docs/superpowers/specs/2026-10-28-site-compare-categories-design.md`(카테고리 확장)
- 페이지 조사 결과: `docs/superpowers/research/2026-10-28-categories-recon.md`

## 설치

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

브라우저는 PC에 설치된 Google Chrome을 사용합니다(`channel="chrome"`). 따라서 `playwright install`은 필요 없습니다.

## 실행

저장소 루트에서 실행합니다.

```bash
.venv/bin/python -m tools.site_compare capture tv_s95h                 # 전체 캡쳐 후 리포트·목차 생성
.venv/bin/python -m tools.site_compare capture tv_s95h --only uk,us    # 일부 컨텍스트만
.venv/bin/python -m tools.site_compare capture tv_s95h --headed        # 브라우저 창을 띄워서 (봇 차단 시)
.venv/bin/python -m tools.site_compare capture tv_s95h --only ca-fr-on --into latest   # 실패한 컨텍스트만 기존 실행에 다시 캡쳐
.venv/bin/python -m tools.site_compare build tv_s95h                   # 카드만 고친 뒤 최신 캡쳐로 리포트 재생성
.venv/bin/python -m tools.site_compare build tv_s95h --run 20261029-101500
.venv/bin/python -m tools.site_compare snapshot tv_s95h                # 오프라인 테스트용 픽스처 다시 저장
```

| 상품 id | 내용 |
|---|---|
| `fold8_ultra` | Galaxy Z Fold8 Ultra |
| `tv_s95h` | OLED S95H(77") |
| `washer_flagship` | 드럼세탁기 최상위(UK WF90H + 판매 종료 WF90F, NA WF90F53) |
| `fridge_t_style` | T-Style 프렌치도어 냉장고 |
| `laptop_book6_pro` | Galaxy Book6 Pro 16" |
| `watch9` | Galaxy Watch9 |

- 결과는 `out/site_compare/<상품>/<실행시각>/`에 저장됩니다. 파일은 `report.html`, `data.json`, `shots/*.png`입니다.
- 전체 목차는 `out/site_compare/index.html`입니다.
- 실행 시간: 페이지 로드 후와 옵션 클릭 후 각각 5초씩 기다립니다. 그래서 상품 하나에 20~60분 걸립니다.
- **동시 실행 금지:** 여러 실행을 동시에 돌리지 마세요. 짧은 간격으로 페이지를 많이 열면 가격이 그려지지 않는 경우가 생깁니다. 도구는 이때 한 번 새로고침하지만, 실행은 차례로 돌리는 게 안전합니다.

## 템플릿과 드라이버

| 드라이버 | 페이지 | 쓰는 곳 |
|---|---|---|
| `hubble` | 구매 페이지 구성기(`hubble-*`) | UK·CA·CA-FR 휴대폰 구매 페이지, 노트북 시리즈 구매 페이지 |
| `pd` | 일반 제품 페이지(`hdd02-buying-tool`, `pdd39`, `pdd32` 스펙) | UK·CA·CA-FR TV·세탁기·냉장고. 노트북·워치의 스펙 페이지 |
| `watchbc` | 워치 구매 페이지(`watch-bc-*`) | UK·CA·CA-FR 워치 |
| `us` | US 구매 페이지(Next.js, `-sku-` URL) | US 휴대폰·노트북·워치 |
| `us_pdp` | US 제품 페이지(Next.js `VD`) | US TV·세탁기·냉장고 |

모든 드라이버는 `sites/base.py`의 `BaseDriver`를 상속합니다.

| 메서드 | 하는 일 |
|---|---|
| `prepare` | 배너·지역 처리 |
| `options` / `choose` | 옵션 발견·선택 |
| `sku_url` | SKU로 직접 진입 |
| `read_state` | 선택·SKU·가격 4종 읽기 |
| `section_boxes` | 구매 섹션 영역 |
| `extra_shots` | 레이어 열기 |
| `specs` | 스펙 펼치기·추출 |

## 새 상품 추가 (discover 모드)

1. `products/<상품>.yaml`을 만듭니다. 비슷한 카테고리 파일을 복사하는 게 빠릅니다.

```yaml
id: tv_s95h
title: Samsung OLED S95H (77" 기준)
axes: [{name: size, iterate: true}]            # 가격이 달라지는 축. 값은 페이지에서 발견
contexts:
  - {id: uk, label: "UK", driver: pd, locale: en-GB, currency: GBP, ref_sku: QE77S95HFTXXU,
     url: "https://www.samsung.com/uk/tvs/…-qe77s95hftxxu/"}
  - {id: ca-en-qc, label: "CA-EN · Quebec", driver: pd, locale: en-CA, currency: CAD, region: CA-QC, ref_sku: …, url: …}
  - {id: us, label: "US", driver: us_pdp, locale: en-US, currency: USD, ref_sku: …, url: …,
     cookies: {eddzipcode: "10001"}}           # US 배송 지역(뉴욕)
sections:   [ {id: size, label_ko: 크기, patterns: ["choose your size", "choisissez votre taille"]}, … ]
key_specs:  [ {id: weight, label_ko: 무게, patterns: ["set weight without stand", "poids .*sans support"]}, … ]
```

   주요 필드는 다음과 같습니다.

   | 필드 | 설명 |
   |---|---|
   | `axes` | `iterate: true`는 모든 값을 캡쳐하고, `fixed: Graphite`는 그 값만 씁니다. 컨텍스트마다 `axes:`로 덮어쓸 수 있습니다. 예: US 냉장고는 `depth` |
   | `ref_sku` | 기준 SKU. 주요 스펙 비교 표와 카드의 기본 비교 대상입니다 |
   | `spec_url` | 스펙이 다른 페이지(제품 페이지)에 있을 때 그 URL입니다. 노트북·워치 UK·CA가 해당합니다 |
   | `spec_only: true` | 판매 종료 모델처럼 스펙만 볼 컨텍스트입니다 |
   | `sections` | 섹션 제목을 표준 id로 묶는 정규식입니다. 매핑되지 않은 제목은 메뉴 구성 표에 원문으로 나오니, 보고 추가합니다. 추가한 패턴은 `build`만 다시 해도 반영됩니다 |
   | `key_specs` | 주요 스펙 비교 표의 행입니다. 라벨 정규식에 처음 맞는 스펙의 원문 값을 보여 줍니다 |

2. `.venv/bin/python -m tools.site_compare capture <상품>`으로 실행하고, 리포트에서 발견한 조합 수·섹션·스펙이 맞는지 봅니다.
3. `.venv/bin/python -m tools.site_compare snapshot <상품>`으로 픽스처를 저장합니다. 저장 직후 "OK"가 나와야 합니다. "OFFLINE DIFF"가 나오면 드라이버가 축약 DOM에서 다르게 읽는 부분이니 고칩니다.
4. `tests/site_compare/test_drivers_offline.py`에 그 상품의 사실 단언(예: 크기 목록, 기준 SKU)을, `test_live_categories.py`에 기준 조합 live 테스트를 추가합니다.
5. `cards/<상품>.yaml`에 차이점 카드를 씁니다.

Fold8처럼 축 값을 직접 적는 `click` 모드(`storages`, `colors`, `carriers`)도 그대로 동작합니다.

## 사이트가 바뀌었을 때

1. `.venv/bin/python -m tools.site_compare snapshot <상품>`으로 픽스처를 새로 저장합니다.
2. `.venv/bin/pytest`를 돌립니다. 실패한 케이스 이름(`<템플릿>/<상품>__<컨텍스트>`)이 어느 템플릿의 어느 값이 바뀌었는지 알려 줍니다.
3. 해당 드라이버(`sites/<템플릿>.py`)의 선택자를 고칩니다. `-m live`로 실제 사이트를 확인한 뒤 다시 snapshot을 저장합니다.

## 카드 형식 (`cards/<상품>.yaml`)

```yaml
cards:
  - id: price-format
    title: 가격 표기 형식
    tags: [국가별 구성 차이]          # 국가별 구성 차이 | 사이트 데이터 오류 | 소스 vs 화면 불일치 | CA-FR 번역
    panels:
      - combo: uk__77                  # data.json의 combo_id
        section: size                  # 섹션 id, full(전체 캡쳐 첫 조각), extra-1(레이어), spec / spec-2(스펙 캡쳐)
        highlight: ["£3,499.00"]       # 빨간 박스로 표시할 화면 텍스트(포함 여부로 찾음)
        caption: 선택 사항
    observation: |
      [사실] …
    note: |
      정규화·파이프라인 메모
```

다시 캡쳐한 뒤 카드가 가리키는 조합·섹션·텍스트가 없으면, 리포트의 해당 카드에 노란 경고가 표시됩니다.

## 결과 해석

| status | 의미 |
|---|---|
| ok | 의도한 조합이 선택되고 값이 기록됨. 경고가 있으면 가격 표 칸이 노란색이 되고 "경고 n" 칩이 붙음 |
| unavailable | 사이트가 그 옵션을 제공하지 않음(목록에 없음·비활성·안내 문구), 또는 판매 종료로 표시됨(가격 표에 "판매 종료") |
| mismatch | 화면 SKU나 선택 상태가 의도와 다르거나 CA 주 설정이 화면에 반영되지 않음 |
| error | 예외 발생, 선택 요소 자체를 못 찾음, 또는 가격·섹션·스펙을 하나도 읽지 못함(`nothing captured`) |

자주 보는 경고는 다음과 같습니다.

| 경고 | 의미 |
|---|---|
| `price not rendered` | 대기·새로고침 후에도 가격이 비어 있음 |
| `reloaded: price was missing` | 가격이 비어 한 번 새로고침했음(정상 수집) |
| `sku mismatch` | 직접 진입·선택 후 화면 SKU가 기대값과 다름 |
| `region mismatch` / `region not applied` | CA 주 설정이 화면에 반영되지 않음 |
| `redirected` | 다른 국가 사이트로 넘어감 |
| `no sections found` | 섹션 제목을 하나도 찾지 못함(사이트 구조 변경 가능성) |

## 문제 해결

- **봇 차단·빈 화면:** `--headed`로 다시 실행합니다.
- **일부 국가만 실패 (네트워크 끊김 등):** `--only <컨텍스트> --into <실행 id 또는 latest>`로 그 컨텍스트만 다시 캡쳐합니다. 나머지 결과는 그대로 두고 해당 컨텍스트 결과만 바뀝니다.
- **옵션 클릭이 먹지 않음:** 클릭 경로로 연 조합이 의도와 다르면 새 페이지에서 한 번 더 시도합니다(경고 `retried:`). 그래도 다르면 `mismatch`입니다.
- **CA 주:** 헤드리스에서는 주 선택 UI가 동작하지 않습니다. 그래서 사이트가 쓰는 `country_region` 쿠키로 지정하고, 화면 표시로 적용 여부를 확인합니다.
- **쿠키 동의:** 동의 버튼을 누르면 UK·CA 페이지가 다시 로드됩니다. 그래서 동의 쿠키를 페이지를 열기 전에 넣습니다(`capture.CONSENT_COOKIES`).
- **긴 페이지:** 전체 캡쳐는 4,000px, 스펙 캡쳐는 3,000px 조각으로 나눠 찍습니다. 한 장으로 크게 찍으면 Chrome에서 위치가 어긋납니다.
- **테스트:** `.venv/bin/pytest`는 오프라인 테스트만 실행합니다. 실제 사이트 테스트는 `-m live`를 붙이고, 한 번에 하나씩 돌립니다.
