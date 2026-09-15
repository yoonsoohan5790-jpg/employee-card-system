-- 출입권한 예외처리(수동 부여) 기능 지원을 위한 스키마 변경
-- Supabase SQL Editor에서 실행할 것. 기존 데이터는 건드리지 않는 추가(ADD COLUMN)만 수행한다.

ALTER TABLE user_access ADD COLUMN IF NOT EXISTS reason VARCHAR(200);
ALTER TABLE user_access ADD COLUMN IF NOT EXISTS expires_at DATE;
