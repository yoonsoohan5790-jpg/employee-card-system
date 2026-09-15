# 사원증 자동 발급 및 출입권한 관리 시스템

Python Flask 기반 MVP. 조직원의 부서/직급에 따라 출입권한을 자동 부여하고,
퇴사·휴직 발생 시 사원증을 자동 중지하고 출입권한을 자동 회수한다.

## 로컬 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed.py        # 초기 데이터 생성 (관리자 + 조직원 5명)
python app.py          # http://localhost:5000
```

- 관리자 계정: `admin` / `admin123`
- 조직원 계정 예시: `hong` / `pass1234` (경영지원팀 사원, 재직)
  - `kim` / `pass1234` (IT팀 사원, 재직)
  - `lee` / `pass1234` (정보보호팀 대리, 재직)
  - `park` / `pass1234` (영업팀 과장, 휴직 → 사원증 중지 상태)
  - `choi` / `pass1234` (개발팀 사원, 퇴사 → 사원증 중지 상태)

## 환경 변수

`.env.example`을 참고해 `.env`를 생성한다.

| 변수 | 설명 |
|---|---|
| `SECRET_KEY` | Flask 세션 서명 키 |
| `DATABASE_URL` | 비우면 SQLite, 값이 있으면 Supabase(Postgres) 등 외부 DB 사용 |
| `AUTO_REACTIVATE_ON_LEAVE_END` | 휴직 종료일 도래 시 자동 재활성화 여부 |
| `ENABLE_BACKGROUND_SCHEDULER` | 로컬 실행 시 5분 주기 자동 점검 스케줄러 사용 여부 |

## 배포 (Vercel + Supabase)

`api/index.py`, `vercel.json`으로 Vercel Python 서버리스 배포를 지원한다.
Supabase 프로젝트를 만들고 `DATABASE_URL`을 Vercel 환경변수로 등록하면
동일한 코드가 로컬 SQLite 대신 Supabase Postgres를 사용한다.

서버리스 환경은 상시 프로세스가 없으므로 APScheduler 백그라운드 스레드가 동작하지 않는다.
대신 관리자 대시보드(`/api/dashboard/summary`) 호출 시점마다
휴직 종료일 자동 점검(`employment_service.check_leave_end_dates`)이 인라인으로 실행된다.

## 주요 자동화 로직

- 조직원 등록(재직) → 사원증 자동 발급 → 부서/직급 정책에 따른 출입권한 자동 부여
- 부서/직급 변경 → 기존 권한 전체 회수 후 새 정책 재적용
- 재직 → 휴직/퇴사 → 사원증 자동 중지 + 출입권한 전체 회수
- 휴직 → 재직(휴직 종료) → 사원증 자동 활성화 + 정책 재적용
- 모든 변경은 `audit_logs`에 기록되며, 시스템이 자동 처리한 경우 변경자는 `SYSTEM`으로 기록
