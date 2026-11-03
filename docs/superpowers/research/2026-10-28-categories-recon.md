# 카테고리별 페이지 조사 결과 (2026-10-28)

이 문서는 TV·세탁기·냉장고·노트북·워치 페이지를 실제로 열어 조사한 결과입니다. 설계(`docs/superpowers/specs/2026-10-28-site-compare-categories-design.md`)와 드라이버 구현의 근거로 씁니다.

- 조사 방법: Playwright(설치된 Chrome, 헤드리스, 1440×1000), 로드 후 5초 대기, 쿠키 동의 처리, 끝까지 스크롤, 기존 드라이버(HubbleDriver·UsDriver) 시험 실행
- 원자료(임시 위치): scratchpad `recon2/<category>/`. 스크린샷, 렌더링 DOM, 프로브 스크립트가 있습니다.
- 사이트는 자주 바뀝니다. 선택자는 이 날짜 기준이고, 바뀌면 `snapshot` 픽스처와 live 테스트로 확인합니다.

## 공통 사실

### 동의 쿠키
TrustArc 동의 쿠키를 `.samsung.com`에 미리 넣으면 배너도 재로드도 없습니다(UK·CA·US).

| 쿠키 | 값 |
|---|---|
| `notice_preferences` | `0:` |
| `notice_gdpr_prefs` | `0::implied,eu` |
| `notice_behavior` | `implied,eu` |
| `cmapi_cookie_privacy` | `permit 1 required` |

배너를 클릭하면 CA·UK에서 1~2초 뒤 전체 재로드가 자주 일어납니다("Execution context was destroyed").

### 지역 쿠키
- CA 주: `country_region=CA-ON|CA-QC`. 쿠키가 없으면 Ontario입니다. 주 표시는 `button.menu__select-field[data-aria-label="change region"]`이고, 값은 Ontario / Quebec / Québec입니다.
- US 우편번호: `eddzipcode=10001`. 한국 IP의 기본값은 14044이고, 이 상태에서는 TV·냉장고가 "not available in your area"로 나오며 장바구니가 비활성입니다.

### 페이지 길이
- 높이: TV 38~44k, 가전 23~27k, 워치 PDP 약 44k, 구매 페이지 14~18k px
- `full_page=True` 한 장 캡쳐는 16,384px를 넘으면 깨집니다(반복·공백·위쪽이 다른 내용). 클립 캡쳐는 정상입니다.

### 화면 요소
- 지역 표시 바: `aside.nv16-country-selector`(약 73px). 닫기 버튼은 `.nv16-country-selector__close`입니다.
- 채팅 말풍선: 화면 왼쪽 아래.

### 기존 드라이버 결과
- HubbleDriver: pd·watchbc 템플릿에서 `read_state`가 전부 None, 섹션 0개입니다. 조합 축이 없으면 경고만 남고 `ok`로 집계됩니다(거짓 ok).
- UsDriver: `SM-` 전용 정규식이라 SKU·선택 상태를 못 읽습니다. 요약 감지도 `SM-` 기준이라 요약을 지나 마케팅 영역까지 섹션으로 잡습니다.

## 1. TV — Neo QLED/OLED S95H 77"

### 비교 대상

| 사이트 | URL | SKU |
|---|---|---|
| UK | https://www.samsung.com/uk/tvs/oled-tv/s95h-77-inch-4k-smart-tv-qe77s95hftxxu/ | QE77S95HFTXXU |
| CA-EN | https://www.samsung.com/ca/tvs/oled-tv/s95ha-77-inch-4k-smart-tv-qn77s95hafxzc/ | QN77S95HAFXZC |
| CA-FR | https://www.samsung.com/ca_fr/tvs/oled-tv/s95h-77-inch-4k-smart-tv-qn77s95hafxzc/ | QN77S95HAFXZC |
| US | https://www.samsung.com/us/tvs/oled-tv/77-inch-oled-4k-tv-s95h-sku-qn77s95hafxza/ | QN77S95HAFXZA |

- CA-EN slug는 `s95ha-…`, CA-FR slug는 `s95h-…`입니다. `/ca/…/s95h-77-…`는 404라 URL을 서로 유도할 수 없습니다.
- `/buy/` 페이지는 없습니다(404).
- 하드웨어가 다른 변형입니다.

| 항목 | UK | NA (CA·US) |
|---|---|---|
| 연결 박스 | One Connect Box(Y24) | Wireless One Connect Ready |
| 스탠드 | Slim OC stand | Round Feet |
| 폭 | 1716.6 mm | 1782.6 mm |
| 깊이 | 11.2 mm | 26.6 mm |
| 스탠드 제외 무게 | 28.2 kg | 31.7 kg |

### UK·CA·CA-FR: pd 템플릿

**옵션: 크기만 있음**
- 선택: `input[name='pd-size']`(id `pd-size-N`, `data-modelcode`). `label[for]`를 클릭합니다.
- 체크된 input의 `data-modelprice`는 RRP, `data-discountprice`는 판매가입니다.
- 값: UK 48/55/65/77(48"는 QE48S95HHEXXU), CA 55"/65"/77"/83"(83"은 QN83S95HAEXZC).
- 클릭하면 페이지 안에서 AJAX와 pushState로 바뀝니다. URL slug, H1, 가격, CTA `data-sku-code`, `.pdd39-anchor-nav__info-sku`, JSON-LD가 모두 갱신됩니다.
- `#anchorNavigationPriceBar[data-model-code]`는 77" 그대로 남습니다. 쓰지 않습니다.

**가격**

| 사이트 | 표시 |
|---|---|
| UK | `£3,499.00`, `RRP: £3,699.00`(`.pd-buying-price__was`), `Save £200.00`(`.pd-buying-price__save`) |
| CA-EN Ontario | `From $187.50/mo for 24 mos or $4,499.99` |
| CA-EN Quebec | `$4,521.09` |
| CA-FR (ON / QC) | `4 499,99 $` / `4 521,09 $` |

- 가격 요소: `#sgDevPriceAreaBase .pd-buying-price__new-price-currency`
- CA-EN Ontario의 월 할부는 부모 `.pd-buying-price__new-price-inner`의 자체 텍스트입니다.
- CA was·save는 `.pd-buying-price__text-saving-info`에 `$5,999.99 Save $1,500.00` 형태로 나옵니다.
- 요약: `.cost-box__price-now`. CA는 리워드 행(`4,500 p`)이 있습니다.
- UK 월 할부는 레이어에만 있습니다. "0% Finance available, view options"(`a[data-target-popup=eipPopup]`)를 누르면 PayPal 18/24/36개월이 나옵니다.

**JSON-LD**
- Product 하나에 Offer 하나, strikethrough는 없습니다.
- UK는 `price`가 3699(RRP)라 화면 가격 £3,499와 **불일치**합니다.
- CA는 4499.99로 Ontario와 같고, Quebec($4,521.09)과는 **불일치**합니다.

**구매 섹션 (순서대로)**
- UK: Choose your size → 배송일 문구 → "Want up to £250.00 off? Recycle your old TV…"(트레이드인) → Add-on Items → Pre-purchase check → 오퍼 목록(제목 없음) → gocertify → 요약
- CA-EN: Choose your size → Samsung Care+ → Personalize your TV → Add-on Items → Pre-purchase check → 요약
- CA-FR: Choisissez votre taille → Samsung Care+ → Personnalisez votre téléviseur → Éléments complémentaires → Vérification avant l'achat → 요약

**스펙**
- 위치: `section.pdd32-product-spec#specs`. 모든 항목이 DOM에 있고 접혀 있습니다.
- 펼치기: `.pdd32-product-spec__expand-cta button`("Expand all" / "Développer tout")
- 라벨·값: `.pdd32-product-spec__content-item-title` / `-desc`
- 항목 수: UK 17그룹 114개, CA-EN 16그룹 131개, CA-FR 16그룹 132개
- CA-EN 치수 값 `1782.6 x 1089.6 x 319.9 inch`는 실제로는 mm입니다(**단위 오류**).

**레이어**
- UK 트레이드인 "Learn more"와 금융 계산기: `.layer-popup[role=dialog]`, 캡쳐 대상은 `.layer-popup__inner`
- 추가 상품 "View more": `button[data-js-action=offerListViewMore]`
- CA 리워드 툴팁: `button.pd-select-option__tooltip__cta`

**지역**
- 퀘벡은 모든 TV 크기에서 **+$21.10**입니다(사운드바 +$3.75) [추정: 환경 부담금].
- 퀘벡 was·save 문구는 Ontario 기준 그대로입니다($5,999.99, Save $1,500.00). 퀘벡의 `data-modelprice`는 6021.09입니다.
- 월 할부는 CA-EN Ontario에서만 보입니다. CA-FR은 Ontario에서도 없습니다.

### US: us_pdp 템플릿 (Next.js, `templateType: VD`)

**옵션**
- 모델: `[data-testid=SeriesTile][role=radio]`(`data-modeldisplay`는 `oled s95h 4k` 등, `aria-checked`)
- 크기: `[data-testid=sizeTileSelect][role=radio][aria-label='Size: 77"']`. "See All Specs"에도 같은 testid가 붙어 있어 반드시 `[role=radio]`를 같이 씁니다.
- 클릭하면 약 4초 뒤 새 `-sku-` URL로 바뀝니다.

**가격**
- 헤더 `[class*=PriceInfoText_priceInfo]`: `$3,699.99 was $4,499.99 Save $800.00`
- 모델 `[class*=ModelInfo_modalInfo]`: `QN77S95HAF / QN77S95HAFXZA`
- 결제 카드 `[data-testid=paymentCardClass]`: `One-time Payment $3,699.99`, `Pay Monthly $154.18/mo for 24 mos ⊕σ`, `Pay in 4 Payments $925.00 every two weeks σπΩ`
- 요약 `#product-summary`: `Total`, `[class*=Summary_totalprice]`

**JSON-LD**
- ProductGroup(variesBy size)에 variant `{sku, price 3699.99, StrikethroughPrice 4499.99}`. 화면과 일치합니다.
- 오류: `productGroupID`가 `"585198-q-series-q990f"`(사운드바)입니다. url만 있는 빈 variant도 있습니다.

**섹션**: `[role=heading][aria-level="2"]` 순서대로 Model → Select a size → Offers → Samsung care+ → Delivery options for: → Enhance your experience → Payment options(+ Galaxy Card) → `#product-summary` → Highlights(여기부터 구매 영역 아님)

**스펙**
- 위치: `#\#specs`. 버튼 `a[class*=Specs_expandBtn]`
- 그룹 `[class*=Specs_specGroupName]`, 항목 `[class*=Specs_subSpecsItem__]`, 이름 `[class*=Specs_subSpecItemName] > div`, 값 `[class*=Specs_subSpecsItemValue]`
- 17그룹 139개. 단위는 in/lb이고 VESA만 mm입니다.

**레이어**
- 모두 `[class*=Overlay_wrapper]` 안의 `role=dialog`로 열리고 Escape로 닫힙니다.
- 대상: Care+ Terms(`button[class*=CarePlus_ux2Anchor]`), Delivery Learn More, 우편번호 모달, Galaxy Card
- Galaxy Card 레이어 안의 "Pre-qualify now"는 누르지 않습니다.

## 2. 세탁기

### 비교 대상

| 컨텍스트 | URL | SKU | 상태 |
|---|---|---|---|
| UK (H세대, 판매 중) | https://www.samsung.com/uk/washers-and-dryers/washing-machines/wf90h24-11kg-white-wf90h11c4wt1/ | WF90H11C4WT1 Neat white(Dark steel WF90H11C4ST1는 "No longer available") | £1,049, RRP £1,149 |
| UK (F세대, 판매 종료) | https://www.samsung.com/uk/washers-and-dryers/washing-machines/wf90f24-front-load-washer-a-55-percent-energy-efficiency-ai-home-ai-wash-9kg-silver-wf90f09c4su1/ | WF90F09C4SU1(Dark Steel 1색) | 화면·CTA "No longer available", JSON-LD offer 없음 |
| CA-EN | https://www.samsung.com/ca/laundry/washing-machines/wf90f27-front-loading-ai-home-ai-optiwash-plus-ultra-capacity-6-1-cu-ft-gray-wf90f53adsa5/ | WF90F53ADSA5(Gray 1색) | |
| CA-FR | 같은 slug, `/ca_fr/` | WF90F53ADSA5(Gris) | |
| US | https://www.samsung.com/us/laundry/washers/front-load-wf90f27-front-loading-ai-home-ai-optiwash-plus-ultra-capacity-5-3-cu-ft-dark-steel-sku-wf90f53adsa5/ | WF90F53ADSA5 Dark Steel / WF90F53ADYA5 Ivory | |

- CA·US에는 WF90H가 없습니다. WF90F27은 같은 최상위 등급입니다(7" AI Home, Flex Auto Dispense).

### UK·CA·CA-FR: pd 템플릿

**옵션**
- 색상: `input[name='pd-color']`(`data-colorname`, `data-modelcode`, `data-modelprice`, `data-discountprice`). `label[for]`를 클릭합니다. UK에서 색상을 바꾸면 **전체 페이지가 새 URL로 이동**합니다.
- 용량: `input[name^='pd-others-']`. UK "11 kg", CA "6.1 cu.ft."이고 CA-FR에는 용량 선택이 없습니다.

**가격**
- 요소: `.pdd39-anchor-nav .pd-buying-price__new-price` / `__was` / `__save`
- UK: `£1,049.00`, `RRP: £1,149.00`, `Save £100.00`
- CA-EN Ontario: `From $41.67/mo for 36 mos or $1,499.99`
- CA-EN Quebec: `$1,499.99`
- CA-FR: `1 499,99 $`
- 요약 `.hdd02-buying-tool__summary`(`.cost-box`). UK 요약에는 에너지 배지와 "Previous price £1,149.00"가 있습니다.
- 가격이 랜덤 모듈(Prepaid Mastercard)에 섞여 들어오는 일이 있어 요약은 반드시 `.hdd02-buying-tool__summary`에서 읽습니다.

**JSON-LD**: Product 하나에 Offer 하나, strikethrough는 없습니다. UK 1049는 화면과 일치합니다.

**섹션**
- 각 섹션은 `.pd-select-option`(제목 `h3.pd-select-option__headline`)입니다. 치수만 `.pd-sellout-option--dimensions`(`p.pd-sellout-option__headline`)입니다.
- UK: Choose your Colour → Choose your Capacity → "Want up to £100.00 off? Recycle your old appliance…" → Pre-purchase check → 오퍼(제목 없음) → 요약
- CA: Colour → Capacity → Dimensions/Make Sure It Fits → Samsung Care+ → Add-on Items(건조기 DV90F53AESAC $1,499.99) → Pre-purchase check(Optional Haul Away) → 요약(Rewards 1,500 p) → Offer Programs
- CA-FR: CA와 같고 용량 섹션만 없습니다.

**스펙**
- 위치·구조는 TV와 같은 `.pdd32-product-spec`입니다. 항목 수는 UK 68, CA 47, CA-FR 47입니다.
- UK: Washing Capacity 11 kg, Energy Efficiency Class A, 29 kWh/100 cycles, 600 x 850 x 590 mm, 75 kg
- CA: Washing Capacity 6.1 cu.ft, Tier 3, 103 kWh/year, IMEF 3.1, IWF 2.9, 686 x 984 x 875 mm (27 x 38.7 x 34.5 inches), 102 kg

**레이어** (모두 `.layer-popup`)
- UK 트레이드업 Learn more: `button[an-la='trade-up:learn more']`
- UK 금융 계산기: `a[data-target-popup='eipPopup']`(PayPal, Samsung Finance, Klarna)
- CA 치수 측정: `a[data-target-popup='dimensionsPopup']`
- CA Care+: `label[for='pd-extended-warranty-option-0']`로 열고 Close로 닫습니다. Confirm은 누르지 않습니다.

**지역**: 가격과 섹션은 같습니다. 월 할부는 CA-EN Ontario에서만 보입니다.

### US: us_pdp 템플릿
- 페이지 자체가 `-sku-` URL입니다. 로드 직후 같은 URL로 3번 재이동합니다.
- 색상: `[aria-label='Color Variant: Dark Steel']` / `'Ivory'`. 클릭하면 `-sku-wf90f53adya5`로 바뀝니다(수 초 걸림).
- 헤더 가격: `$1,299.00`, `Comp. Value: $1,649.00ⓘSave $350.00`(Ivory는 $1,549.00 / Save $250.00)
- 결제: `One-time Payment $1,299.00`, `Pay Monthly $54.13/mo for 24 mos`, `Pay in 4 Payments $324.75`
- 요약 `[class*=Summary_container_v2]`: `$1,649.00`, `Instant Savings - $350.00`, `Total $1,299.00`
- JSON-LD: 1299, strike 1649, `color` "Dark Steel". 화면과 일치합니다.
- 섹션: Color(`[class*=Relation_title]`) → Complete your laundry → Offers → Dimensions → Make sure it fits → Samsung care+ → Delivery options for: → Payment options → 요약 → Highlights(끝)
- 스펙: 정적 HTML에는 없고 스크롤 후 DOM에 생깁니다(`[class*=Specs_subSpecItemName]`). 예: Washer Capacity (cu. ft.) 5.3, Product Weight (lbs.) 224.9, Product Dimensions 27 x 38.7 x 34.4(단위 없음), CEE Rating 3
- 레이어(`[class*=Overlay_dialog]`): Care+ Terms, Start Measuring, Delivery Learn More. Delivery 레이어의 치수 라벨이 `34.4" W x 27" H x 38.…`로 W·H·D가 뒤바뀌어 있습니다.
- 페이지 폭이 1477px라 캐러셀이 넘칩니다. 클립을 페이지 폭 안으로 제한해야 합니다.

### 정규화 차이
- **용량:** CA 6.1 cu ft / US 5.3 cu ft(같은 모델) / UK 11 kg. CA-FR은 "6,1 pi³"와 "7.6 pi³"가 섞여 있습니다.
- **에너지:** UK EU 등급(A, kWh/100 cycles) / CA Tier 3, ENERGY STAR, IMEF·IWF / US Tier 3, CEE 3, ENERGY STAR Most Efficient
- **무게:** CA 102 kg, CA-FR "102 lbs"(단위 오류), US 224.9 lbs
- **기타:** CA-FR 탈수 "1 201 tr/min" vs 1200 rpm, CA-FR 치수 라벨 "(H x L x P)"
- **색상명:** CA 칩은 "Gray", 스펙은 "Dark Steel"입니다.

## 3. 냉장고

### 비교 대상

| 사이트 | URL | SKU |
|---|---|---|
| UK | https://www.samsung.com/uk/refrigerators/multi-door/rf9000d-rf9000dc-t-style-french-door-beverage-center-645l-silver-rf65dg960esreu/ | RF65DG960ESREU(Black RF65DG960EB1EU) |
| CA-EN | https://www.samsung.com/ca/refrigerators/french-door/counter-depth-4-door-flex-refrigerator-with-beverage-center-23-cu-ft-stainless-steel-rf23dg9600srac/ | RF23DG9600SRAC |
| CA-FR | 같은 slug, `/ca_fr/` | RF23DG9600SRAC |
| US | https://www.samsung.com/us/refrigerators/french-door/bespoke-counter-depth-4-door-flex-refrigerator-23-cu-ft-with-beverage-center-in-stainless-steel-sku-rf23db9600qlaa/ | RF23DB9600QLAA(깊이 Full은 RF29DB9600QLAA $2,699) |

### UK·CA·CA-FR: pd 템플릿
- 색상: `input[name=pd-color]`(`an-la="colour:silver"`). UK에서 색상을 바꾸면 **전체 페이지가 이동**합니다(가격 같음).
- 용량: `input[name^=pd-others-]` 1개("646 L", "23 cu.ft.", CA-FR "23 cu.ft")
- SKU: `.pdd39-anchor-nav__cta [data-modelcode]`, 요약 CTA `.cost-box__cta a`
- 가격: UK `£3,399.00`, CA `$3,299.98`(Ontario는 `From $91.67/mo for 36 mos or $3,299.98`), CA-FR `3 299,98 $`
- CA CTA의 `data-modelprice=3899.99`는 숨은 MSRP이고 화면에는 나오지 않습니다.
- `{{...}}` 자리표시자가 약 7초 동안 남습니다. 요약 `.cost-box__price-now`에서 `{{`가 사라질 때까지 기다립니다.
- 섹션
  - UK: Colour → Capacity → Dimensions(+ Start measuring) → Trade-Up(£100) → Pre-purchase check → 오퍼 목록 → gocertify → 요약
  - CA: Colour → Capacity → Dimensions → Care+ → Pre-purchase check → Estimate delivery fees(늦게 뜸) → 요약(Rewards 3,300 p) → Offer Programs
- 스펙: `pdd32`, UK 49개, CA 44개
  - UK: Gross Total 646 ℓ, Energy Class E, 368 kWh/year, 912 x 1830 x 723 mm, 144 kg, 37 dBA
  - CA: Net Total 22.8 cu.ft, 634 kWh/year, 911 x 1832 x 714 mm, 137 kg
  - CA-FR: 라벨은 불어인데 값에는 영어 단위("cu.ft")가 남아 있습니다.
- 레이어: UK 금융 계산기, Trade-Up Learn more, `#dimensionsPopup`, CA Care+ `#extended-warranty-vd`(Confirm 금지)
- 지역: 가격과 섹션은 같고, 월 할부만 CA-EN Ontario에서 보입니다.

### US: us_pdp 템플릿
- 타일: `[data-testid=SeriesTile][role=radio]`, `an-la="depth:counter depth"` / `"depth:full depth"`
- 깊이를 바꾸면 전체 이동합니다. Playwright 클릭에 `no_wait_after=True`가 필요합니다.
- 가격
  - 헤더 `[class*=PriceInfoText_newHAHeader]`: `$2,799.00 Comp. Value: $3,699.00ⓘSave $900.00`
  - 요약 `#product-summary`: `Summary_eppPrice`, `Summary_totalprice`
  - 결제 카드: `$116.63/mo for 24 mos`, `$699.75` Pay in 4
- 섹션: Color → Depth → Offers → Dimensions → Make sure it fits → Open Box Pricing($2,295.18) → Samsung care+ → Delivery options for: → Water Filter → Payment options + Galaxy Card → 요약
- 우편번호가 14044면 RF23은 판매 불가입니다. 10001이면 배송·설치 무료와 Haul Away $50가 나오고, Comp. Value가 $3,728.99, Save가 $929.99로 바뀝니다.
- 스펙: 스크롤 후 로드됩니다. 108개. Total Capacity 22.8 cu ft, Width 35 7/8", 317.5 lbs
- `SupportedLanguagesPopup`(빈 `role=dialog`)이 항상 있으므로 레이어 판별에서 제외합니다.

### 정규화 차이
- **용량 기준:** UK 총용량(gross) ℓ / CA 실용량(net) cu ft / US total cu ft
- **치수:** UK mm / CA mm + 소수 inch / US 분수 inch(높이 73" vs CA 72.125")
- **할인:** UK 없음 / CA 숨은 MSRP / US Comp. Value(우편번호마다 다름)

## 4. 노트북 — Galaxy Book6 Pro 16"

### 비교 대상

| 사이트 | 캡쳐할 URL | SKU |
|---|---|---|
| UK | https://www.samsung.com/uk/computers/galaxy-book/galaxy-book6-series/buy/?modelCode=NP960XJG-KGAUK | NP960XJG-KGAUK, Ultra X7 358H / Arc B390 / 32GB / 1TB / Grey, £2,299 |
| CA-EN | https://www.samsung.com/ca/computers/galaxy-book/galaxy-book6-series/buy/?modelCode=NP960XJG-KG1CA | NP960XJG-KG1CA, **Ultra 7 356H** / Intel Graphics, $3,299.99(was $3,599.99) |
| CA-FR | 같은 경로, `/ca_fr/` | NP960XJG-KG1CA |
| US | https://www.samsung.com/us/computers/galaxy-book/galaxy-book6-series/buy/galaxy-book6-pro-16-intel-core-ultra-x7-1tb-gray-sku-np960xjg-kg1us/ | NP960XJG-KG1US, X7 / Arc B390, $2,149.99(was $2,649.99) |

- 주신 UK URL은 PDP입니다. 그 BUY NOW는 단순 구매 템플릿(hdd02)으로 가므로, UK도 시리즈 구매 페이지(hubble)를 씁니다.
- 스펙 PDP
  - UK: https://www.samsung.com/uk/computers/galaxy-book/galaxy-book6-pro-ultra-3-32gb-1tb-np960xjg-kgauk/
  - CA: `…/ca/computers/galaxy-book/galaxy-book6-pro-ultra-7-32gb-1tb-np960xjg-kg1ca/`(`/buy/`는 시리즈 페이지로 301). CA-FR은 같은 경로입니다.

### UK·CA·CA-FR: hubble (시리즈 구매 페이지)

**옵션 라디오** (`input.hubble-pd-radio__input`, name에 공백 주의)

| 축 | name |
|---|---|
| Device | `device-rdo` |
| OS | `sim-rdo` |
| Colour | `basic-color` |
| Memory | `"memories-rdo "` |
| Storage | `"memory-rdo "` |
| Connectivity | `" connectivity-rdo"` |
| Screen | `"screensize-rdo "`(displayname `16&quot;`) |
| Processor | `"processor-rdo "` |
| Graphic | `"graphic-rdo "` |

- 라디오마다 `data-modelcode`(그 옵션을 누르면 바뀔 SKU)가 있습니다. 해당 기기에 없는 옵션은 비활성이 아니라 **숨김**입니다.
- 클릭하면 SKU와 가격이 바뀌지만 URL은 그대로입니다. 다른 축도 연쇄로 바뀔 수 있습니다. SKU는 `.price-bar-cart-btn[data-modelcode]`에서 읽습니다.

**가격**
- 가격 바 `.hubble-price-bar__price-total-text`: UK `£63.87/mo. or £2,299.00`, CA-ON `From $275.00/mo. with 0% APR‡ or $3,299.99`, CA-FR `À partir de 275,00 $/mo. … ou 3 299,99 $`
- was: `.hubble-price-bar__price-total-save-inner span` = `$3,599.99 Save $300.00`

**JSON-LD**: ProductGroup.hasVariant, strikethrough는 없습니다. CA 3299.99는 화면과 일치하지만, was 가격 $3,599.99는 JSON-LD에 없습니다.

**섹션**
- CA: Device, OS, Colour, Memory, Storage, Connectivity, Screen size, Processor, Graphic, Samsung Trade-in, Samsung Care+, Offer, Buy Direct, 요약
- UK: "Offer" 대신 "Gift and Savings", "Discover More"가 추가됩니다.

**레이어**: UK 오퍼 배너, 트레이드인 Learn more(`#hubble-tradein-info-layer`), 0% Finance(`#hubble-eip-layer`)

**지역**: 가격은 같습니다. QC에서는 금융 표시가 전부 사라집니다(가격 바 "From Total $3,299.99").

**주의**
- CA·CA-FR은 로드 몇 초 뒤 **스스로 한 번 재로드**합니다.
- CA-FR 색상 englishname이 "Gris"라 현재 드라이버의 색상 판정이 실패합니다.

### US: us (구매 SPA)
- 축 그룹 제목: `span[class*=Label_sharpSansBold][class*=Label_large]`(Device, Operating System, Memory, Storage, Screen Size, Processor and Graphics, Graphics, Color)
- 타일
  - 모든 타일에 `[data-modeldisplay]`가 있습니다(소문자, 예: `1 tb`, `16.0"`, 앞 공백이 있는 ` intel® graphics`).
  - `data-modelcode`는 해당 타일을 눌렀을 때의 SKU입니다.
  - 일부 타일은 `handleRelationSelect`가 없는 `Capacity_*` div입니다.
  - 색상은 `aria-label="Color Variant: Gray"`입니다.
- 클릭할 때마다 새 `-sku-` URL로 바뀌고, JSON-LD가 따라 바뀝니다.
- 가격 헤드라인: `$2,149.99 or $89.59/mo for 24 mos at 0% APR⊕σ was $2,649.99 Save $500.00`
- 요약: `NP960XJGD-EXP / NP960XJG-KG1US`, 7개 항목 줄 `Windows 11 Home | 32 GB | 1 TB | 16.0" | Intel® Core™ Ultra X7 358H | Intel® Arc™ B390 | Gray`, `Total $2,149.99 was $2,649.99`
- 스펙: `#accordion-Specs`. 스크롤 후 제목 `[data-testid=accordion-title]`을 클릭하면 내용이 주입됩니다.
- 모든 타일의 `data-discountprice`는 현재 선택된 SKU의 가격입니다. 타일별 가격으로 쓰면 안 됩니다.

### 정규화 차이
- **같은 값의 표기:**
  - 용량·메모리: UK 1TB / 32GB, 나머지 1 TB / 32 GB
  - 화면: 16" / 16.0"
  - 색상: Grey / Gray / Gris
  - OS: Windows 11 Home / Famille
- **금융:** UK 36개월 / CA-ON 12개월 / CA-QC 없음 / US 24개월
- **스펙 라벨:** UK "Size (inch)"·"Weight (kg)", CA "Size"·"Weight". US에는 Shipping Weight가 추가됩니다.
- **[사실] 사이트 오류 후보:**
  - CA 비교 블록 부제가 "Compare the latest Galaxy Z Series smartphones"입니다(CA-FR은 미번역).
  - US 14" 월 할부 문구에 `$`가 없습니다("or 102.09/mo").
  - US 트레이드인 금액이 "$335+"와 "up to $337"로 서로 다릅니다.
  - UK KGAUK(£2,299)와 KGJUK(£2,599)의 PDP 스펙이 같습니다.

## 5. 갤럭시워치 — Watch9 40mm Graphite Bluetooth

### 비교 대상 (캡쳐는 구매 페이지)

| 사이트 | 구매 페이지 | 비고 |
|---|---|---|
| UK | https://www.samsung.com/uk/watches/galaxy-watch9/buy/?modelCode=SM-L340NZKAEUB | bare /buy/는 **LTE 40mm**로 열림 |
| CA-EN | https://www.samsung.com/ca/watches/galaxy-watch9/buy/?modelCode=SM-L340NZKAXAC | bare는 BT 40mm |
| CA-FR | 같은 경로, `/ca_fr/` | |
| US | https://www.samsung.com/us/watches/galaxy-watch9/buy/galaxy-watch9-40mm-graphite-bluetooth-sku-sm-l340nzkaxaa/ | bare /buy/는 **44mm** StudioSelect로 리다이렉트 |

- 스펙 PDP
  - UK: https://www.samsung.com/uk/watches/galaxy-watch/galaxy-watch9-40mm-graphite-bluetooth-sm-l340nzkaeub/
  - CA·CA-FR: `/ca/…/galaxy-watch9-40mm-graphite-bluetooth-sm-l340nzkaxac/`
  - US: SKU별 PDP가 없어서 구매 페이지의 Specs 아코디언을 씁니다.
- `?modelCode=<SKU>`로 열면 해당 조합이 선택된 상태와 가격으로 뜹니다(4개 SKU로 검증).
- SKU 규칙

| 항목 | 값 |
|---|---|
| 모델 (UK·CA) | 40 BT `L340N`, 40 LTE `L345F`, 44 BT `L350N`, 44 LTE `L355F` |
| 모델 (US LTE) | `L345U`, `L355U` |
| 색상 | Graphite ZK, Cream ZE, Silver ZS(40mm는 Graphite/Cream, 44mm는 Graphite/Silver) |
| 접미사 | UK AEUB, CA AXAC, US AXAA |

### UK·CA·CA-FR: watchbc 템플릿

**옵션**
- 섹션: `.watch-bc-option__option[data-type-code]`(C-DVC, C-SIZ, C-CON, C-CLR, B-TYP, B-CLR, B-SIZ)
- 옵션: `input.hidden`(`data-modeldisplay`, `data-modelcode`, `data-product-presetmodelcode`). `label.option-select[for]`를 클릭합니다. 선택되면 `.is-checked`가 붙습니다.

**가격**

| 위치 | 선택자 | 예 |
|---|---|---|
| 가격 바 | `strong.bar-total-price` | `£349.00` |
| was·save | `.bar-was-price` / `.bar-save-price` | 숨김 상태 |
| SKU | `.total-summary .model-code` | |
| 기기 가격 | `.summary-main-price` | |
| 총액 | `.summary-total-price .price-target` | |
| 요약 4필드 | `.summary-main-product strong` | |

**JSON-LD**: ProductGroup에 variant 8개(가격이 문자열). strikethrough는 없습니다.

**가격표**

| 사이트 | 40 BT | 40 LTE | 44 BT | 44 LTE |
|---|---|---|---|---|
| UK | £349 | £399 | £379 | £429 |
| CA / CA-FR | $519.99 | $599.99 | $559.99 | $639.99 |
| US | $379.99 | $429.99 | $409.99 | $459.99 |

**섹션**
- UK: 가격 바 → 오퍼 배너 → Device → Case size → Connectivity → Case colour → Band type/colour/size → Trade-in → Samsung Care+ → Gifts and Savings → Buy direct → What's in the box + 요약
- CA-FR 제목: Appareil, **"Taille de la valise"**(케이스 크기 오역), Connectivité, Couleur du boîtier, Type de bande, …, Trade-in(미번역)
- 마크업: 옵션 섹션 `h2.watch-bc-option__option-title`, 그 외 `.watch-bc-buyflow`(제목 `.watch-bc-buyflow__headline-title`)

**스펙** (PDP `pdd32`)
- 공통 값: 1.3" (34mm), 31.5 g, 42.7 x 40.4 x 8.6 mm, 390 mAh, 5 ATM
- CA-FR은 소수점이 섞여 있습니다(`1,3 po` / `31.5`).

**레이어**: 오퍼 배너. `button.s-offer-open`은 x ≥ 0인 것을 고르고(UK 캐러셀 복제본 제외), `.watch-bc-offer-banner-wrap`을 캡쳐합니다. 트레이드인 `.trade-in-popup-open`과 `.cta-target`은 누르지 않습니다.

**지역**: 가격은 같습니다. CA-EN Quebec에만 구매 시 추가 할인 블록(`.seca-pwp-buy-page--offers`, "Bespoke Jet AI …")이 있습니다.

**주의**: 클릭 순서에 따라 상태가 꼬입니다(UK 44mm £334 케이스 전용 코드, CA-FR LTE를 눌러도 BT SKU). 직접 진입 후 SKU를 검증해야 합니다.

### US: us (구매 SPA)
- 타일 `an-la`: `case size:40mm`, `card:bluetooth|lte`, `case color:graphite`, `band type:…`
- LTE는 통신사 선택 없이 SM-L345U(unlocked)입니다. 요약에 숨은 "Watch Carrier: Wifi"가 있습니다.
- 헤더: `$379.99 or 15.83/mo for 24 mos at 0% APR⊕σ`(**`$` 없음**). 결제 타일: `$15.83/mo`, `Pay in 4 Payments $95.00`
- 섹션: Device, Case Size, Connectivity, Case Color, Band Type/Color/Size, Samsung Trade-in, Samsung Care+, Enhance your experience, Choose your purchase option, Samsung Galaxy Card, 요약, 아코디언(Specs)
- 요약 줄을 위치로 읽으면 color="Bluetooth", carrier="Wifi"로 잘못 읽습니다. 선택된 타일 기준으로 읽어야 합니다.

### 정규화·카드 후보
- bare /buy/ 기본 변형이 나라마다 다릅니다(UK LTE, CA BT, US 44mm).
- LTE 모델 문자가 다릅니다(UK·CA F, US U). SKU 10번째 자리 `D`는 UK·CA에서 케이스 전용, US에서는 StudioSelect입니다.
- CA-EN 오퍼 배너에 "Galaxy Watch Ultra2"가 적혀 있습니다(Watch9 페이지).
- UK 페이지가 "Color options may vary"(미국식 철자)로 씁니다.
- CA-FR은 옵션 제목에서 "bande", 요약에서 "Bracelet"을 씁니다.
