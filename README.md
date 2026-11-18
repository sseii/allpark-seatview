# 올팍 시트뷰 (All-Park SeatView)

2026 한국체육산업개발(주) 공공데이터 활용 경진대회 출품작.
올림픽공원 공연장 3D 좌석 시야, 공연일 주차 혼잡 예측, 배리어프리 동선을 안내하는 웹 서비스.

- 데모: https://sseii.github.io/allpark-seatview/  
- 마감: 2026-12-01(월) 18:00 / 팀 목표: 12-01 오전 제출

## 폴더 구조

| 폴더 | 내용 | 담당 |
|---|---|---|
| `web/` | 웹 서비스 (Vite + Three.js). main 에 push 되면 자동 배포 | 웹, 3D |
| `web/public/models/` | 웹용 3D 모델 (GLB, 50MB 이하) | 3D |
| `web/public/data/` | 분석 결과 JSON | 분석 |
| `analysis/` | 데이터 분석 노트북·코드 | 분석 |
| `scripts/` | 공공데이터 내려받기 스크립트 | 팀장 |
| `docs/` | 기획서, 회의록 | 팀장 |

## 브랜치 규칙

- `main` 은 배포용. 직접 push 하지 않고 Pull Request 로 합친다.
- 각자 작업 브랜치: `3d`, `analysis`, `web`, `docs`
- 작업 → commit → 자기 브랜치에 push → GitHub 에서 Pull Request → 한 명 이상 확인 후 merge

## 실행 방법 (web)

```
cd web
npm install
npm run dev
```
브라우저에서 표시되는 주소(http://localhost:5173/allpark-seatview/)로 접속.

## 절대 하지 말 것

- API 키를 코드·커밋·단톡에 올리지 않는다. 키는 `keys.json`(로컬, gitignore 처리)이나 GitHub Secrets 에만 둔다.
- 원천 CSV, DAE/SKP 원본 3D 파일을 커밋하지 않는다 (GitHub 파일 하나 100MB 제한).
