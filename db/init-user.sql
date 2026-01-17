CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    phone_number VARCHAR(15),
    google_id VARCHAR(100),
    apple_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (username),
    UNIQUE (email),
    UNIQUE (phone_number),
    UNIQUE (google_id),
    UNIQUE (apple_id)
);

CREATE INDEX idx_email ON users (email);
CREATE INDEX idx_phone_number ON users (phone_number);
CREATE INDEX idx_google_id ON users (google_id);
CREATE INDEX idx_apple_id ON users (apple_id);