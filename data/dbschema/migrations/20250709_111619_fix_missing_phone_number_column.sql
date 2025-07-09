-- Missing phone_number column fix
-- Applied: Wed Jul  9 11:16:19 CDT 2025
-- Issue: SQLAlchemy expected phone_number column in users table
-- Resolution: Added missing column and index to staging database

ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);
CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users (phone_number) WHERE phone_number IS NOT NULL;
