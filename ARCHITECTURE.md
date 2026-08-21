# Architecture

`main` 브랜치는 계산 파이프라인, 테스트, React 정적 웹, 문서를 보관합니다. `data` 브랜치는 검증을 통과한 결과만 append-only로 보관합니다.

주간 워크플로는 12개 심볼을 수집한 뒤 동일한 마지막 완결 주차, 최소 52주 이력, 양수 조정종가를 검증합니다. 이 통과 뒤 최근 104주를 전체 재계산하고, `rrg.json`, `summary.csv`, `manifest.json`을 주차 폴더로 발행합니다. 같은 커밋에서 `latest.json`을 갱신한 뒤 해당 파일을 포함한 정적 웹을 Pages에 배포합니다.

브라우저는 시장 데이터 공급자를 직접 호출하지 않고 `./data/latest.json`만 읽습니다. 새 snapshot 계산이나 data branch push가 실패하면 Pages 배포 단계에 도달하지 않으므로 이전 정상 화면이 유지됩니다.

