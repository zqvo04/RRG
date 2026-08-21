# Web

React와 SVG로 만든 정적 RRG 지도입니다. 개발 서버에서는 로컬 fixture가 표시됩니다. Pages 배포에서는 `web/public/data/latest.json`의 검증 스냅샷을 읽습니다.

```bash
npm install
npm run dev
```

## UI 원칙

데스크톱에서는 지도판과 우측 주석 레일을, 모바일에서는 상태 인장·지도·필터·선택 섹터 상세 흐름을 제공합니다. 차트는 계산하지 않으며, 선택·필터·꼬리 길이는 표시만 제어합니다.

