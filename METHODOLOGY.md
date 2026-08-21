# Methodology

```text
relative_price[t] = sector_adjusted_close[t] / SPY_adjusted_close[t]
ratio[t] = 100 × relative_price[t] / EMA(relative_price, 13)[t]
momentum[t] = 100 × ratio[t] / ratio[t - 4]
```

Ratio와 Momentum이 모두 100 이상이면 Leading, Ratio만 100 이상이면 Weakening, 둘 다 100 미만이면 Lagging, Momentum만 100 이상이면 Improving으로 분류합니다. 각 snapshot은 최신 관측점과 직전 12개 관측점으로 구성된 12주 꼬리를 제공합니다.

