-- SQL Explorer 개발용 시드 스키마 (orders/stores/refunds)
-- 이 파일은 앱이 실행하지 않습니다. 로컬 read-only PG에 수동으로 적재하세요.
-- 사용법: psql -U <user> -d <dbname> -f seed.sql
--
-- 설계 의도:
--   - 탐색 필요성 있는 quirk 포함: 대문자 status enum, is_refunded bool,
--     amount numeric, order_date, 컬럼 COMMENT
--   - 스키마-agnostic 설계: 이 시드는 예시일 뿐, 실제 DB와 무관하게 동작

-- ── 기존 테이블 제거 (재실행 가능) ──
DROP TABLE IF EXISTS refunds CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS stores CASCADE;

-- ── stores ──
CREATE TABLE stores (
    store_id   SERIAL PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL,
    region     VARCHAR(50),
    opened_at  DATE
);

COMMENT ON TABLE stores IS '매장 정보';
COMMENT ON COLUMN stores.region IS '매장이 위치한 지역 (예: 서울, 부산)';

-- ── orders ──
CREATE TABLE orders (
    order_id    SERIAL PRIMARY KEY,
    store_id    INTEGER NOT NULL REFERENCES stores(store_id),
    order_date  TIMESTAMP NOT NULL DEFAULT now(),
    amount      NUMERIC(12, 2) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
    is_refunded BOOLEAN NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE orders IS '주문 내역';
COMMENT ON COLUMN orders.status IS '주문 상태: COMPLETED | CANCELLED | PENDING (대문자)';
COMMENT ON COLUMN orders.is_refunded IS '환불 여부 (true이면 refunds 테이블에 레코드 존재)';
COMMENT ON COLUMN orders.amount IS '주문 금액 (원화, VAT 포함)';

-- ── refunds ──
CREATE TABLE refunds (
    refund_id   SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(order_id),
    refund_date TIMESTAMP NOT NULL DEFAULT now(),
    amount      NUMERIC(12, 2) NOT NULL,
    reason      VARCHAR(200)
);

COMMENT ON TABLE refunds IS '환불 내역';

-- ── 샘플 데이터 ──
INSERT INTO stores (store_name, region, opened_at) VALUES
    ('강남점',   '서울', '2020-03-01'),
    ('홍대점',   '서울', '2021-06-15'),
    ('해운대점', '부산', '2022-01-10'),
    ('서면점',   '부산', '2019-11-20');

-- orders: 2024-03~2024-05 데이터 (지난달 테스트용)
INSERT INTO orders (store_id, order_date, amount, status, is_refunded) VALUES
    (1, '2024-04-03 10:00:00', 35000,  'COMPLETED', FALSE),
    (1, '2024-04-07 14:30:00', 12000,  'COMPLETED', TRUE),
    (1, '2024-04-15 09:00:00', 78000,  'CANCELLED', FALSE),
    (2, '2024-04-02 11:00:00', 22500,  'COMPLETED', FALSE),
    (2, '2024-04-20 16:00:00', 45000,  'COMPLETED', TRUE),
    (3, '2024-04-05 13:00:00', 60000,  'COMPLETED', FALSE),
    (3, '2024-04-18 10:30:00', 31000,  'COMPLETED', FALSE),
    (4, '2024-04-10 08:00:00', 19000,  'COMPLETED', FALSE),
    (4, '2024-04-25 17:00:00', 88000,  'COMPLETED', TRUE),
    (1, '2024-03-15 12:00:00', 50000,  'COMPLETED', FALSE),
    (2, '2024-05-01 09:00:00', 27000,  'COMPLETED', FALSE);

INSERT INTO refunds (order_id, refund_date, amount, reason) VALUES
    (2, '2024-04-08 11:00:00', 12000, '단순 변심'),
    (5, '2024-04-21 10:00:00', 45000, '상품 불량'),
    (9, '2024-04-26 09:30:00', 88000, '오배송');
