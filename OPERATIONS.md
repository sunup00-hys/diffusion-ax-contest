# DIFFUSION AX Contest 운영/배포 절차

이 저장소는 기존 운영 주소와 Supabase 데이터를 유지하면서 안전하게 변경하기 위한 절차를 사용합니다.

## 환경
- production: 기존 `agents`, `scores`, `app_settings`
- staging: `stg_agents`, `stg_scores`, `stg_app_settings`
- `AX_ENV=staging`일 때 앱은 staging 테이블만 사용합니다.
- 기본값은 production입니다.

## 변경 절차
1. 운영 DB 백업
2. staging DB를 운영 데이터로 동기화
3. `automation-staging` 브랜치에서 코드 수정
4. Railway staging 배포
5. 문법/기동/DB 읽기·쓰기/집계 검증
6. `ax_ops.update_history`에 검증 결과 기록
7. 사용자 승인
8. 승인 후 main 반영 및 운영 배포
9. 운영 검증 후 이력 상태를 deployed로 변경

## 원칙
- 사용자 승인 전 main 및 운영 데이터에 기능 변경을 적용하지 않습니다.
- DB DDL은 Supabase migration으로 기록합니다.
- 가족게임과 별도의 Railway 프로젝트 및 Supabase 프로젝트를 사용합니다.
- 비밀키는 GitHub 코드에 저장하지 않습니다.
