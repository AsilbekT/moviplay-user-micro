BEGIN;

-- shared updated_at trigger function
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- users (account identity)
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,

  email VARCHAR(255) UNIQUE,
  phone_number VARCHAR(15) UNIQUE,
  google_id VARCHAR(100) UNIQUE,
  apple_id VARCHAR(100) UNIQUE,

  name VARCHAR(100),
  username VARCHAR(50) UNIQUE,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT users_require_identifier
  CHECK (
    email IS NOT NULL OR
    phone_number IS NOT NULL OR
    google_id IS NOT NULL OR
    apple_id IS NOT NULL OR
    username IS NOT NULL
  )
);

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users (phone_number);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users (google_id);
CREATE INDEX IF NOT EXISTS idx_users_apple_id ON users (apple_id);

-- profiles (one user -> many profiles)
CREATE TABLE IF NOT EXISTS profiles (
  id SERIAL PRIMARY KEY,

  user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

  name VARCHAR(50) NOT NULL,
  is_kids BOOLEAN NOT NULL DEFAULT false,
  avatar VARCHAR(50) DEFAULT '',
  language VARCHAR(10) DEFAULT 'uz',
  maturity_level VARCHAR(20) DEFAULT 'all',

  preferences JSONB NOT NULL DEFAULT '[]'::jsonb,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- prevents duplicate profile names within the same user
  UNIQUE (user_id, name)
);

DROP TRIGGER IF EXISTS trg_profiles_updated_at ON profiles;
CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON profiles
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles (user_id);
CREATE INDEX IF NOT EXISTS idx_profiles_is_kids ON profiles (is_kids);

COMMIT;
