-- LocalCloud database schema (PostgreSQL)

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users
CREATE TABLE users (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email      TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL,
    role       TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Filesystem nodes
CREATE TABLE filesystem_nodes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id  UUID REFERENCES filesystem_nodes(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    node_type  TEXT NOT NULL CHECK (node_type IN ('file', 'folder')),
    path       TEXT NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (owner_id, parent_id, name) WHERE NOT is_deleted
);

-- Useful views
CREATE VIEW active_nodes AS
    SELECT * FROM filesystem_nodes WHERE NOT is_deleted;

-- Storage usage per user
SELECT
    u.email,
    COUNT(fn.id)            AS file_count,
    SUM(f.size_bytes)       AS total_bytes,
    SUM(f.size_bytes) / (1024 * 1024 * 1024.0) AS total_gb
FROM users u
JOIN filesystem_nodes fn ON fn.owner_id = u.id AND NOT fn.is_deleted
JOIN files f ON f.node_id = fn.id
GROUP BY u.id, u.email
ORDER BY total_bytes DESC;
