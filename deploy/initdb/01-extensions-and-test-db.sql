-- Runs once, when the pgdata volume is created.
-- pg_trgm is also created by the first migration; here it makes it available in template1 for qb_test.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
\connect template1
CREATE EXTENSION IF NOT EXISTS pg_trgm;
\connect qb
CREATE DATABASE qb_test OWNER qb;
