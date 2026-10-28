# 국가별 화면 비교 캡쳐 도구 — 카테고리 확장 설계 (TV·세탁기·냉장고·노트북·워치)

- 작성일: 2026-10-28 (KST)
- 선행 설계: `docs/superpowers/specs/2026-10-28-site-capture-comparison-design.md` (Fold8 Ultra 1차). 이 문서는 그 설계를 확장하며, 충돌하는 부분은 이 문서가 우선합니다.
- 조사 근거: `docs/superpowers/research/2026-10-28-categories-recon.md`(카테고리별 URL·SKU·선택자·가격 형식·섹션·스펙·레이어·함정·카드 후보). 원자료(스크린샷·DOM 덤프)는 임시 위치(scratchpad `recon2/`)라, 오프라인 테스트용 픽스처는 `snapshot` 명령으로 새로 저장합니다.

## 1. 의도

Fold8 Ultra로 만든 도구를 TV, 세탁기, 냉장고, 노트북, 갤럭시워치로 넓힙니다. 사용자가 나라별 차이를 실제 화면으로 확인하고 CA·US 데이터 정규화와 파이프라인에 반영하는 목적은 같습니다. 이번에는 **스펙(사양표)** 도 함께 봅니다. 가전과 노트북은 스펙의 단위·라벨·값 차이가 정규화의 핵심이기 때문입니다.

사용자 요구: "추후 작업 때에 최소 변경만으로 수집 가능하도록". 따라서 이번 확장의 성공 기준은 다음과 같습니다.
- 같은 템플릿의 새 상품은 **상품 YAML 하나**만 추가하면 수집됩니다.
- 사이트 구조가 바뀌면 **어느 템플릿의 어느 부분이 깨졌는지 테스트가 바로 알려 줍니다**.

## 2. 목표 / 비목표 / 안티 목표

**목표**
- G1. 5개 카테고리 상품을 6개 컨텍스트(UK, CA-EN ON/QC, CA-FR ON/QC, US)에서, 가격이 달라지는 옵션 조합별로 캡쳐합니다.
- G2. 조합마다 구매 영역(섹션별 캡쳐, 가격, SKU, 레이어)과 **스펙**(펼친 스펙 섹션 캡쳐와 라벨·값 텍스트)을 기록합니다.
- G3. 상품별 리포트(기존 A안)에 **주요 스펙 비교 표**와 스펙 원문 부록을 더합니다. 모든 상품 리포트로 가는 **목차 페이지**를 둡니다.
- G4. 템플릿별 드라이버와 템플릿별 오프라인 테스트(실제 페이지에서 저장한 DOM)를 둡니다. 카테고리별 실제 사이트 테스트도 둡니다.
- G5. Fold8 Ultra 수집은 계속 동작해야 합니다. 기존 리포트·카드가 깨지지 않아야 합니다.

**비목표**
- 스펙 라벨의 완전한 국가 간 정렬 사전. 주요 필드만 규칙으로 묶고, 나머지는 원문으로 둡니다.
- 구매 진행, 로그인, 우편번호 여러 곳 비교, 모바일 화면.
- 카테고리마다 가능한 모든 모델. 상품 1개(+옵션 조합)씩입니다.

**안티 목표**
- 가격·섹션이 모두 비었는데 `ok`로 집계되는 것. 조사에서 기존 드라이버가 이 상태로 `ok`를 낸 사례가 여러 건 있었습니다.
- 다른 SKU(옵션 클릭 후 상태가 꼬인 페이지)의 가격·스펙을 의도한 조합의 값으로 기록하는 것.
- 긴 페이지의 깨진 전체 캡쳐를 정상 캡쳐로 쓰는 것.

## 3. 상품과 비교 대상 (사용자 결정 포함)

| 상품 id | UK | CA-EN·CA-FR | US | 조합(가격이 달라지는 옵션 전부) |
|---|---|---|---|---|
| `tv_s95h` | QE77S95HFTXXU ([URL](https://www.samsung.com/uk/tvs/oled-tv/s95h-77-inch-4k-smart-tv-qe77s95hftxxu/)) | QN77S95HAFXZC (CA-EN slug `s95ha-…`, CA-FR slug `s95h-…`, 서로 유도 불가) | QN77S95HAFXZA | **크기 전부**: UK 48/55/65/77, CA·US 55/65/77/83. US의 시리즈 타일(S85H/S90H)은 제외 |
| `washer_flagship` | **두 컨텍스트**: `uk` = WF90H11C4WT1(판매 중, 주신 URL), `uk-f` = WF90F09C4SU1(같은 F세대, 판매 종료 — 스펙 비교용) | WF90F53ADSA5 | WF90F53ADSA5 | **색상 전부**: UK H는 Neat white/Dark steel(Dark steel은 판매 종료 표시), US Dark Steel/Ivory, CA 1색 |
| `fridge_t_style` | RF65DG960ESREU | RF23DG9600SRAC (같은 DG960 플랫폼) | RF23DB9600QLAA (Bespoke 변형) | UK **색상** Silver/Black, US **깊이** Counter/Full(RF29DB9600QLAA), CA 1개 |
| `laptop_book6_pro` | NP960XJG-KGAUK (시리즈 구매 페이지 `galaxy-book6-series/buy/?modelCode=`) | NP960XJG-KG1CA (CA에 Ultra X7 구성이 없어 가장 가까운 Ultra 7 356H, 32GB/1TB) | NP960XJG-KG1US (동일) | **기준 구성 1개** |
| `watch9` | SM-L340NZKAEUB (구매 페이지 `/uk/watches/galaxy-watch9/buy/`) | SM-L340NZKAXAC | SM-L340NZKAXAA | **크기 × 연결**: 40/44mm × Bluetooth/LTE, 색상 Graphite 고정 |

- US 지역은 우편번호 **10001**(뉴욕) 하나입니다(사용자 결정). 한국 IP 기본값(14044)에서는 TV·냉장고가 "구매 불가"로 나오고 배송 옵션이 비어서, 쿠키 `eddzipcode=10001`로 지정합니다.
- 카드에는 "동일 모델이 아님"을 명시합니다. 대상은 세탁기 세대 차이, 노트북 CA 프로세서, TV 하드웨어 변형(UK One Connect Box vs NA Wireless One Connect)입니다.
- 정확한 URL·SKU는 조사 결과 문서에 있고, 빌더가 상품 YAML로 옮깁니다. 조합 값은 페이지에서 **발견**합니다(5.2).
- `uk-f`(WF90F09C4SU1)는 판매 종료라 **스펙 전용 컨텍스트**입니다. 조합 1개를 캡쳐하고, 상태는 `unavailable`로 둡니다. 가격 표에서는 '판매 종료'로 표시합니다.
- **기준 SKU**(주요 스펙 비교 표와 카드의 기본 비교 대상)
  - TV: 77"
  - 세탁기: UK WF90H11C4WT1 / UK-F WF90F09C4SU1 / CA WF90F53ADSA5 / US WF90F53ADSA5(Dark Steel)
  - 냉장고: UK Silver / CA RF23DG9600SRAC / US RF23DB9600QLAA(Counter depth)
  - 노트북: 표의 구성 그대로
  - 워치: 40mm Bluetooth Graphite

## 4. 확인된 페이지 템플릿 (조사 사실)

| 템플릿 | 쓰이는 곳 | 핵심 구조 |
|---|---|---|
| **hubble** (기존) | Fold8(UK/CA/CA-FR), 노트북 시리즈 구매(UK/CA/CA-FR) | `input.hubble-pd-radio__input`, `h2.s-option-title`, `.hubble-price-bar`, `.hubble-product__summary` |
| **pd** (신규) | TV·세탁기·냉장고 PDP(UK/CA/CA-FR) | `section.hdd02-buying-tool > .hdd02-buying-tool__option > .pd-select-option`(제목 `h3.pd-select-option__headline`, 치수는 `p.pd-sellout-option__headline`), 가격 바 `.pdd39-anchor-nav`, 요약 `.hdd02-buying-tool__summary`/`.cost-box`, 스펙 `section#specs.pdd32-product-spec` |
| **watchbc** (신규) | 워치 구매(UK/CA/CA-FR) | `.watch-bc-option__option[data-type-code]`(C-SIZ, C-CON, C-CLR …), `label.option-select[for]`, 가격 바 `strong.bar-total-price`, 요약 `.total-summary .model-code`, 기타 블록 `.watch-bc-buyflow` |
| **us** (기존, 일반화) | Fold8·노트북·워치 구매(US, Next.js) | `-sku-<model>/` URL, 타일 `data-modeldisplay`/`aria-label`/`an-la`, 요약 블록. 휴대폰 전용(`SM-…`) 정규식이 문제 |
| **us_pdp** (신규) | TV·세탁기·냉장고 PDP(US, Next.js `templateType: VD`) | 타일 `[data-testid=SeriesTile|sizeTileSelect][role=radio]`(`aria-checked`, `data-modelcode`), 섹션 `[role=heading][aria-level="2"]`, 요약 `#product-summary`, 결제 카드 `[data-testid=paymentCardClass]`, 레이어 `[class*=Overlay_dialog]`, 스펙 `[class*=Specs_subSpecItemName]` |

**스펙 위치**
- pd 템플릿 상품은 같은 페이지에 있습니다(모든 항목이 DOM에 있고 접혀 있음, "Expand all").
- 노트북·워치의 UK/CA/CA-FR은 구매 페이지가 아니라 **PDP**(`pdd32`)에 있습니다.
- US는 같은 페이지의 스펙 영역(스크롤 후 로드, 노트북·워치는 아코디언 클릭 후 주입)에 있습니다.

**공통 함정 (조사에서 반복 확인)**
- **쿠키 동의 클릭 후 페이지가 다시 로드됩니다**(CA·UK). "Execution context was destroyed"가 납니다. 동의 쿠키를 미리 넣으면 배너도 재로드도 없습니다: `notice_preferences=0:`, `notice_gdpr_prefs=0::implied,eu`, `notice_behavior=implied,eu`, `cmapi_cookie_privacy=permit 1 required`.
- **16,384px를 넘는 페이지를 한 장으로 캡쳐하면 깨집니다.** 반복되거나, 비거나, 위쪽이 다른 내용으로 찍힙니다. 페이지 높이는 TV 38~44k, 가전 23~27k, 워치 PDP 44k px입니다.
- **옵션 클릭 후 상태가 꼬일 수 있습니다.** 워치 UK 44mm가 £334(케이스 전용 코드)로 표시됐고, CA-FR에서는 LTE를 눌러도 Bluetooth SKU에 머물렀습니다. US 통신사 타일 문제(1차)도 같은 종류입니다.
- **US 레이어 판별:** 빈 `SupportedLanguagesPopup` `[role=dialog]`가 항상 화면 전체를 덮습니다.
- **사이트별 가격 표시**
  - CA 일부 페이지는 `{{...}}` 자리표시자가 7초 넘게 남습니다.
  - 퀘벡 TV는 가격이 $21.10 높지만 JSON-LD는 Ontario 가격입니다.
  - UK TV JSON-LD 가격은 RRP입니다.
  - US 일부 월 할부 문구에는 `$`가 없습니다(예: "or 15.83/mo").

## 5. 설계

### 5.1 조합은 "SKU별로 연 페이지"가 기본 (내 판단)

조사 결과 모든 사이트가 조합별 직접 진입을 지원합니다.
- hubble: `?modelCode=<SKU>`
- watchbc: `/buy/?modelCode=<SKU>`
- US: `-sku-<sku>/` URL
- pd: 옵션 input의 `data-modelcode`와 클릭 결과 URL

반면 옵션 클릭은 상태가 꼬이는 사례가 반복됐습니다. 그래서 새 카테고리는 **조합마다 해당 SKU 상태로 페이지를 새로 열고, 화면의 SKU가 기대 SKU와 같은지 검증**하는 방식을 기본으로 합니다.
- 직접 URL이 없는 경우(pd 템플릿의 크기·색상)는 기본 URL을 연 뒤 해당 옵션을 클릭하고 SKU 변경을 기다립니다.
- Fold8은 기존 클릭 방식을 그대로 둡니다. 결과가 이미 검증됐습니다.

### 5.2 조합 발견 (내 판단)

나라마다 옵션 값이 다릅니다(TV 크기 UK 48~77, CA·US 55~83). 그래서 상품 YAML에는 **반복할 축 이름**만 적고, 값은 컨텍스트별로 페이지에서 발견합니다.

드라이버는 `options(page, axis)`를 구현하고 `[{value, label, sku, url?, available}]`을 돌려줍니다. 오케스트레이터는 다음 순서로 동작합니다.
1. 기본 페이지를 엽니다.
2. 축별 옵션을 발견합니다.
3. 데카르트 곱(고정 축은 고정값)으로 조합을 만듭니다.
4. 조합마다 캡쳐합니다.

- **판매 불가 옵션:** 발견됐지만 판매 불가(예: UK 세탁기 Dark steel "No longer available")인 조합도 캡쳐하고 `unavailable`로 둡니다.
- **조합 수 확인:** 발견한 조합 수는 실행 로그와 리포트 머리말에 컨텍스트별로 표시합니다. 사용자가 범위를 확인할 수 있게 하려는 것입니다.

### 5.3 데이터 모델 일반화

- `State`: `storage/color/carrier`를 **`selection: dict[str, str]`**(축 이름 → 화면 표시값)로 바꿉니다. `sku`, `region`, `prices`는 그대로입니다.
- `ComboResult`
  - `full_shot: str` → **`full_shots: list[str]`**(조각 캡쳐).
  - **`specs: list[SpecItem(group, label, value)]`**와 스펙 캡쳐 `spec_shots`를 추가합니다.
  - 상태 판정에 "가격 없음 + 섹션 없음 → `error`"를 추가합니다.
- 기존 Fold8 `data.json`은 새 모델로 읽을 수 있어야 합니다. 기존 필드에서 변환합니다.
- 상품 YAML 스키마는 축 정의를 일반화합니다(`axes:` 목록, 축별 `iterate | fixed | check`, 값 별칭·코드). Fold8 YAML은 새 스키마로 옮깁니다.

### 5.4 드라이버

| 드라이버 | 작업 |
|---|---|
| `hubble` | 노트북 대응 수정: 라디오 name 앞뒤 공백, `html.unescape`, 색상은 `data-color`/SKU로 판정(CA-FR 영어명 "Gris"), was는 가격 바 `.hubble-price-bar__price-total-save-inner`, 숨겨진 옵션은 선택 불가 |
| `pd` (신규) | 옵션 축 `pd-size`, `pd-color`, `pd-others-*`. SKU는 `.pdd39-anchor-nav__info-sku` 또는 CTA `data-modelcode`. 가격은 `.pd-buying-price__*`. 섹션은 `.hdd02-buying-tool__option` 자식들. 스펙은 Expand all 후 `pdd32`. 레이어는 금융 계산기, 트레이드업, 치수 측정, Care+ |
| `watchbc` (신규) | `?modelCode=` 진입 후 SKU 검증. 섹션은 `.watch-bc-option__option`, `.watch-bc-buyflow`, `.total-summary`. 스펙은 PDP |
| `us` (일반화) | SKU 정규식 일반화(`-sku-([a-z0-9-]+)`, 요약 `X / Y`). 선택 상태는 선택된 타일(`an-la`, `aria-checked`, selected 클래스)에서 읽음. 월 할부의 `$` 생략 허용. 스펙 아코디언 |
| `us_pdp` (신규) | 4장의 VD 구조. `eddzipcode` 쿠키. 레이어 판별에서 `SupportedLanguagesPopup` 제외 |

**공통 준비 단계:** 페이지를 열기 전에 동의 쿠키, 주 쿠키, US 우편번호 쿠키를 넣습니다. 이후 동의 배너가 보이면 JS로 클릭합니다. 지역 표시 바와 채팅 팝업은 닫습니다. US 채팅 팝업은 1차에서 남겨 둔 Minor였습니다.

### 5.5 스펙

- **위치:** 같은 페이지에 스펙이 있으면 조합마다 수집합니다(TV 크기마다 치수·무게가 다름). 스펙이 다른 페이지(노트북·워치 UK/CA/CA-FR PDP)에 있으면 컨텍스트별 기준 SKU 1회만 수집합니다.
- **수집 절차:** 펼치기 → 스펙 영역 조각 캡쳐 → 라벨·값 텍스트 추출.
- **주요 스펙 비교 표의 칸에는 컨텍스트별 기준 SKU(3장)의 값을 넣습니다**(내 판단). 다른 조합(TV 다른 크기, US 냉장고 Full depth, 워치 44mm·LTE 등)의 스펙은 부록에 조합별 원문 표로 둡니다. 스펙은 같은 페이지에 있으면 조합마다 저장하고(`ComboResult.specs`), 별도 PDP에 있으면 기준 SKU 조합에 붙입니다.
- **주요 스펙 규칙:** 상품 YAML에 `key_specs`(표준 필드 → 언어별 라벨 정규식)를 둡니다. 예: `capacity: ["washing capacity", "capacité de lavage", "washer capacity"]`. 리포트의 "주요 스펙 비교" 표는 행이 표준 필드, 열이 컨텍스트이고, 칸에는 원문 값을 넣습니다. 규칙에 걸리지 않은 항목은 부록 원문 표에 남습니다.

### 5.6 캡쳐

- **전체 캡쳐:** 8,000px 이하 조각으로 나눠 찍습니다. 위에서부터 차례로 찍고, 찍기 전에 끝까지 스크롤해 지연 로딩을 풀어 둡니다.
- **섹션 클립:** 페이지 폭을 넘지 않게 자르고, 실제 PNG 크기를 기록합니다. 1차 Minor(하이라이트 위치 어긋남)도 함께 해결됩니다.

### 5.7 리포트

- **상품별 리포트:** 기존 구조에 두 가지를 더합니다.
  - 요약에 "주요 스펙 비교" 표
  - 부록에 컨텍스트별 스펙 원문 표와 스펙 캡쳐

  US 열은 상품별로 정합니다. Fold8은 Unlocked/Verizon이고, 새 상품은 `us` 하나입니다.
- **목차:** `out/site_compare/index.html`에 상품별 최신 실행, 상태 요약, 리포트 링크를 둡니다. 실행·빌드할 때마다 갱신합니다.
- **카드:** 상품별 카드는 캡쳐 후 내가 작성합니다(상품당 5~10개). 조사 단계에서 나온 후보를 우선 확인합니다(8장).

### 5.8 테스트 (사용자 요구: 카테고리별 충분히)

- **템플릿 픽스처**
  - 저장 대상: 각 템플릿의 실제 렌더링 DOM(스크립트 제거, 구매 영역·가격 바·요약·스펙만 남긴 축약본)을 `tests/site_compare/fixtures/<template>/<product>_<ctx>.html`에 저장합니다.
  - 저장 명령: `python -m tools.site_compare snapshot <product>`
  - 사이트가 바뀌면 이 명령으로 픽스처를 다시 저장하고, 오프라인 테스트로 무엇이 깨졌는지 확인합니다.
- **오프라인 드라이버 테스트**(템플릿 × 상품 × 컨텍스트 매개변수화)
  - `options()` 발견 값
  - 현재 선택·SKU·가격 4종 파싱
  - 섹션 제목 목록과 표준 id 매핑
  - 스펙 항목 수와 대표값
  - 레이어 열기용 선택자 존재 여부
- **오프라인 공통 테스트**: 조합 발견, 상태 판정(가격·섹션 없음 → error 포함), 조각 캡쳐, 주요 스펙 표, 목차, 구 `data.json` 읽기.
- **실제 사이트 테스트**(`-m live`): 상품마다 대표 조합 1~2개(UK·CA-QC·US)를 캡쳐해 다음을 확인합니다.
  - SKU와 가격 일치
  - 주요 섹션 존재
  - 스펙 수집
- **Fold8 회귀**: 기존 오프라인·live 테스트를 모두 유지합니다.

## 6. 빌더에게 맡기는 것

- 선택자 세부, 대기·재시도 정책, 픽스처 축약 방식, 내부 모듈 구조, 파일 형식
- 상품 YAML의 정확한 URL과 SKU(조사 원자료에 있음), 섹션 규칙 정규식(조사 보고서에 후보 있음)
- 리포트 스타일

## 7. 결정 기록

**사용자가 정한 것**
- 범위: 구매 영역 + 스펙
- 조합: 가격이 달라지는 옵션 전부(노트북은 기준 구성 1개)
- 세탁기: UK는 WF90H(판매 중, 가격·구매 단계 비교)와 WF90F09C4SU1(판매 종료, 같은 세대 스펙 비교) 두 모델. CA·US는 WF90F53ADSA5
- US 우편번호: 10001 하나

**내가 정한 것 (확인 대상)**
- 새 카테고리 조합은 SKU별 직접 진입 + SKU 검증이 기본입니다. Fold8은 클릭 방식을 유지합니다.
- 조합 값은 페이지에서 발견합니다. YAML에는 축 이름만 적습니다.
- US 시리즈 타일(TV S85H/S90H)은 조합에서 제외합니다.
- 워치 색상은 Graphite로 고정합니다(40·44mm 모두 있는 색).
- 스펙이 별도 PDP에 있는 노트북·워치는 컨텍스트당 기준 SKU 1회만 수집합니다.
- 주요 스펙 비교 표는 기준 SKU 값입니다. 다른 조합의 스펙은 부록에 둡니다.
- 판매 종료 UK F세대 세탁기는 스펙 전용 컨텍스트로 둡니다(상태 `unavailable`).
- 템플릿별 실제 DOM 축약 픽스처와 `snapshot` 명령을 둡니다.
- 목차 페이지를 둡니다.

## 8. 조사 단계에서 나온 카드 후보 (캡쳐로 재확인)

- **TV**
  - 퀘벡 +$21.10이 붙는데 정가·JSON-LD는 Ontario 가격입니다.
  - UK JSON-LD 가격은 RRP라 화면 가격과 다릅니다.
  - CA-EN 치수가 mm 값인데 "inch"로 표기됩니다.
  - 트레이드인은 UK에만, Care+는 CA·US에만 있습니다.
  - 월 할부는 CA-EN Ontario에서만 보입니다.
  - US JSON-LD의 `productGroupID`가 사운드바 ID입니다.
  - 하드웨어 변형: UK One Connect Box vs NA Wireless One Connect.
- **세탁기**
  - 같은 모델 WF90F53ADSA5인데 CA 6.1 cu ft, US 5.3 cu ft입니다.
  - CA-FR 무게가 "102 lbs"(실제 kg), 치수 라벨이 "(H x L x P)"입니다.
  - US 배송 레이어 치수 라벨이 뒤바뀌어 있습니다.
  - UK 판매 종료 표시 / 에너지 라벨 체계 차이(EU 등급 vs Tier·ENERGY STAR·CEE).
- **냉장고**
  - 용량 기준이 다릅니다: UK 총용량(gross) ℓ, CA 실용량(net) cu ft, US total cu ft.
  - CA에 화면에 안 나오는 MSRP $3,899.99가 있습니다.
  - US 할인액이 우편번호에 따라 달라집니다.
  - US Open Box 가격이 있습니다.
- **노트북**
  - CA에는 Ultra X7 구성이 없습니다.
  - 같은 값의 표기가 다릅니다: 1TB / 1 TB, Grey / Gray / Gris.
  - CA 비교 블록 부제가 "Compare the latest Galaxy Z Series smartphones"입니다.
  - US 14" 월 할부 문구에 `$`가 없습니다.
  - CA was 가격이 JSON-LD에는 없습니다.
- **워치**
  - CA-FR에서 케이스 크기를 "Taille de la valise"(여행가방 크기)로 번역했습니다.
  - CA-EN Watch9 배너에 "Galaxy Watch Ultra2"가 나옵니다.
  - bare /buy/의 기본 변형이 나라마다 다릅니다(UK LTE, CA BT, US 44mm).
  - US LTE에는 통신사 선택이 없습니다.
  - US 월 할부 문구에 `$`가 없습니다.
