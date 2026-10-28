# site_compare: 국가별 Samsung.com 화면 비교 캡쳐

같은 상품을 국가·지역·옵션 조합별로 실제 브라우저에서 열어 캡쳐하고, 차이점 카드가 들어간 `report.html`을 만드는 도구입니다. 설계는 `docs/superpowers/specs/2026-10-28-site-capture-comparison-design.md`에 있습니다.

## 설치

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

브라우저는 PC에 설치된 Google Chrome을 사용합니다(`channel="chrome"`). 따라서 `playwright install`은 필요 없습니다.

## 실행

저장소 루트에서 실행합니다.

```bash
.venv/bin/python -m tools.site_compare capture fold8_ultra                # 전체 캡쳐 후 리포트 생성
.venv/bin/python -m tools.site_compare capture fold8_ultra --only uk,us   # 일부 컨텍스트만
.venv/bin/python -m tools.site_compare capture fold8_ultra --headed       # 브라우저 창을 띄워서 (봇 차단 시)
.venv/bin/python -m tools.site_compare build fold8_ultra                  # 카드만 고친 뒤 최신 캡쳐로 리포트 재생성
.venv/bin/python -m tools.site_compare build fold8_ultra --run 20261028-091500
```

- 결과는 `out/site_compare/<상품>/<실행시각>/`에 저장됩니다. 들어가는 파일은 `report.html`, `data.json`, `shots/*.png`입니다.
- 실행이 끝나면 마지막 줄에 `report.html` 경로가 출력됩니다.
- 전체 실행(Fold8 Ultra, 조합 39개)은 20~30분 걸립니다. 페이지 로드 후와 옵션 클릭 후 각각 5초씩 대기하기 때문입니다.

## 상품 추가

1. `products/<상품>.yaml`을 만듭니다. `fold8_ultra.yaml`을 복사해서 고치면 됩니다.
   - `storages`, `colors`(색상명 → SKU 색상코드), `fixed_color`: 조합 축을 정합니다.
   - `carriers`: `driver: us` 컨텍스트에만 적용됩니다.
   - `contexts`: 국가·언어·지역별 URL입니다. `driver`는 `hubble`(UK/CA/CA-FR) 또는 `us`이고, CA는 `region: CA-ON` 형식으로 씁니다.
   - `sections`: 페이지에서 찾은 섹션 제목을 표준 id로 묶는 정규식입니다. 매핑되지 않은 제목은 리포트의 메뉴 구성 표에 원문 그대로 표시되므로, 그걸 보고 규칙을 추가하면 됩니다.
2. `cards/<상품>.yaml`을 만듭니다. 처음에는 `cards: []`로 두고, 캡쳐를 본 뒤 카드를 씁니다.
3. 가전처럼 구매 구성기가 다른 페이지는 드라이버(`sites/hubble.py`, `sites/us.py`)에서 선택자와 섹션 찾는 방식을 맞춰야 할 수 있습니다.

## 카드 형식 (`cards/<상품>.yaml`)

```yaml
cards:
  - id: price-format
    title: 가격 표기 형식
    tags: [국가별 구성 차이]          # 국가별 구성 차이 | 사이트 데이터 오류 | 소스 vs 화면 불일치 | CA-FR 번역
    panels:
      - combo: uk__256gb               # data.json의 combo_id
        section: storage               # 섹션 id, full(전체 캡쳐), extra-1(첫 번째 펼친 레이어)
        highlight: ["£1,899.00"]       # 빨간 박스로 표시할 화면 텍스트(포함 여부로 찾음)
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
| unavailable | 사이트가 그 옵션을 제공하지 않음(목록에 없음·비활성·"unavailable" 안내 문구)이 확인되고, 최종 선택 상태도 다름. 예: 1TB Graphite + Verizon |
| mismatch | 근거 없이 최종 선택 상태가 의도와 다르거나 CA 주 설정이 화면에 반영되지 않음 |
| error | 예외 발생. 선택 요소 자체를 못 찾은 경우(사이트 구조 변경 가능성)도 포함 |

자주 보는 경고는 다음과 같습니다.

| 경고 | 의미 |
|---|---|
| `price not rendered` | 5초를 두 번 기다려도 가격이 비어 있음 |
| `region mismatch` / `region not applied` | CA 주 설정이 화면에 반영되지 않음 |
| `redirected` | 다른 국가 사이트로 넘어감 |
| `no sections found` | 섹션 제목을 하나도 찾지 못함(사이트 구조 변경 가능성) |

## 문제 해결

- **봇 차단·빈 화면:** `--headed`로 다시 실행합니다.
- **CA 주:** 헤드리스에서는 주 선택 UI가 동작하지 않습니다. 그래서 사이트가 쓰는 `country_region` 쿠키로 지정하고, 화면 표시로 적용 여부를 확인합니다.
- **선택자 변경:** 사이트 구조가 바뀌면 다음 파일을 고칩니다.
  - `sites/hubble.py`: `STORAGE`, `COLOR`, `_SECTIONS_JS`
  - `sites/us.py`: `select()`, `_SECTIONS_JS`

  고친 뒤 `.venv/bin/pytest -m live tests/site_compare/test_live.py`로 확인합니다.
- **테스트:** `.venv/bin/pytest`는 오프라인 테스트만 실행합니다. 실제 사이트 테스트는 `-m live`를 붙입니다.
