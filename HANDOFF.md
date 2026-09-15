# 프로젝트 인계 문서 (Handoff)

> 다른 AI 에이전트 세션에서 이 프로젝트 작업을 이어가기 위한 문서.
> 이 파일 하나를 새 세션에 붙여넣거나 첨부하면 지금까지의 맥락을 그대로 이어받을 수 있다.

## 1. 프로젝트 개요

**사원증 자동 발급 및 출입권한 관리 시스템** — 조직원의 인사상태(재직/휴직/퇴사)와
부서/직급에 따라 사원증을 자동 발급하고 출입권한을 자동으로 부여/회수하는 웹 시스템.

- 로컬 경로: `C:\workspace_claude\project\법인숙소 관리\employee_card_system`
- 스택: Python Flask + SQLAlchemy, Jinja2, Vanilla JS, Chart.js
- DB: 로컬은 SQLite(`database.db`), 배포 환경은 Supabase Postgres
- 원본 요구사항: 이 폴더의 대화 초반에 사용자가 제공한 전체 스펙 문서 참고 (조직원 관리 /
  사원증 자동 발급 / 부서·직급별 출입권한 / 인사상태 자동화 / 관리자 대시보드 / 변경 이력 등)

## 2. 배포 현황

| 항목 | 값 |
|---|---|
| GitHub | https://github.com/yoonsoohan5790-jpg/employee-card-system (main 브랜치, push 시 Vercel 자동 배포) |
| Vercel 프로덕션 URL | https://employee-card-system.vercel.app |
| Vercel 프로젝트 | team "soohan" 하위 "employee-card-system" |
| Supabase 프로젝트 | `20260915_ETNS_S` (project ref: `sgxzdafpfzirwdlcwiap`, 리전 ap-northeast-1 Tokyo) |
| Supabase 연결 방식 | Transaction Pooler (포트 6543), SQLAlchemy + psycopg3 |

⚠️ **주의**: Supabase 계정에는 `20260915_ETNS_G`/`20260915_ETNS_V`/`20260915_ETNS_S` 라는
날짜+ETNS+G(GitHub)/S(Supabase)/V(Vercel) 네이밍의 **다른(투두리스트) 앱** 리소스도 존재한다.
이번 사원증 앱은 위 표의 리소스를 그대로 쓰고 있지만, 혼동하지 않도록 주의.

### 로그인 계정 (로컬/프로덕션 공통 시드 데이터)

- 관리자: `admin` / `admin123`
- 조직원 예시: `hong`/`pass1234`(재직), `kim`/`pass1234`(재직), `lee`/`pass1234`(재직),
  `park`/`pass1234`(휴직→중지 확인용), `choi`/`pass1234`(퇴사→중지 확인용)
- 프로덕션에는 위 6명 + 대량 테스트 데이터 `emp0007`~`emp0806` (총 806명, 비밀번호 `test1234`)이
  들어있음 (`generate_bulk_test_data.py`로 생성)

## 3. 핵심 아키텍처 / 폴더 구조

```
employee_card_system/
├── app.py                 # Flask 앱 팩토리, 블루프린트 등록, 로컬 APScheduler
├── config.py               # .env 로드, DB/메일 설정
├── extensions.py           # db = SQLAlchemy()
├── seed.py                 # 초기 데모 데이터 (admin + 5명), seed_data()는 원격 트리거용으로도 사용
├── generate_bulk_test_data.py  # 대량 테스트 데이터 생성 (batch insert 최적화됨)
├── vercel.json / api/index.py  # Vercel 서버리스 배포 설정
├── models/
│   ├── user.py, card.py, access_area.py, access_policy.py
│   ├── user_access.py      # reason, expires_at 컬럼 포함 (출입권한 예외처리용)
│   ├── audit_log.py
│   └── card_application.py # 사원증 신청서 (일반 사용자용)
├── services/
│   ├── card_service.py, access_service.py, employment_service.py
│   ├── mail_sender.py      # Gmail SMTP 발송 (260915_mailsender 스킬 기반)
│   ├── alert_mail_service.py       # 권한 이상 알림 메일
│   ├── application_service.py      # 신청 승인/반려 로직
│   ├── application_mail_service.py # 신청 검토 알림 메일
│   └── link_token.py       # 이메일 1회성 조치 링크용 HMAC 서명 토큰
├── routes/
│   ├── auth.py, users.py, cards.py, access.py, dashboard.py, audit.py, pages.py
│   ├── admin_seed.py        # POST /api/seed-once, /api/seed-bulk (보호된 원격 시딩용)
│   ├── alerts.py            # 권한이상 알림 발송 + /cards/suspend-via-link
│   └── applications.py      # GET /apply, /api/card-applications 관련
├── templates/, static/
└── supabase/migration_002_access_exceptions.sql  # 수동 스키마 마이그레이션 SQL
```

## 4. 지금까지 구현된 기능

1. **기본 스펙 전체** (요구사항서 기준): 조직원 CRUD, 사원증 자동 발급/재발급/중지/폐기,
   부서+직급 기반 출입권한 자동 부여, 부서/직급 변경 시 권한 재계산, 퇴사/휴직 자동 중지,
   휴직 종료 자동 재활성화, 관리자 대시보드(Chart.js, 5초 자동 갱신), 변경 이력(audit_logs)
2. **검색 기능**: 조직원 관리 / 출입권한 관리 화면에 이름·아이디·이메일 검색
3. **출입권한 예외처리**: 관리자가 개별 직원에게 정책과 다른 권한을 **사유 + 적용기간(종료일)**
   과 함께 부여, 기간 만료 시 자동으로 정책값 복귀, "예외처리 목록"에서 조회
4. **권한 이상 알림 메일**: 대시보드의 "권한 이상 알림" 항목에서 "메일 발송" 클릭 →
   확인 후 관리자에게 메일 발송, 메일 안에 **1회성 사원증 즉시중지 링크** 포함
   (클릭 시 확인 페이지를 한 번 더 거침 — 메일 보안 스캐너 오작동 방지)
5. **일반 사용자 사원증 신청** (`/apply`, 로그인 불필요): 이름/사번/부서/직책/기타사항 입력
   - 기타사항 없음 → 즉시 자동 승인 (계정 생성 + 사원증 발급, 초기 비밀번호 `changeme123`)
   - 기타사항 있음 → "검토 대기", 관리자에게 알림 메일 발송, 관리자가 승인/반려
6. **성능 개선**: 806명 규모에서 사용자당 반복 쿼리(N+1)로 인한 지연 문제를
   일괄 조회(`access_service.get_access_status_bulk`)로 해결 (3~5배 개선)
7. **대량 테스트 데이터 생성**: `generate_bulk_test_data.py` — 정책/구역을 한 번만 조회하고
   User/Card/UserAccess/AuditLog를 일괄 insert (원격 DB에서도 800명이 몇 초 내 처리됨)

## 5. 반드시 알아야 할 기술적 함정 (재발 방지)

1. **Supabase Transaction Pooler + psycopg3**: `prepare_threshold=None`을
   `SQLALCHEMY_ENGINE_OPTIONS.connect_args`에 넣지 않으면 `DuplicatePreparedStatement` 에러 발생.
   (`config.py`에 이미 적용됨)
2. **순환 import**: `seed.py`가 모듈 최상단에서 `app.py`를 import하면, `routes/admin_seed.py`가
   `seed.py`를 import하는 구조와 맞물려 `python app.py` 직접 실행 시 순환 참조 에러 발생.
   `seed.py`의 `run()` 함수 안에서만 지연 import하도록 되어 있음 — 이 패턴 유지할 것.
3. **N+1 쿼리**: 사용자 목록을 순회하며 `access_service.get_user_access_status(u)`를
   한 명씩 호출하면 안 됨. 여러 명을 다룰 때는 항상 `get_access_status_bulk(users)` 사용.
4. **Vercel 서버리스 실행시간 제한**: 사용자 1명당 여러 DB 왕복이 발생하는 로직(예: 개별
   `card_service.issue_card()` 반복 호출)은 800명 같은 대량 처리 시 타임아웃 남. 대량 처리는
   반드시 배치 insert로 작성.
5. **스키마 변경 시 마이그레이션 도구 없음**: Flask-Migrate/Alembic 미사용. 새 컬럼을 추가하면
   로컬 SQLite는 직접 `ALTER TABLE` 실행, Supabase는 SQL Editor에서 동일하게 실행해야 함
   (`supabase/migration_*.sql`에 기록해두는 관례 유지). **완전히 새로운 테이블**은
   `db.create_all()`이 앱 기동 시 자동 생성하므로 별도 작업 불필요 (`card_applications`가 그 예).
6. **보호된 원격 엔드포인트**: `/api/seed-once`, `/api/seed-bulk`는 `X-Seed-Key` 헤더 값이
   `SECRET_KEY`와 일치해야 동작. SECRET_KEY 값은 Vercel 환경변수에 있음(코드/이 문서에는 없음).

## 6. 자격증명 — 실제 값은 여기 없음, 저장 위치만 기록

| 항목 | 로컬 | 프로덕션(Vercel) |
|---|---|---|
| `SECRET_KEY` | `.env` (Flask 세션 서명 + 원격 시딩 X-Seed-Key로도 사용) | Vercel 환경변수에 설정됨 |
| `DATABASE_URL` | 없음(SQLite 기본값 사용) | Vercel 환경변수에 설정됨 (Supabase Transaction Pooler) |
| `MAIL_SENDER_EMAIL` | `.env`에 설정됨 (`yoonsoohan5790@gmail.com`) | **미설정** — 아직 Vercel에 없음 |
| `MAIL_SENDER_APP_PASSWORD` | `.env`에 설정됨 (Gmail 앱 비밀번호) | **미설정** |
| `MAIL_ALERT_RECIPIENT` | `.env`에 설정됨 (발신자와 동일) | **미설정** |

⚠️ **보안 메모**: Gmail 앱 비밀번호가 이전 대화 중 채팅창에 평문으로 노출된 적이 있음.
[Google 계정 앱 비밀번호 페이지](https://myaccount.google.com/apppasswords)에서 재발급 권장.
실제 비밀번호 값은 브라우저 폼(Vercel 등)에 Claude가 직접 입력하지 않고, 사용자가 직접
붙여넣도록 안내하는 방식으로 진행해왔음 — 이 관례를 유지할 것.

## 7. 만들어둔 개인 스킬

- `260915_mailsender` (위치: `C:\Users\etners\.claude\skills\260915_mailsender\`)
  Gmail SMTP 발송 재사용 스킬. `scripts/send_email.py`를 프로젝트로 복사해 사용하는 방식.
  이 프로젝트에서는 `services/mail_sender.py`로 이식되어 있음.
  **발송 전 항상 사용자 확인**을 받는다는 규칙이 SKILL.md에 명시되어 있음.

## 8. 미완료 / 다음에 할 일

1. **Vercel에 메일 환경변수 미등록** — `MAIL_SENDER_EMAIL`, `MAIL_SENDER_APP_PASSWORD`,
   `MAIL_ALERT_RECIPIENT`를 Vercel 프로젝트 환경변수에 등록해야 프로덕션에서 권한이상 알림
   메일 / 신청 검토 알림 메일이 실제로 발송됨. (등록 안 해도 앱 자체는 정상 동작, 메일만 조용히 스킵됨)
2. Gmail 앱 비밀번호 재발급 권장 (위 보안 메모 참고)
3. 자동화된 테스트 스위트 없음 — 지금까지 전부 브라우저/curl 수동 검증으로 진행함
4. DB 마이그레이션 도구 부재 — 스키마 변경 시 로컬+Supabase 양쪽에 수동 반영 필요

## 9. 작업 스타일/합의된 규칙 (이 세션에서 확립된 것)

- 실제 비밀번호/DB 접속정보 등 민감한 값은 Claude가 대신 웹 폼에 입력하지 않고, 사용자가
  직접 붙여넣도록 안내한다 (Vercel 환경변수 등록 시 실제로 이렇게 진행함).
- 배포(GitHub push)는 매번 사용자에게 확인 후 진행한다 (Vercel 자동배포와 직결되므로).
- 테스트로 실제 DB에 넣은 임시 데이터는 검증 후 정리(cleanup)한다.
- 새 기능 추가 시 로컬에서 먼저 API/브라우저로 실제 동작을 검증한 뒤 배포한다.
