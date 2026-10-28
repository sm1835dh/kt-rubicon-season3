# 루비콘 국가 확산(UK → CA → US) Samsung.com 사이트 비교 — 작업 정리

- 작성일: 2026-10-27 (KST)
- 기준 사이트: UK `https://www.samsung.com/uk/`
- 비교 대상: CA-EN `https://www.samsung.com/ca/`, CA-FR `https://www.samsung.com/ca_fr/`, US `https://www.samsung.com/us/`
- 문서 구성: ① 범위 결정 → ② 비교 조사 보고서(재확인 정정 반영) → ③ 정적 재수집 정오표 → ④ 렌더링 검증 키트 → ⑤ 의사결정 필요 사항

> 표기 규칙
> - **[사실]** 페이지에서 직접 확인 / **[추정]** 관찰 기반 추론 / **[미확인]** JS 렌더링·접근 제한으로 확인 못함
> - **[정정]** 10/27 재확인에서 보고서 내용과 다르게 확인되어 고친 부분
> - **[신규]** 10/27 재확인에서 새로 발견한 부분

---

## 0. 요약

- **CA는 UK 파이프라인 재사용률이 높습니다.** URL 패턴, GNB, PDP 스펙 그룹 구조가 사실상 같습니다. 다만 단위(cu.ft·lb·inch 혼용), 규제 필드(ENERGY STAR·CEE Tier vs UK A–G 등급), 주(province)별 가격, Affirm 금융은 정규화 계층에서 흡수해야 합니다.
- **CA-FR은 번역된 동등 사이트가 아닙니다.** URL slug는 영어 그대로이고 /ca/와 1:1로 대응합니다. 하지만 스펙 값에 영어가 남아 있고, 소수점 표기가 섞여 있으며(5,8 pi³ / 5.8 pi³), 타국 리뷰가 번역 없이 노출되고, 같은 모델의 사이즈 옵션이 /ca/와 다릅니다. 같은 세탁기의 무게가 EN은 kg, FR은 lbs로 표기된 사례도 있습니다 **[신규]**.
- **US는 사실상 신규 구축입니다.** PDP URL이 `-sku-` 접미사를 쓰고, 통신사별 SKU로 분기되며, 가격은 정가·할인가 분리와 세금 별도, 금융은 TD Bank, 할인은 Offer Program(ID.me)이라는 별도 체계를 씁니다. 페이지 메타의 모델코드와 본문 모델코드가 다른 사례도 있습니다 **[신규]**. US 일정은 CA보다 2배 이상 여유 있게 잡는 편이 안전합니다 [추정].
- **가장 먼저 막아야 할 위험은 더미 가격 문구입니다.** UK·CA·CA-FR PDP 정적 HTML에 국가와 무관한 £/$ 템플릿 문자열이 들어 있습니다. 가격은 JSON-LD·API에서만 받아야 합니다.
- **남은 확인 작업:** £ 더미가 실제 화면에 보이는지, hreflang 태그 유무, US PDP 스펙 렌더링 여부는 정적 수집으로 판단할 수 없습니다. 렌더링 검증 키트(4장)로 확인해야 합니다.

---

## 1. 작업 경과

| 순서 | 작업 | 결과 |
|---|---|---|
| 1 | 조사 범위 결정 | 범위 **B**(사이트 전반), 깊이 **C**(대표 카테고리 심층 + 동일 모델 필드 비교), **CA-FR 포함** |
| 2 | 비교 조사 보고서 작성 | 사이트 전반, PLP/PDP, 동일 모델 필드, URL·taxonomy, CA-FR parity, 재사용/신규 구분, 리스크, 의사결정 사항 |
| 3 | 헤드리스 브라우저 확인 시도 | 작업 환경에서 samsung.com 접속이 네트워크 정책으로 차단(프록시 403), 사용자 PC 연결 없음 → 렌더링 확인 불가 |
| 4 | 정적 재수집으로 핵심 주장 재대조 | 보고서 오류 4건, 신규 발견 3건, 시점 차이·재현 불가 3건 확인(3장) |
| 5 | 렌더링 검증 키트 작성 | `verify.py`, `claims.json`, `README.md`. 17개 항목·21개 페이지. 모의 페이지로 동작 확인(4장) |

---

## 2. 비교 조사 보고서 (재확인 정정 반영)

### 2.1 조사 방법과 한계

- 정적 HTML 수집과 검색 스니펫(JSON-LD 포함)을 근거로 했습니다.
- 가격·재고·배송일 위젯 상당수는 클라이언트 렌더링 템플릿(`{{price.priceWrapper.info.salePriceFormatted}}` 등)이라 정적 수집으로 실제 값을 확인할 수 없었습니다.
- **주의 [사실]:** UK·CA·CA-FR PDP 정적 HTML에 `from £55.53/mo for 36 mos or £3,299.00 £2,399.00 save $ £400.00`, `TotalVAT Inclusive From $107.50/mo ... $2,579.96`, `al mese` 같은 더미 템플릿 문자열이 국가와 무관하게 들어 있습니다. 10/27 재확인에서 CA·CA-FR 세탁기 PDP에서도 같은 문자열을 확인했습니다. 이를 실제 가격으로 인덱싱하면 CA 페이지에 £ 가격이 들어가는 환각 원인이 됩니다.
- 조사 시점에 US·CA 홈 검색창이 "Search under maintenance" 상태였습니다. **[정정]** 10/27 23시 재확인에서 CA는 정상, US는 점검 상태 유지.

### 2.2 사이트 전반 비교 (표 1)

| 항목 | UK (기준) | CA-EN | CA-FR | US |
|---|---|---|---|---|
| og:locale / sitecode | en-GB / uk | en-CA / ca | fr-CA / ca_fr | `en` / us (지역 없는 locale) |
| 첫 진입 시 지역 선택 | 국가/언어 배너만 | **주(Province) 선택 모달**(기본값 Quebec). "The page will be reloaded to display the corresponding prices." | 동일(불어) | 국가 배너, "MY BENEFITS / SPECIAL OFFERS" 배너 |
| GNB 1단계 | Shop, Mobile, TV & AV, Appliances, Computers & Monitors, Wearables, Accessories, Samsung Week, Support, For Business | UK와 동일 | 번역판(Magasiner, Mobilité, TV et AV, Électroménager, Ordinateurs et écrans, Appareils connectés, Accessoires, Assistance, Pour les entreprises) | Shop, Mobile, TV & AV, Appliances, Computers & Monitors, Wearables, **Audio**, Accessories, **Samsung Week, Find a Store**, Support, For Business **[정정: Samsung Week·Find a Store 포함]** |
| 금융(할부) | **Samsung Finance(Glow)**: £250–£10,000, 12–24개월 0% APR, 36개월 14.9% APR(본문·FAQ 기준). 같은 페이지 meta-description은 "0% APR … up to 36 months"로 상충. Klarna, PayPal Credit, Samsung Flex 병행 | **Affirm**: 0–31.99% APR, 최대 36개월 0%(일부 품목, 오퍼 페이지). Affirm 안내 페이지 meta는 "up to 24 months"로 상충. **Flexiti**, Klarna, Samsung Pay. 퀘벡은 조건 상이 | 동일(불어). "TAEG de 0 % pendant 36 mois" | **Samsung Financing(TD Bank)**: Standard Purchase APR 29.99%. Pay in 4, **Samsung Galaxy Card**, **Samsung Access**(TV 구독) |
| 트레이드인 | Mobile Trade In, Instant Trade In, TV Trade Up | Samsung Trade-in, **Annual Upgrade Program**(12/24개월) | Programme de mise à niveau annuelle | Samsung Trade-In. 15일 내 미반납 시 크레딧 전액 청구 |
| 특수 스토어 | Student & Youth, Key Worker & Teacher, Business | 학생·기업·정부·비즈니스 할인 프로그램 | 동일(불어) | **Samsung Offer Program**: 학생·교사·정부·군인·기업 직원 "Save up to 30%", ID.me 자격 확인, 연간 카테고리별 2개 한도 |
| 반품 기간 | **14일**, 결함 30일 | **15일**, 대형가전 **7일** | 15일(대형가전 7일 불어판 미확인) | **15일**, restocking fee |
| 배송 표기(PDP) | "Arrives tomorrow, if you order by 7pm" | "2 day Shipping Available / 15-day returns / Optional Haul Away", $50 이상 무료배송 | "Livraison en 2 jours disponible / Retour sous 15 jours / Transport en option" | 변형별 "Get it by …" |
| 보증 | 세탁기 PDP "5 Year Warranty" | 세탁기 모터 10년 | "Garantie de 10 ans sur le moteur" | [미확인] |
| 보호 플랜 | Samsung Care+ | Samsung Care+ | Care+. 퀘벡 배송·수거 제품은 Care+ Premium 미제공 | Samsung Care+ |
| 리워드 | Samsung Rewards | 최대 0.7% 포인트 적립 | 동일(불어) | Samsung Rewards |
| 고객지원 GNB | Live Chat, Call, Sign Language, Book a Repair, Track My Repair, Regulatory Information | 24/7 Chat, Call, Text support, Sign Language, Mail-in/In-Home Repair, Premium Care Service | 동일(불어, 일부 오탈자) | [미확인] |
| 국가 전용 기능 | 결제수단 연계 프로모션(PayPal 결제 시 TV 추가 할인) | 주별 가격, 퀘벡 예외, 이중언어 | 퀘벡 예외 | 통신사 연계 판매, Carrier Deals, Galaxy Card, 외부 HVAC 사이트 |

**루비콘 시사점**
- 정책 문서는 `country`, `language`, `policy_type`, `product_scope` 메타데이터가 필수입니다. "반품 기간" 하나에 UK 14일, CA 15일(대형가전 7일), US 15일(restocking fee)이 충돌합니다.
- 금융 상품명은 국가별 엔티티 사전이 필요합니다. 사용자는 Samsung Finance, Affirm/Flexiti, TD Bank 금융을 모두 "할부"라고 부릅니다.
- 같은 페이지 안에서 금융 수치가 충돌합니다(본문 vs meta). 정책 청크 간 우선순위 규칙(본문 > meta)이 필요합니다.
- 퀘벡 예외(Care+ Premium, 금융 조건, 주별 가격)는 CA 평가셋에 반드시 넣어야 합니다.

### 2.3 제품 정보(PLP/PDP) 노출 항목 비교 (표 2)

| 항목 | UK | CA-EN | CA-FR | US |
|---|---|---|---|---|
| PDP 템플릿 | 공통 PDP(Features / Specs / Reviews / Support) | UK와 동일 | 동일(Caractéristiques / Spéc. / Avis / Aide) | **별도 템플릿**: 모델코드 `QN65QN90FAF / QN65QN90FAFXZA`, Storage·Color·**Connectivity** 선택기 |
| 통화·가격 형식 | `£1,359.00`, JSON-LD `"price":"1359"` | `$2,329.99`, `From $64.72/mo.‡` | **`2 329,99 $`**, `À partir de 64,72 $ /mo.‡`. JSON-LD는 점(`1999.99`) | `was: $1399.99 $1,149.99`. JSON-LD `price`(할인가)와 `priceSpecification.price`(정가) 분리 |
| 세금 표기 | VAT 포함 | [추정] 세금 별도, 명시 문구 [미확인] | 동일 [추정] | **세금 별도** 명시 |
| 정가·할인가 | `RRP:` 라벨, `lowestWasPricetext` | "save $" 템플릿 | 동일 | "was:" 병기 |
| 리뷰·평점 | 별점·건수(QN90F 65 "4.6 (142)"). 타국 리뷰 혼재 | 별점·건수. PLP JSON-LD aggregateRating | 별점(QN90F 65 "4.8 (1,357)"). 스페인·독일·프랑스·UK·호주 출처 리뷰 혼재 | 별점(S26 Ultra 4.8 (18,591), QN90F 소비자 PDP 4.6 (992)) |
| Q&A·FAQ | 모델별 FAQ(JSON-LD FAQPage) | FAQ(`inLanguage: en-CA`) | FAQ(불어) | [미확인] |
| 단위 체계 | 미터법(mm, kg, kWh/100 cycles), TV 화면만 인치 | **혼용**: cu.ft.(IEC/DOE), mm 또는 inch, kg 또는 lb | CA-EN과 같은 혼용 + 소수점 혼용(5,8 / 5.8) + EN과 단위 불일치 사례 **[신규]** | 야드파운드법 |
| 에너지·규제 | UK/EU 등급(TV F, 세탁기 A), Yearly Power Consumption(EU), Noise Emission Class | ENERGY STAR + **CEE Tier**, Energy Consumption(annual), IMEF/IWF. EnerGuide [미확인] | "Certification ENERGY STAR® Yes" | ENERGY STAR 배지, "ENERGY STAR® Most Efficient" |
| 재고·배송 | "Out of Stock", "Sorry this item is out of stock" | "Out of Stock", "Not for sale" | "Rupture de stock" | 변형별 "Out of stock", "Get it by …" |
| 모델코드 체계 | `SM-S948BZKDEUB`, TV `QE65QN90FATXXU` | `SM-S948WZVAXAC`, TV `QN65QN90FAFXZC` | CA-EN과 동일 코드 | `SM-S948ULBAXAA`, `…ATT`/`…VZW`, TV `QN65QN90FAFXZA` |
| 옵션 변형 | 스토리지·색상, JSON-LD `hasVariant` | `256 GB｜12 GB`, 색상, Samsung.com 전용 색상 | 동일. FAQ 본문은 "Go/To" | 스토리지, 색상, **Connectivity** |

**루비콘 시사점**
- 가격은 HTML 본문에서 파싱하지 말고 JSON-LD `offers`와 API에서만 받습니다. UK·CA는 같은 JSON-LD 파서를 쓰고, US는 `priceSpecification` 매핑을 추가합니다.
- 가격 스키마는 `list_price`, `sale_price`, `currency`, `tax_included`, `region(province)`, `financing_monthly`로 분리합니다.
- 리뷰 청크에는 `origin_country`, `lang` 메타데이터가 필요합니다.
- 단위 정규화 계층에 **값 범위 검증**을 넣습니다. 같은 숫자에 단위만 다른 경우(98 kg vs 98 lbs)는 단순 변환으로는 잡히지 않습니다.

### 2.4 카테고리별 동일 모델 필드 비교 (표 3)

#### 2.4.1 스마트폰: Galaxy S26 Ultra

| 국가 | 대표 SKU(예) | 코드 규칙 |
|---|---|---|
| UK | SM-S948BZKDEUB(256GB Black), SM-S948BZDHEUB(1TB Pink Gold) | `SM-S948B` + 색상2 + 용량1 + `EUB` |
| CA-EN/FR | SM-S948WZVAXAC(256GB Cobalt Violet), SM-S948WZDEXAC | `SM-S948W` + 색상2 + 용량1 + `XAC` |
| US | SM-S948ULBAXAA(Unlocked 256GB Sky Blue), SM-S948UZKAATT(AT&T), SM-S948ULBAVZW(Verizon) | `SM-S948U` + 색상2 + 용량1 + `XAA`/통신사 |

- [추정] B/W/U는 지역, 다음 2자리는 색상, 다음 1자리는 용량.
- **[정정] 용량 코드 추정의 신뢰도가 낮습니다.** 보고서는 SM-S948WZDEXAC를 "Samsung.com 전용 512GB, $2,329.99"로 기술했습니다. 하지만 이 URL의 검색 결과 제목은 "Pre-order Galaxy S26 Ultra **1 TB**"이고, 현재 정적 HTML에는 이 코드가 없습니다(ZVF, ZVE, LBE, ZSE, ZKE, ZKA, ZVA, LBA, ZDF만 확인). $2,329.99 가격도 재현되지 않았고 트레이드인 기준 "$35.25/mo"만 보였습니다. 용량 코드는 국가별 매핑표를 실제 선택 상태로 검증한 뒤 확정해야 합니다(검증 키트 C09).

| 필드 | UK | CA-EN | CA-FR | US |
|---|---|---|---|---|
| 스토리지 표기 | "256 GB / 512 GB / 1 TB", JSON-LD "256GB 12GB" | "256 GB｜12 GB", "512 GB｜12 GB", "1 TB｜16 GB" | 동일(FAQ는 "256 Go", "1 To") | "256GB / 512GB / 1TB" |
| 가격(관측값) | 256GB £1,359, 512GB £1,529, 1TB £1,859 (JSON-LD) | 보고서: "$64.72/mo or $2,329.99". **[정정] 재수집 시 미재현** | "2 329,99 $" | 256GB Unlocked $1,149.99(정가 $1,399.99) |
| 화면 크기 | "6.9-inch" | "6.9-inch display" | "Écran 6,9 po" | [미확인] |
| 국가 고유 옵션 | Enterprise Edition, Certified Re-Newed(SM5) | Annual Upgrade Program, 전용 색상(Pink Gold, Silver Shadow) | 동일, 공기계 판매 명시 | Connectivity(통신사), Online Exclusive 색상 |
| 평점 | 4.9(1,950건, 비즈니스 PDP) | 4.8(40,456건, 10/27 재확인. 보고서 시점 40,395) | [미확인] | 4.8(18,591건) |

추가 관찰 [사실]: CA FAQ는 표준 색상에 White를 포함하지만 구매 도구에는 White가 없습니다. 같은 페이지 안의 불일치입니다.

#### 2.4.2 TV: Neo QLED QN90F 65" (2025)

모델 매핑: UK `QE65QN90FATXXU`, CA-EN/FR `QN65QN90FAFXZC`, US `QN65QN90FAFXZA`.

| 필드 | UK | CA-EN | CA-FR | US |
|---|---|---|---|---|
| 상품명 | "65" Neo QLED QN90F 4K Vision AI Smart TV (2025)" | **[사실] 현재 65" URL이 "55" Neo QLED 4K QN90F Vision AI Smart TV"(QN55QN90FAFXZC)를 표시** | 타이틀은 불어, 본문 상품명은 영어 | "65 Inch Class Neo QLED QN90F" |
| 화면 크기 | 65" | (현재 페이지) 55" | 65" | "65 Inch Class" |
| 대각선 실측 | 필드 없음 | Diagonal Screen Size 64.5"(보고서, 검색 스니펫 기준). **[정정] 현재 페이지는 55" 상품이라 54.6"** | 64.5" | 별도 필드 없음(정적 기준) |
| 주사율 | 120Hz (Up to 165Hz) | 120Hz (Up to 165Hz) | 120 Hz (jusqu'à 165 Hz) | "Motion Xcelerator 165Hz" |
| 해상도 | 4K (3,840 x 2,160) | 4K (3,840 x 2,160) | 4K (3,840 x 2,160) | [미확인] |
| 전원 | AC220-240V~ 50/60Hz | AC110-120V~ 50/60Hz | 110-120 V C.A. ~ 50/60 Hz | [미확인] |
| 소비전력 | Max 270 W, Typical 89.0 W, Stand-by 0.50 W | 보고서: Max 250 W, Typical 140 W. **[정정] 현재 페이지(55")는 Max 215 W, Typical 116 W** | Max 250 W, Typical 140 W, 대기 0.5 W | [미확인] |
| 에너지 규제 | Energy Efficiency Class F, Yearly 123 kWh(EU) | 필드 없음 | 필드 없음 | ENERGY STAR 배지만 |
| 국가별 서비스 값 | "Alexa (GB, DE, FR, IT, ES, AT, IE)" 등 국가코드가 값에 포함 | [미확인] | [미확인] | [미확인] |
| 치수·무게 | 1446.3 x 891.3 x 270.6 mm, 27.5 kg | [미확인] | 1446.3 x 891.3 x 270.6 mm, 포장 포함 33.6 kg | [미확인] |
| 사이즈 옵션 | 43/50/55/65/75/85/98/115 | 43/55/75/98/115 | 43/50/55/65/75/85/115 | 43–115(43/50/55/75 Out of stock, 65/85/98/115 표시 없음) |
| 판매 상태 | **[정정]** "Out of Stock"(보고서의 "No longer available"은 템플릿 문자열) | "Out of Stock"(색상·베젤 옵션) | JSON-LD outOfStock | 65" $2,499.99 |
| 평점 | 4.6 (142) | 4.8 (2,389, 현재 55" 페이지) | 4.8 (1,357) | 4.6 (992, 소비자 PDP) |
| 스펙 그룹 | Product Type / Display / Video / Audio / Smart Service / Smart Feature / Game Feature / Tuner / Connectivity / Design / Additional Feature / Accessibility / Power & Eco / Dimension / Weight / Accessory | 동일 체계 | 동일(불어) | [미확인] |

#### 2.4.3 가전: 드럼세탁기 (CA·US 동일 모델 WF50BG8300AVUS, UK는 근접 모델 WW11DB8B95GBU1)

| 필드 | UK (WW11DB8B95GBU1) | CA-EN | CA-FR | US |
|---|---|---|---|---|
| 상품명 | "Bespoke AI Front-Load Washing Machine Series 8 AI Energy 11KG" | "5.8 cu. ft. Front load Washer with Large Capacity and Super Speed" | "Laveuse, charge frontal, capacité Bespoke 5,8 pi³, technologie Super Speed" | "Front Load Washer Super Speed Wash \| Steam Wash \| 5.0 cu.ft." |
| 모델코드 표기 | WW11DB8B95GBU1 | WF50BG8300AVUS | WF50BG8300AVUS | **[신규]** title·og:title은 **WF50BG8300AEUS**, 헤딩·URL·가격 영역은 **WF50BG8300AVUS** |
| 용량 | 11.0 kg | 5.8 cu. ft. (IEC) / 5.0 cu. ft. (DOE) | "5,8 pi³"(제목·특징)와 "5.8 pi³"(선택기) 혼재. 라벨된 용량 필드는 없음 | 5.0 cu. ft.(IEC 표기 없음) |
| 에너지 | Class A, 32 kWh/100 cycles | Tier 3 (Advanced Tier), ENERGY STAR Yes, Energy Consumption (annual) 99(단위 누락) | Tier 3, ENERGY STAR "Yes"(영어), 99 kWh | "ENERGY STAR® Most Efficient" |
| 효율 지표 | Water 50 L, Spin Efficiency B(9kg 형제 모델) | IMEF 3.1, IWF 2.9 | 3.1, IWF 2.9 | [미확인] |
| 탈수 | 1400rpm | 1200 rpm | 1200 rpm | [미확인] |
| 치수 | 600 x 850 x 600 mm | **[정정]** 개별 Width/Height/Depth가 아니라 `Net Dimension (WxHxD) 686 x 984 x 850 mm` 한 필드 | "Dimensions (H x L x P) 686 × 984 × 850 mm / 27.0 × 38.7 × 33.5 inches"(라벨 순서 오류) | [미확인] |
| 무게 | [미확인] | Net Weight **98 kg**, Gross Weight **100 kg** | Poids net **"98 lbs"**와 단위 없는 "98" 공존, Poids brut **100 lbs** | [미확인] |
| 영어 값 잔존 | — | — | Yes/No, "Brushed Black", "Black Deco + Glass", 사이클·옵션명 대부분 영어 | — |
| 보증 | 5 Year Warranty | 모터 10년 | 모터 10년 | [미확인] |
| 가격 | [미확인] | [미확인](JS) | [미확인](JS) | $1,199.00 |
| 평점 | [미확인] | 4.7 (1,674), 리뷰 출처 "Samsung US" | 4.7 (1,828), "Publié à l'origine le Samsung US" | 4.6 (1,993) |

**[신규] 같은 모델, 같은 숫자, 다른 단위.** CA-EN은 98 kg / 100 kg, CA-FR은 98 lbs / 100 lbs입니다. 98 kg ≈ 216 lb이므로 FR 쪽 단위 표기 오류로 보입니다 [추정]. 어느 쪽이든 단위 변환만 하는 정규화 계층은 한쪽을 2.2배 틀리게 만듭니다.

**루비콘 시사점 (동일 모델)**
- "같은 모델코드 = 같은 답"이 성립하지 않습니다. 정규 스키마에 `capacity_value`, `capacity_unit`, `capacity_standard(IEC/DOE/EU)`를 둡니다.
- TV 화면은 `nominal_size_in`과 `diagonal_actual_in`(CA 전용)으로 분리합니다.
- 에너지 필드는 하나로 합치지 말고 국가별 규제 개념을 병렬 보존합니다(`energy_class_eu`, `kwh_per_100_cycles`, `energy_star`, `cee_tier`, `kwh_annual`, `energy_star_most_efficient`).
- 모델코드는 title·meta 하나에서 뽑지 말고 본문·JSON-LD·URL을 교차 검증합니다(US 세탁기 AEUS/AVUS 사례).
- 스펙 필드명 정렬 사전이 필요합니다(Screen Size ↔ Taille de l'écran, Child Lock ↔ Verrouillage parental, IMEF ↔ Facteur énergétique modifié intégré 등).
- US 스펙은 정적 HTML에서 확인되지 않았습니다. US 착수 전에 PDP 스펙 수집 PoC가 필요합니다.

### 2.5 URL 구조 및 Taxonomy 비교 (표 4)

| 항목 | UK | CA-EN | CA-FR | US |
|---|---|---|---|---|
| 루트 | /uk/ | /ca/ | /ca_fr/ | /us/ |
| PDP 패턴 | `/uk/{cat}/{subcat}/{slug}-{모델코드}/` | 동일 | /ca/와 slug 동일(영문 유지). 레거시 `/ca_fr/c/p/{MODEL}/{SUFFIX}` | `/us/{cat}/{subcat}/{slug}-sku-{모델코드}/`. 레거시 `/us/home-appliances/…`, `/us/televisions-home-theater/…` 공존 |
| 스마트폰 구매 | /uk/smartphones/galaxy-s26-ultra/buy/ | /ca/…/buy/?modelCode=… | /ca_fr/…/buy/ | /us/…/buy/{slug}-sku-{sku}/ (SKU별 URL) |
| PLP 필터 | `?crystal-uhd` 등 | `?smart` 등 | `?the-frame-tv` | `?shop=Buy+Online`, `?category_names=…` |
| 지원(모델) | /uk/support/model/{MODEL}/ | /ca/support/model/{MODEL}/ | /ca_fr/support/model/{MODEL}/ | [미확인] |
| 비즈니스 중복 PDP | /uk/business/… | /ca/business/… | /ca_fr/business/… | /us/business/… |
| 세탁 카테고리 | /uk/washers-and-dryers/ | /ca/laundry/ | /ca_fr/laundry/ | /us/laundry/washers/, /us/home-appliances/washers/ |
| 조리 카테고리명 | Ovens, Hobs, Hoods, Microwaves | Ranges, Wall Ovens, Cooktops, Ventilation | Cuisinières, Fours mural, Plaques de cuisson, Hottes | Wall Ovens, Ranges, Cooktops, Hoods |
| TV 사이즈 버킷 | "40 & 43 inch TVs" | "42 & 43 inch TVs" | "TV de 40 et 43 pouces"(/ca/와 불일치) | 사이즈별 PLP |
| 고유 1단계 카테고리 | Samsung Week | Samsung Week | Samsung Week | **Audio**. **[정정] US에도 Samsung Week 있음** |
| 언어 신호 | og:locale en-GB | og:locale en-CA | og:locale fr-CA, 언어 선택기 "Canada / Français". hreflang [미확인] | og:locale `en` |

**루비콘 시사점**
- CA-EN/CA-FR은 `/ca/ ↔ /ca_fr/` 치환으로 문서 쌍을 만들 수 있습니다. `doc_group_id`로 묶으면 EN·FR 교차 검색, 번역 누락 탐지, 병렬 평가셋 구축 비용이 줄어듭니다.
- 모델코드는 URL 말미에서 추출합니다(UK·CA `-{model}/$`, US `-sku-{model}/$`). US는 SKU별 URL이라 문서 수가 크게 늘어나므로 모델 패밀리 단위로 접고 SKU는 메타데이터로 둡니다 [추정].
- /business/ 중복 PDP와 레거시 경로는 canonical 기준으로 dedupe하거나 `channel=b2b`로 분리합니다.
- **URL과 콘텐츠가 어긋납니다.** /ca/ QN90F 65" URL이 55" 상품을 표시합니다. URL slug로 사이즈·모델을 추론하지 말고 본문·JSON-LD SKU를 기준으로 삼습니다.
- **[신규] 단종 상품 URL이 목록 페이지로 바뀝니다.** CA WF50T8500AV URL이 상품 없는 세탁기 카테고리 목록을 반환합니다(soft 404). 크롤러가 이를 걸러내지 않으면 엉뚱한 페이지가 해당 SKU로 인덱싱됩니다.

### 2.6 CA-FR 콘텐츠 동등성(parity) 진단

| 점검 항목 | 결과 | 판정 |
|---|---|---|
| URL·구조 | /ca/와 동일 경로·slug, GNB 구성 동일 | 동등 |
| 정책 문서 | 반품 15일, 가격 보장, 약관 불어판 존재 | 대체로 동등 |
| 스펙 필드명 | 대부분 번역 | 부분 동등 |
| 스펙 값 | **[정정] 카테고리별 차이.** TV(QN90F)는 영어 값이 "Yes" 1건뿐이고 대부분 "Oui". 세탁기는 Yes/No, 색상명, 사이클·옵션명이 대부분 영어 | 불완전(가전 중심) |
| 숫자 형식 | 가격은 "2 329,99 $". 스펙 소수점은 점(64.5", 0.5 W, 3.1)과 쉼표(5,8 pi³)가 혼재. 해상도는 천 단위 쉼표 유지 | 불일치 |
| 단위 | 같은 세탁기 무게가 EN kg, FR lbs **[신규]** | 불일치 |
| 상품명 | 타이틀 불어, 본문 상품명 영어 | 혼합 |
| 사이즈·라인업 | QN90F: FR 43/50/55/65/75/85/115, EN 43/55/75/98/115 | 불일치 |
| 리뷰 | 스페인·독일·프랑스·UK·호주·US 원문 리뷰가 번역 없이 노출 | 불일치 |
| UI 공통 문자열 | "Out of Stock", "Product Ratings" 등 영어 잔존 | 불완전 |
| 오탈자·메타 | "Colombie-Britiannique", "Samsug Care+", "charge frontal" 등 | 품질 이슈 |
| 상품 수(PLP) | JS 렌더링 | 미확인 |
| hreflang | og:locale만 확인 | 미확인 |

**루비콘 시사점**
- CA-FR을 CA-EN 번역본으로 간주해 인덱스를 생략하면 안 됩니다. 사이즈 옵션, 리뷰, 단위가 다릅니다.
- 수치 필드는 같은 모델코드면 EN 기준으로 FR을 교차 검증하는 용도로 쓸 수 있습니다. 단, 무게 단위 불일치처럼 **교차 검증에서 충돌이 나면 플래그**를 세워야 합니다.
- 숫자 파서는 로캘을 인지하되 ca_fr 안에서도 점과 쉼표를 모두 허용하고, 필드 타입별(가격, 해상도, 소수)로 분리합니다.
- 혼합 언어(불어 라벨 + 영어 값)가 많으므로 다국어 임베딩(EN·FR 공유 공간)과 언어별·영어 분석기를 병행하는 하이브리드 검색이 적합합니다 [추정]. 단위 동의어 확장(pi³ ↔ cu. ft., po ↔ inch, Go/To ↔ GB/TB)도 필요합니다.
- 평가셋은 EN·FR 병렬 질문 쌍으로 만들고, (a) 수치 일치, (b) FR 전용 차이, (c) 혼합 언어 값 검색, (d) EN/FR 단위 충돌을 포함합니다.

### 2.7 UK 파이프라인 재사용과 신규 구축

| 구성요소 | CA-EN | CA-FR | US |
|---|---|---|---|
| 크롤러(URL 발견) | 재사용(접두만 변경) | 재사용(/ca/ 치환) | **신규**(`-sku-`, SKU 폭증, 레거시 경로) |
| PDP 파서 | 재사용 | 재사용 + 번역 필드 사전 | **신규**(정적 스펙 미확인) |
| JSON-LD 가격 파서 | 재사용(CAD) | 재사용 | 수정(`priceSpecification`) |
| 모델코드 추출 | 재사용 + 본문·JSON-LD 교차 검증 | 동일 | 신규 + title/본문 불일치 처리 |
| 단위 정규화 | **신규**(cu.ft/lb/inch, IEC/DOE) | 신규 + 소수점 혼용 + EN/FR 단위 충돌 검출 | 신규(야드파운드) |
| 규제 필드 | 신규(ENERGY STAR, CEE Tier, IMEF/IWF) | 동일 + 번역 | 신규(Most Efficient) |
| 정책·금융 문서 | 재수집, 구조 재사용 | 재사용 | 신규(Offer Program, TD Bank, Carrier, Access) |
| 청킹 | 재사용(스펙 그룹 단위) | 재사용 + 언어 태그 | 모델 패밀리 단위 SKU 접기 |
| 리뷰 처리 | 수정(origin_country 필터) | 수정(타국어 필터·번역) | 재사용 가능성 높음 [미확인] |
| 단종·soft 404 처리 | 신규 | 신규 | 신규 |

### 2.8 확산 단계별 리스크와 권장사항

**UK → CA (4~6주 규모, 추정)**
1. 더미 템플릿 가격(£ 값) 인덱스 오염 → 본문 가격 텍스트 차단, JSON-LD·API만 사용.
2. 주별 가격 차이 → 크롤링 시 province 쿠키 고정(예: Ontario), 답변에 "주별로 다를 수 있음" 표시.
3. 단위 혼용과 데이터 오류 → 값 범위 검증 규칙. EN/FR 같은 모델의 단위 충돌 검출.
4. CA-FR 품질 이슈 → 언어 감지 필터, EN 교차 검증.
5. URL–콘텐츠 불일치(65" URL → 55" 상품)와 soft 404 → SKU 기준 키, 목록 페이지 판별.
6. CA 단계에서 국가 무관 정규 스키마 v1을 확정하면 US 비용이 줄어듭니다.

**CA → US (CA 대비 2배 이상, 추정)**
1. SKU 폭증(색상×용량×통신사) → 모델 패밀리 문서 + SKU 메타데이터.
2. PDP 스펙 수집 경로가 다름 → 착수 전 수집 PoC.
3. 가격 의미가 다름(세금 별도, 정가·할인가, 회원가, 통신사 할인) → `price_context` 필드.
4. 정책·금융 엔티티가 완전히 다름 → 국가 전용 FAQ 인덱스.
5. og:locale이 `en` → sitecode와 URL 접두로 국가 판별.
6. title·meta와 본문 모델코드 불일치 → 다중 소스 교차 검증.

**공통**
- canonical URL, sitecode, 모델코드를 3중 키로 씁니다.
- 국가별 평가셋은 (1) 동일 모델 국가 간 차이, (2) 정책 수치, (3) 단위·통화 변환, (4) 국가 전용 기능 네 축으로 구성하고, CA는 EN·FR 병렬로 만듭니다.
- 리뷰 수·가격·재고는 며칠 사이에도 바뀝니다(예: CA-FR 세탁기 리뷰 1,623 → 1,828). 평가셋 정답으로 쓰지 않습니다.

---

## 3. 정적 재수집 결과 (정오표, 2026-10-27 23시)

방법: 같은 정적 수집 방식으로 주요 PDP와 홈을 다시 읽어 보고서 주장과 대조했습니다. 값은 요약 모델을 거쳐 추출한 것이므로, 화면 노출 여부와 hreflang은 여전히 판단할 수 없습니다.

### 3.1 보고서와 다르거나 새로 확인된 항목

| # | 항목 | 보고서 기재 | 재확인 결과 | 구분 |
|---|---|---|---|---|
| 1 | CA-EN 세탁기 치수 | Width 686 / Height 984 / Depth 850 mm 개별 필드 | `Net Dimension (WxHxD) 686 x 984 x 850 mm` 단일 필드 | 정정 |
| 2 | 세탁기 무게 단위 EN/FR | FR "Poids net 98(단위 없음)", "Poids brut 100 lbs" | EN 98 kg / 100 kg, FR "98 lbs"·"98" / 100 lbs | 신규(단위 충돌) |
| 3 | US 세탁기 모델코드 | 없음 | title·og:title **AEUS**, 본문·URL **AVUS** | 신규 |
| 4 | CA S26 `SM-S948WZDEXAC` | 512GB, $2,329.99 | 검색 제목 "1 TB", 정적 HTML에 코드 없음, 가격 미재현 | 충돌 |
| 5 | CA QN90F 65" URL 스펙 값 | Diagonal 64.5", 250 W / 140 W | 현재 페이지는 55" 상품: 54.6", 215 W / 116 W | 정정 |
| 6 | UK QN90F 판매 상태 | "No longer available" | "Out of Stock"(No longer available은 템플릿 문자열) | 정정 |
| 7 | US GNB | Samsung Week는 UK·CA 전용 | US에도 Samsung Week, Find a Store | 정정 |
| 8 | CA 홈 검색 | "Search under maintenance" | CA 정상, US 점검 유지 | 시점 차이 |
| 9 | CA "Width 27 mm" 오류 사례 | WF50T8500AV PDP | URL이 상품 없는 카테고리 목록으로 바뀜 | 재현 불가(soft 404, 신규) |
| 10 | CA-FR 영어 값 잔존 | 전반적으로 Yes/No 잔존 | TV는 "Yes" 1건, 세탁기는 다수 | 정정(카테고리별) |
| 11 | 리뷰 수 | 각 수치 | S26 CA 40,395 → 40,456, CA-FR 세탁기 1,623 → 1,828 등 | 시점 차이 |

### 3.2 보고서대로 재확인된 항목

- CA QN90F 65" URL이 55" 상품(QN55QN90FAFXZC)을 표시
- £/$ 더미 문자열: UK·CA·CA-FR QN90F, CA·CA-FR 세탁기(CA-FR에도 "VAT Inclusive")
- UK QN90F: Energy Efficiency Class F, Yearly 123 kWh, AC220-240V, Max 270 W, Typical 89.0 W, 1446.3 x 891.3 x 270.6 mm, 27.5 kg, 다음날 배송 문구
- CA-FR QN90F: 사이즈 43/50/55/65/75/85/115, 64.5", 250/140/0.5 W, 33.6 kg, 4.8 (1,357), 타국 리뷰 출처
- CA-EN QN90F 사이즈 옵션 43/55/75/98/115
- CA 세탁기: 5.8 cu. ft. (IEC) / 5.0 cu. ft. (DOE), Tier 3, 99(단위 누락), IMEF 3.1, IWF 2.9, 1200 rpm, 모터 10년 보증
- US: og:locale "en", 세탁기 $1,199.00·5.0 cu.ft.·IEC 미표기, QN90F 65" $2,499.99
- CA 홈: 주 선택 기본값 Quebec, 포인트 0.7% 배너

---

## 4. 렌더링 검증 키트

### 4.1 배경

작업 환경에서 samsung.com 접속이 네트워크 정책으로 차단되어 헤드리스 브라우저 확인을 직접 하지 못했습니다. 대신 사용자 PC에서 실행하면 렌더링 결과와 하이라이트 스크린샷, 비교 리포트를 만들어 주는 키트를 작성했습니다.

### 4.2 구성

| 파일 | 내용 |
|---|---|
| `verify.py` | Playwright 기반 실행 스크립트. 페이지 준비(쿠키 동의, 캐나다 주 선택, 전체 스크롤, 스펙 펼치기) → 항목별 측정 → 하이라이트 스크린샷 → 판정 → `report.html`, `evidence.json` 생성 |
| `claims.json` | 검증 항목 17개 정의(보고서 기재, 정적 재수집 결과, 루비콘 영향, 대상 URL, 측정 방법, 기대값) |
| `README.md` | 설치·실행·결과 해석·문제 해결·항목 추가 방법 |

### 4.3 실행

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install playwright
playwright install chromium

python verify.py                      # 전체 17개 항목, 21개 페이지, 약 15~20분
python verify.py --only C01,C03,C07   # 일부만
python verify.py --headed --channel chrome   # 봇 차단 시
```

결과: `out/run-YYYYmmdd-HHMMSS/report.html`, `evidence.json`, `shots/*.png`

### 4.4 측정 방식

- **텍스트 3단계 카운트**: 원본 HTML(정적 크롤러가 보는 것) / 렌더링 DOM(JS 실행 후, 숨김 포함) / 화면 텍스트(`innerText`, 숨김 제외)
  - 원본 > 0, 화면 = 0 → 숨김 요소·템플릿·메타 값. 크롤러에서 걸러야 함
  - 화면 > 0 → 실제 노출. 스크린샷 빨간 박스로 위치 확인
  - 원본 = 0, DOM > 0 → JS 실행 후에만 생김. 정적 수집으로는 안 보임
- **판정**: 보고서와 일치 / 보고서와 다름 / 새로 확인(보고서 미확인 항목) / 판단 불가 / 접속 차단·오류
- **측정 유형**: `text`, `spec`(라벨 옆 값), `options`(선택기 옵션), `links`(href 패턴), `selected`(선택 상태), `selector_text`, `meta`(title·lang·og:locale·canonical·hreflang), `jsonld`(Product 주요 필드), 항목 단위 `compare`(두 옵션 집합 비교)

### 4.5 검증 항목

| ID | 항목 | 중요도 | 대상 | 확인 내용 |
|---|---|---|---|---|
| C01 | £/$ 더미 가격 — 화면에도 보이는가 | 높음 | CA-EN·CA-FR·UK QN90F, CA 세탁기 | 더미 문자열 원본/DOM/화면 카운트, JSON-LD 실제 가격 |
| C02 | CA 65" URL → 55" 상품 | 높음 | CA-EN QN90F | h1, QN55 코드 화면 노출, JSON-LD SKU |
| C03 | QN90F 사이즈 옵션 EN vs FR | 중간 | CA-EN·CA-FR QN90F | 선택기 옵션 집합, href 사이즈, 두 집합 비교 |
| C04 | US QN90F 스펙 렌더링 | 중간 | US QN90F | 스펙 필드 존재, $2,499.99 |
| C05 | US S26 Ultra 가격·통신사·스펙 | 중간 | US S26 Unlocked | JSON-LD 통화, $1,149.99/$1,399.99, 통신사 선택지, 스펙 |
| C06 | 세탁기 용량 IEC/DOE, FR 소수점 | 높음 | CA·US·CA-FR 세탁기 | Washing Capacity, 5.0 cu.ft., IEC 미표기, 5,8/5.8 pi³ |
| C07 | 세탁기 무게·치수 EN vs FR | 높음 | CA·CA-FR 세탁기 | Width/Net Dimension, Net/Gross Weight, Poids net/brut |
| C08 | US 세탁기 모델코드 불일치 | 중간 | US 세탁기 | title·canonical, AEUS/AVUS 노출 |
| C09 | SM-S948WZDEXAC 실제 용량 | 중간 | CA S26 구매(modelCode) | 선택된 용량·색상, $2,329.99 |
| C10 | CA 세금 표기 | 중간 | CA-EN·CA-FR S26 구매 | 세금 문구(HST/GST/PST/QST, TPS/TVQ/TVH) |
| C11 | CA EnerGuide 표기 | 낮음 | CA·CA-FR 세탁기 | EnerGuide/ÉnerGuide 문구 |
| C12 | US GNB Samsung Week | 낮음 | US 홈 | 헤더의 Samsung Week, Audio |
| C13 | og:locale·hreflang | 중간 | 4개국 홈 | og:locale 값, hreflang 렌더링·원본 |
| C14 | 타국 리뷰 혼재 | 중간 | UK·CA-FR QN90F, CA 세탁기 | "Originally posted on Samsung …" 등 |
| C15 | 금융 조건 상충 | 중간 | UK Finance, CA Affirm | 14.9% APR, 36/24개월 |
| C16 | 반품 기간 | 높음 | UK·CA FAQ, US 판매 약관 | 14일, 15일·7일, 15일·restocking fee |
| C17 | "Width 27 mm" 사례 | 낮음 | CA WF50T8500AV | 헤딩, Width 값(soft 404 확인) |

### 4.6 상태와 주의

- 모의 페이지(숨김 템플릿 가격, 쿠키 배너, 주 선택 모달, 스펙 펼치기, 사이즈 선택기, JSON-LD)로 모든 측정 유형과 판정 흐름을 확인했습니다.
- **실제 samsung.com에서는 아직 실행하지 않았습니다.** 첫 실행에서 Akamai 봇 차단, 주 선택 모달 문구, 스펙 펼치기 버튼 문구에 따라 조정이 필요할 수 있습니다(README 5장).
- 가격·리뷰 수·재고 항목이 "보고서와 다름"이면 보고서 오류인지 시점 변동인지 스크린샷으로 구분해야 합니다.

---

## 5. 의사결정 필요 사항

1. **불어 인덱스 분리 여부.** 권장: 단일 인덱스 + `lang`, `country`, `doc_group_id` 메타데이터 + 다국어 임베딩(URL 1:1 대응, 수치 필드 공유가 근거). FR 전용 랭킹 튜닝이나 품질 격리가 중요하면 별도 인덱스. 판단에는 EN·FR 혼합 값 비중과 FR 트래픽 목표가 필요합니다.
2. **스펙 필드 표준화 범위.** 권장: 핵심 20~40개 필드(가격, 용량, 화면, 전력, 치수, 무게, 에너지)만 정규화하고 나머지는 원문 텍스트 청크로 유지. 국가 고유 필드는 `country_specific` 네임스페이스로 보존.
3. **에너지·규제 필드 처리.** 권장: 국가별 병렬 보존. 단일 `efficiency_score` 추상화는 비권장.
4. **리뷰 사용 범위.** 타국 원문 리뷰를 제외 / 번역 포함 / 그대로 둘지.
5. **US SKU 단위.** 통신사 변형을 별도 문서로 둘지, 모델 패밀리로 접을지.
6. **가격 응답 정책.** 실시간 가격을 답변에 포함할지, 링크로만 안내할지.
7. **CA 크롤링 기준 주.** 하나로 고정할지(검증 키트 기본값 Ontario), 다중 주 가격을 저장할지.
8. **B2B(/business/) 콘텐츠.** 포함 여부와 채널 분리 방식.
9. **[신규] EN/FR 수치 충돌 처리.** 같은 모델에서 단위·값이 충돌할 때(98 kg vs 98 lbs) 어느 쪽을 기준으로 할지, 양쪽 모두 플래그하고 답변에서 제외할지.
10. **[신규] 단종·soft 404 처리.** 상품 URL이 목록 페이지로 바뀐 경우 문서를 삭제할지, 단종 상태로 보존할지.

---

## 6. 미확인 항목과 다음 단계

**미확인 (검증 키트 대상)**
- £ 더미 가격의 실제 화면 노출 여부(C01)
- US PDP 스펙 필드 전반(C04, C05)
- hreflang `<link>` 태그(C13)
- CA 세금 표기 문구(C10), EnerGuide 라벨(C11)
- SM-S948WZDEXAC의 실제 용량(C09)

**미확인 (키트 범위 밖)**
- CA-FR과 CA-EN의 PLP 상품 수
- UK 일반 보증 기간 페이지, US 지원 모델 경로
- CA-FR 대형가전 7일 반품 규정 반영 여부

**다음 단계**
1. 사용자 PC에서 검증 키트 실행 → `report.html`, `evidence.json` 공유
2. 결과를 반영해 본 문서의 [미확인]·[추정] 항목 확정
3. 정규 스키마 v1 초안(가격·용량·화면·에너지·무게 필드)과 EN/FR 충돌 검출 규칙 설계

---

## 7. 출처

**사이트 홈**
- https://www.samsung.com/uk/
- https://www.samsung.com/ca/
- https://www.samsung.com/ca_fr/
- https://www.samsung.com/us/

**TV (QN90F)**
- https://www.samsung.com/uk/tvs/qled-tv/qn90f-65-inch-neo-qled-4k-mini-led-smart-tv-qe65qn90fatxxu/
- https://www.samsung.com/ca/tvs/qled-tv/qn90f-65-inch-neo-qled-4k-vision-ai-smart-tv-qn65qn90fafxzc/
- https://www.samsung.com/ca_fr/tvs/qled-tv/qn90f-65-inch-neo-qled-4k-vision-ai-smart-tv-qn65qn90fafxzc/
- https://www.samsung.com/us/tvs/neo-qled/65-class-neo-qled-4k-tv-qn90f-sku-qn65qn90fafxza/
- https://www.samsung.com/us/business/tvs/qled-tv/65-class-neo-qled-4k-tv-qn90f-sku-qn65qn90fafxza/

**스마트폰 (Galaxy S26 Ultra)**
- https://www.samsung.com/uk/smartphones/galaxy-s26-ultra/buy/
- https://www.samsung.com/uk/business/smartphones/galaxy-s/galaxy-s26-ultra-black-512gb-sm-s948bzkgeub/buy/
- https://www.samsung.com/uk/smartphones/galaxy-s/galaxy-s26-ultra-black-256gb-certified-re-newed-sm5s948bzkdeub/
- https://www.samsung.com/ca/smartphones/galaxy-s26-ultra/buy/
- https://www.samsung.com/ca/smartphones/galaxy-s26-ultra/buy/?modelCode=SM-S948WZDEXAC
- https://www.samsung.com/ca_fr/smartphones/galaxy-s26-ultra/buy/
- https://www.samsung.com/us/smartphones/galaxy-s26-ultra/buy/galaxy-s26-ultra-256gb-unlocked-sku-sm-s948ulbaxaa/
- https://www.samsung.com/us/smartphones/galaxy-s26-ultra/buy/galaxy-s26-ultra-256gb-at-t-sku-sm-s948uzkaatt/

**세탁기**
- https://www.samsung.com/uk/washers-and-dryers/washing-machines/ww8400d-front-loading-smartthings-ai-energy-made-a-40-percent-extra-energy-efficiency-ai-ecobubble-11kg-black-ww11db8b95gbu1/
- https://www.samsung.com/ca/laundry/washing-machines/wf8300b-front-loading-large-capacity-super-speed-energy-star-certified-5-cu-ft-black-wf50bg8300avus/
- https://www.samsung.com/ca_fr/laundry/washing-machines/wf8300b-front-loading-large-capacity-super-speed-energy-star-certified-5-8-cu-ft-black-wf50bg8300avus/
- https://www.samsung.com/us/laundry/washers/front-load-wf8300b-front-loading-large-capacity-super-speed-energy-star-certified-5-cu-ft-brushed-black-sku-wf50bg8300avus/
- https://www.samsung.com/us/home-appliances/washers/front-load/5-0-cu-ft-extra-large-capacity-smart-front-load-washer-with-super-speed-wash-and-steam-in-brushed-black-wf50bg8300avus/
- https://www.samsung.com/ca/laundry/washing-machines/front-load-5-8-cu-ft-black-caviar-wf50t8500av-a5/

**정책·금융·프로그램**
- https://www.samsung.com/uk/samsung-finance/
- https://www.samsung.com/ca/affirm-financing/
- https://www.samsung.com/ca/offer/mobile/
- https://www.samsung.com/us/shop/offer-program/
- https://www.samsung.com/us/shop/access/tv/frequently-asked-questions/
- https://www.samsung.com/uk/shop-faq/returns-and-cancellations/what-is-the-returns-period/
- https://www.samsung.com/ca/shop-faq/returns-and-cancellations/what-is-the-returns-period/
- https://www.samsung.com/ca_fr/shop-faq/returns-and-refunds
- https://www.samsung.com/us/terms-of-sale/
- https://shop.samsung.com/us/cart

**기타 (URL·taxonomy·지원)**
- https://www.samsung.com/ca/tvs/all-tvs/
- https://www.samsung.com/ca_fr/tvs/
- https://www.samsung.com/ca_fr/offer/tvav/
- https://www.samsung.com/ca_fr/termsandconditions/
- https://www.samsung.com/ca_fr/shop-faq/price-match/
- https://www.samsung.com/uk/support/model/SM-S948BZKDEEB/
- https://www.samsung.com/ca_fr/support/model/QN65QN90FAFXZC/
