# RRG Sector Atlas

[**공개 RRG 상황판 열기**](https://zqvo04.github.io/RRG/)

**RRG Sector Atlas**는 미국 대표 섹터 ETF 11개의 움직임을 SPY와 비교해, 어느 섹터가 상대적으로 강해지거나 약해지는지 한 화면에서 살펴보는 주간 분석 도구입니다. 이 프로젝트는 공개 가격 데이터를 바탕으로 한 **RRG-style proxy**이며, 공식 JdK 지표 또는 투자 자문 서비스라고 주장하지 않습니다. RRG라는 시각화 방법의 핵심은 여러 자산의 상대 성과와 상대 성과의 변화를 공통 벤치마크 위에서 함께 비교하는 데 있습니다.[1]

> **핵심 원칙:** 이 지도는 “가격이 올랐는가”가 아니라 “SPY와 비교했을 때 어떤 섹터가 상대적으로 강하거나 약한가”를 보여 줍니다. 따라서 단독 매매 신호가 아니라, 추가 분석이 필요한 섹터를 빠르게 좁히는 탐색 도구로 사용해야 합니다.[1] [2]

## 목차

| 항목 | 내용 |
|---|---|
| [RRG란 무엇인가](#rrg란-무엇인가) | 상대강도와 상대 모멘텀을 한 지도에 표시하는 방법 |
| [사분면 읽기](#사분면-읽기) | Leading·Weakening·Lagging·Improving의 의미 |
| [궤적 해석](#궤적해석-시작점-방향-최신점) | 시작점·최근 방향·최신 위치와 4·8·12주 비교법 |
| [RRG Atlas 방법론](#rrg-atlas-방법론) | 현재 프로젝트의 데이터·계산식·유니버스 |
| [데이터 신뢰성](#데이터-신뢰성과-갱신) | 수집·검증·저장·공개 배포 흐름 |
| [활용 순서](#권장-활용-순서) | 상황판을 읽는 실용적인 순서 |

---

## RRG란 무엇인가

**RRG(Relative Rotation Graph)**는 여러 종목·섹터·자산군을 동일한 벤치마크와 비교해, 상대 성과의 **추세**와 그 추세의 **변화 속도**를 산점도 형태로 표현하는 분석 방식입니다. 전통적인 개별 가격 차트가 한 자산의 절대 가격 흐름을 주로 본다면, RRG는 “A가 B보다 나은가”라는 상대 비교를 중심에 둡니다.[1]

RRG의 가로축은 보통 상대 성과 추세를 나타내는 **RS-Ratio**, 세로축은 그 상대 성과가 좋아지거나 나빠지는 속도를 나타내는 **RS-Momentum**입니다. 두 축의 기준선 100은 해당 값이 상대적 강세·약세 또는 개선·둔화의 경계에 있음을 뜻합니다. 같은 벤치마크로 계산한 값끼리는 비교할 수 있으므로, 여러 섹터를 동일 지도 안에서 비교할 수 있습니다.[1] [2]

```text
가로축: RS-RATIO     → SPY 대비 상대 성과의 추세·강도
세로축: RS-MOMENTUM  → 상대 성과 추세가 개선·둔화되는 속도
기준선: 100          → 각 축의 상대적 강세/약세 경계
```

이 지도는 상대적인 상태를 나타냅니다. 예를 들어 에너지 섹터가 Leading에 있다는 것은 **해당 기간에 SPY보다 상대적으로 강한 상태**라는 뜻이지, 가격이 반드시 상승 중이거나 다음 주에도 상승한다는 보장은 아닙니다. 반대로 Lagging은 SPY 대비 상대적 약세를 뜻하며, 절대 가격의 상승·하락과는 별개의 개념입니다.

## 사분면 읽기

가로축과 세로축이 100에서 교차하면 네 개의 사분면이 만들어집니다. RRG Atlas는 Ratio와 Momentum의 위치를 기준으로 아래와 같이 분류합니다.[1] [3]

| 사분면 | 조건 | 상대 흐름의 해석 | 확인할 질문 |
|---|---|---|---|
| **Leading** | Ratio ≥ 100, Momentum ≥ 100 | 상대 성과 추세가 강하고, 그 강세가 유지·개선되는 구간입니다. | 강세가 지속되는가, 과열·둔화 징후는 없는가? |
| **Weakening** | Ratio ≥ 100, Momentum < 100 | 상대 성과는 아직 강하지만, 상대 모멘텀이 둔화되는 구간입니다. | 강세 추세의 일시 조정인가, 추세 약화의 시작인가? |
| **Lagging** | Ratio < 100, Momentum < 100 | 상대 성과 추세가 약하고, 약세 모멘텀도 이어지는 구간입니다. | 약세가 지속되는가, 모멘텀 반전 신호가 나타나는가? |
| **Improving** | Ratio < 100, Momentum ≥ 100 | 상대 성과는 아직 약하지만, 상대 모멘텀이 개선되는 구간입니다. | 회복 시도가 지속되어 Ratio도 100을 넘는가? |

일반적인 교과서적 회전은 **Leading → Weakening → Lagging → Improving → Leading**의 시계 방향으로 설명되곤 합니다. 다만 실제 시장의 궤적은 원형일 필요가 없고, 모든 섹터가 네 사분면을 순서대로 거치는 것도 아닙니다. 따라서 사분면 하나만으로 결론 내리기보다, **어디서 출발해 어느 방향으로 얼마나 이동했는지**를 함께 봐야 합니다.[1]

### 가로축과 세로축의 역할 차이

RS-Ratio는 상대 성과의 추세를 더 직접적으로 나타내므로 “현재 상대적 리더인가”를 볼 때 우선순위가 높습니다. RS-Momentum은 RS-Ratio의 변화율을 보므로 추세 전환의 초기 단서를 줄 수 있지만, 일시적인 교차가 곧바로 추세 반전으로 이어지지는 않습니다.[1] [2]

| 먼저 볼 요소 | 이유 | 해석 예시 |
|---|---|---|
| **RS-Ratio의 100선 위치** | 현재 상대 강세·약세의 상태를 구분 | 왼쪽에서 오른쪽으로 이동하면 상대 성과 추세의 개선 가능성을 검토 |
| **RS-Momentum의 변화** | 상대 추세가 가속·감속하는 초기 단서 | Leading에서 Momentum이 100 아래로 내려가면 둔화 여부를 점검 |
| **궤적의 길이·방향** | 기간 내 변화의 크기와 최근 이동을 확인 | 짧고 반복되는 경로보다 일관된 방향의 이동을 추가 확인 |

## 궤적 해석: 시작점, 방향, 최신점

RRG Atlas의 각 섹터 궤적은 선택한 기간 동안의 주간 관측점을 순서대로 연결합니다. 기본 화면에서는 4주·8주·12주 표시 기간을 바꿔, 단기 변화와 조금 더 긴 변화가 같은 방향을 가리키는지 비교할 수 있습니다. 표시 기간을 길게 할수록 더 많은 문맥을 얻을 수 있지만, 여러 섹터를 동시에 볼 때는 선이 겹칠 수 있으므로 짧은 기간부터 확인하는 편이 좋습니다.[1]

| 화면 표식 | 뜻 | 읽는 방법 |
|---|---|---|
| **속이 빈 작은 원 `○`** | 선택 기간의 시작점 | 현재 위치와의 거리를 비교해 기간 내 변화 폭을 파악합니다. |
| **연결선** | 각 주간 관측점의 순서 | 선의 흐름이 어느 사분면을 지나왔는지 확인합니다. |
| **선 끝의 화살촉 `→`** | 가장 최근 한 주의 이동 방향 | 지금의 상대 변화가 어느 축을 향하는지 읽습니다. |
| **작은 채움 원 `●`** | 최신 관측점 | 현재 사분면과 기준선에서의 거리를 확인합니다. |

선택한 섹터를 누르면 오른쪽 **선택 섹터** 패널에서 더 구체적인 변화를 확인할 수 있습니다. 이 패널은 최근 1주의 Ratio·Momentum 변화, 선택 기간의 시작 사분면과 현재 사분면, 누적 이동 거리, Ratio·Momentum 누적 변화량을 제공합니다. 지도는 방향을 이해하는 데, 패널의 수치는 변화 폭을 비교하는 데 사용하면 좋습니다.

> **해석 예시:** 어떤 섹터가 Improving에 있고 화살촉이 오른쪽 위를 가리키며, 8주 누적 Ratio와 Momentum이 모두 개선됐다면 상대 회복이 진행 중인지 추가 확인할 후보가 될 수 있습니다. 그러나 Improving 자체가 매수 신호를 뜻하지는 않습니다. Ratio가 여전히 100 아래일 수 있고, 다음 주에 이동이 되돌려질 수도 있습니다.

## RRG Atlas 방법론

### 비교 대상과 데이터 기준

RRG Atlas는 **SPY**를 공통 벤치마크로 사용하고, 아래 11개 미국 Select Sector SPDR ETF를 비교합니다. 화면에서는 티커보다 한국어 섹터명을 먼저 보여 주되, 티커를 보조 정보로 함께 표시합니다.

| 티커 | 화면 섹터명 | 영문 자산명 |
|---|---|---|
| XLB | 소재 | Materials Select Sector SPDR Fund |
| XLC | 커뮤니케이션 | Communication Services Select Sector SPDR Fund |
| XLY | 경기소비재 | Consumer Discretionary Select Sector SPDR Fund |
| XLP | 필수소비재 | Consumer Staples Select Sector SPDR Fund |
| XLE | 에너지 | Energy Select Sector SPDR Fund |
| XLF | 금융 | Financial Select Sector SPDR Fund |
| XLV | 헬스케어 | Health Care Select Sector SPDR Fund |
| XLI | 산업재 | Industrial Select Sector SPDR Fund |
| XLK | 정보기술 | Technology Select Sector SPDR Fund |
| XLRE | 부동산 | Real Estate Select Sector SPDR Fund |
| XLU | 유틸리티 | Utilities Select Sector SPDR Fund |

모든 계산은 **주간 조정종가(weekly adjusted close)**를 기반으로 하며, 관측 주차는 미국 동부시간 정규장 마감 기준의 완료된 금요일에 맞춥니다. 금요일이 휴장일이면 해당 주의 마지막 거래일 종가를 사용하고, 관측 날짜는 그 주의 금요일로 정규화합니다.[3] [4]

### 이 프로젝트의 계산식

RRG Atlas는 공식 JdK RS-Ratio·RS-Momentum의 구현을 복제하지 않습니다. 대신 공개 가격 데이터에서 재현 가능하도록 아래 `rrg_proxy_v2` 산식을 사용합니다. 이 차이를 이해하는 것은 중요합니다. 화면의 수치와 사분면은 **이 프로젝트의 정의**에 따른 것이며, 다른 RRG 서비스의 수치와 일치해야 하는 것은 아닙니다.[3]

```text
relative_price[t] = sector_adjusted_close[t] / SPY_adjusted_close[t]
ratio[t]          = 100 × relative_price[t] / EMA(relative_price, 13)[t]
momentum[t]       = 100 × ratio[t] / ratio[t - 4]
```

| 설정 | 현재 값 | 의미 |
|---|---:|---|
| 계산용 이력 | 104주 | 지표 계산에 사용하는 주간 이력 범위 |
| 최소 이력 | 52주 | 발행을 허용하기 위한 최소 완료 주간 수 |
| Relative Price EMA | 13주 | Ratio 기준선 계산에 쓰는 평활화 기간 |
| Momentum 지연 | 4주 | Ratio 변화율을 비교하는 간격 |
| 저장 가능한 최대 궤적 | 26주 | 스냅샷이 보관하는 최대 궤적 길이 |
| 화면 표시 선택지 | 4·8·12주 | 지도에서 빠르게 비교할 수 있는 기간 |

## 데이터 신뢰성과 갱신

데이터는 Alpha Vantage에서 주간 조정가격을 수집하며, API 키와 원본 응답은 Git 또는 정적 배포물에 저장하지 않습니다. 매주 자동 작업이 수집·계산·검증·발행·배포를 한 흐름으로 수행합니다. 별도의 관계형 DB 대신 GitHub 저장소의 `data` 브랜치가 검증된 스냅샷 저장소 역할을 합니다.[5] [6]

```text
Alpha Vantage API
    ↓  주간 조정종가 수집
RRG proxy 계산
    ↓  발행 전 품질 게이트
GitHub data 브랜치
    ├── latest.json
    ├── index.json
    └── snapshots/<주차>/rrg.json · summary.csv · manifest.json
    ↓  정적 웹 빌드
GitHub Pages 공개 RRG Atlas
```

발행 전에는 기대 시계열 수, 최소 이력, 중복 주차, 양수 가격, 모든 섹터의 기준일 정렬을 확인합니다. 하나라도 실패하면 새 스냅샷을 발행하지 않으며, 공개 화면은 이전의 정상 검증본을 유지합니다. 배포 후에는 공개 `latest.json`의 스냅샷 ID가 이번에 발행한 ID와 일치하는지도 확인합니다.[5] [6]

## 권장 활용 순서

RRG는 신호를 자동으로 확정하는 도구가 아니라, 상대 분석의 우선순위를 정리하는 도구입니다. 아래 순서로 보면 해석의 일관성을 높일 수 있습니다.

| 순서 | 확인할 내용 | 목적 |
|---:|---|---|
| 1 | 상단의 기준일·데이터 검증 상태 | 오래되었거나 검증되지 않은 데이터인지 먼저 확인 |
| 2 | 이번 주 핵심 신호 | 사분면 전환·100선 접근·강한 이동 후보 파악 |
| 3 | 8주 지도에서 최신 위치와 화살촉 | 현재 사분면과 최근 방향을 빠르게 비교 |
| 4 | 4주·12주로 기간 전환 | 단기 움직임이 중기 흐름과 같은지 확인 |
| 5 | 선택 섹터 패널의 누적 변화 | 이동 거리와 Ratio·Momentum 변화량 비교 |
| 6 | 개별 가격·실적·거시 환경 등 추가 자료 | RRG 밖의 근거로 해석을 검증 |

## 해석 시 유의사항

RRG Atlas는 상대 성과를 시각화합니다. 동일 섹터가 특정 사분면에 있다고 해서 미래 수익을 보장하지 않으며, 사분면 전환·100선 통과·화살촉 방향도 자동 매매 신호가 아닙니다. 상대 모멘텀은 상대 성과 추세보다 먼저 변할 수 있지만, 모든 모멘텀 변화가 추세 반전으로 이어지는 것은 아닙니다.[1] [2]

특히 이 프로젝트는 주간 데이터와 자체 proxy 산식을 사용합니다. 일간 RRG, 다른 벤치마크, 다른 평활화 설정, 공식 JdK 구현과는 다른 결론이 나올 수 있습니다. 따라서 투자 판단에는 개별 가격 차트, 거래량, 펀더멘털, 거시 환경, 위험 관리 기준 등 독립적인 자료를 함께 검토해야 합니다.

## 로컬 실행

```bash
python -m pip install -e ".[dev]"
pytest -q
cd web && npm install && npm run dev
```

실제 스냅샷 실행에는 `ALPHAVANTAGE_API_KEY` 환경 변수가 필요합니다. 정기 발행, 수동 재실행, 데이터 지연 및 배포 실패 대응은 [운영 가이드](OPERATIONS.md)를 참고하세요.

## 참고 자료

[1]: https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/relative-rotation-graphs-rrg-charts "StockCharts ChartSchool — Relative Rotation Graphs"
[2]: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rrg-relative-strength "StockCharts ChartSchool — RRG Relative Strength"
[3]: ./METHODOLOGY.md "RRG Atlas 계산식·사분면·주차 앵커"
[4]: ./config/universe.us-sector-spdr.json "SPY 및 Select Sector SPDR 유니버스"
[5]: ./.github/workflows/weekly-snapshot.yml "주간 수집·검증·저장·Pages 배포 자동화"
[6]: ./pipeline/quality.py "발행 전 데이터 품질 게이트"
