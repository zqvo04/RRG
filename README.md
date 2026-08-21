# RRG Sector Atlas

SPY 대비 미국 Select Sector SPDR 11개의 주간 상대강도 회전을 보여 주는 반응형 RRG-style 스냅샷 웹입니다. 공식 JdK 지표를 복제한다고 주장하지 않으며 공개 상대가격 기반의 `rrg_proxy_v1` 산식을 사용합니다.

GitHub Actions가 주간 조정 데이터를 수집·검증·계산하고, 검증을 통과한 Ratio·Momentum·사분면·12주 꼬리를 `data` 브랜치에 저장합니다. 정적 웹은 이 검증 스냅샷만 읽습니다.

```bash
python -m pip install -e ".[dev]"
pytest
cd web && npm install && npm run dev
```

실제 스냅샷 실행에는 `ALPHAVANTAGE_API_KEY` 환경 변수가 필요합니다. 원본 가격 응답과 API 키는 Git이나 정적 배포물에 저장하지 않습니다.

