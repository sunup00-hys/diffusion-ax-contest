
# DIFFUSION AX 경진대회 — 공용 DB 실시간 채점판

## 완성 기능
- 심사위원 9명이 각자 휴대폰에서 동일 URL 접속
- 8개 팀: 1배
- DIFF_CHAMPION: 3배
- MASTER / 2006: 관리자
- 5개 Agent × 5개 항목 × 1~5점
- 같은 심사위원이 같은 Agent를 재제출하면 기존 값을 수정(upsert)
- Supabase 공용 DB에 즉시 저장
- MASTER 결과 화면 3초 자동 갱신
- 항목별 가중 합계 + 최종 점수(최대 275점)
- 최종점수 내림차순 자동 정렬
- 최우수 1 / 우수 2 / 장려 2 표시
- 심사위원별 제출 현황
- 전체 진행률 45건 기준 표시
- MASTER가 Agent 이름 5개를 앱에서 직접 수정
- 테스트 점수 전체 초기화
- CSV 다운로드

## 계정
DRAM_ALD / 2026
DRAM_FUR / 2026
DRAM_IMP / 2026
NAND_ALD / 2026
NAND_FUR / 2026
NAND_IMP / 2026
M15X_DIFF / 2026
DIFF_STRAT / 2026
DIFF_CHAMPION / 2026  (3배)
MASTER / 2006

## 1. Supabase DB 만들기
1) https://supabase.com 에서 프로젝트 생성
2) SQL Editor 열기
3) `schema.sql` 전체 붙여넣고 Run
4) Project Settings > API에서 아래 2개 확인
   - Project URL
   - service_role key
※ service_role key는 외부에 공개하면 안 됩니다.

## 2. 로컬 테스트
1) Python 설치
2) 터미널에서:
   pip install -r requirements.txt
3) `.streamlit/secrets.toml.example` 을 `.streamlit/secrets.toml` 로 복사
4) SUPABASE_URL / SUPABASE_KEY 입력
5) 실행:
   streamlit run app.py
6) 같은 네트워크라면 PC 주소로 휴대폰 테스트 가능

## 3. 실제 휴대폰용 공개 주소 만들기 — Streamlit Community Cloud
1) GitHub에 이 폴더의 파일 업로드
   - app.py
   - requirements.txt
   - schema.sql
   - .gitignore
   ※ 실제 `.streamlit/secrets.toml` 은 절대 GitHub에 올리지 마세요.
2) https://share.streamlit.io 에서 GitHub 저장소 선택
3) Main file: app.py
4) Advanced settings > Secrets에 아래 입력
   SUPABASE_URL="..."
   SUPABASE_KEY="..."
5) Deploy
6) 발급된 https://xxxxx.streamlit.app 주소를 심사위원에게 공유
7) QR 코드로 만들어 행사장 화면에 띄우면 편리합니다.

## 데이터 보안
이 앱은 DB 접속 키를 Streamlit 서버의 Secrets에만 저장합니다.
브라우저에는 Supabase service_role key를 직접 전달하지 않습니다.
DB 테이블은 RLS를 활성화하고 공개 정책을 만들지 않는 방식입니다.

## 점수 계산
심사위원 가중치 합 = 8×1 + 1×3 = 11
개인 최대 = 25점
Agent 최종 최대 = 25×11 = 275점
항목별 최대 = 5×11 = 55점
