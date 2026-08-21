# Methodology

```text
relative_price[t] = sector_adjusted_close[t] / SPY_adjusted_close[t]
ratio[t] = 100 × relative_price[t] / EMA(relative_price, 13)[t]
momentum[t] = 100 × ratio[t] / ratio[t - 4]
```

Ratio와 Momentum이 모두 100 이상이면 Leading, Ratio만 100 이상이면 Weakening, 둘 다 100 미만이면 Lagging, Momentum만 100 이상이면 Improving으로 분류합니다. 각 snapshot은 최신 관측점과 직전 12개 관측점으로 구성된 12주 꼬리를 제공합니다.

주간 관측점은 미국 동부시간 기준으로 **정규 장이 마감된 가장 최근 금요일**에 앵커를 둡니다. 금요일이 휴장일이면 그 주의 마지막 거래일 종가를 사용하되, 관측 날짜는 해당 금요일로 정규화합니다. 금요일 장 마감 전 실행된 작업은 진행 중인 주를 제외하고 직전 금요일을 사용합니다.
