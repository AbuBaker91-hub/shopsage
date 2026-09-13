CREATE TABLE IF NOT EXISTS products (
    id              bigserial PRIMARY KEY,
    handle          text NOT NULL UNIQUE,
    title           text NOT NULL,
    description     text NOT NULL DEFAULT '',
    category        text NOT NULL DEFAULT '',
    tags_json       jsonb NOT NULL DEFAULT '[]',
    price_cents     integer NOT NULL,
    stock           integer NOT NULL DEFAULT 0,
    attributes_json jsonb NOT NULL DEFAULT '{}',
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chats (
    id             bigserial PRIMARY KEY,
    session_id     text NOT NULL,
    question       text NOT NULL,
    reply_json     jsonb NOT NULL DEFAULT '{}',
    prompt_version text NOT NULL DEFAULT '',
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chats_session_idx ON chats (session_id);
