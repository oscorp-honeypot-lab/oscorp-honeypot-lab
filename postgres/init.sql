CREATE TABLE IF NOT EXISTS eventos (
    id SERIAL PRIMARY KEY,
    event_hash TEXT UNIQUE,
    event_uuid TEXT,
    timestamp_evento TIMESTAMPTZ,
    eventid TEXT,
    session_id TEXT,
    sensor TEXT,
    src_ip TEXT,
    src_port INTEGER,
    username TEXT,
    password TEXT,
    command_input TEXT,
    url TEXT,
    shasum TEXT,
    raw_event JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE eventos
ADD COLUMN IF NOT EXISTS event_hash TEXT;

ALTER TABLE eventos
ADD COLUMN IF NOT EXISTS event_uuid TEXT;

ALTER TABLE eventos
DROP CONSTRAINT IF EXISTS eventos_event_uuid_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_eventos_event_hash
ON eventos(event_hash);

CREATE INDEX IF NOT EXISTS idx_eventos_event_uuid
ON eventos(event_uuid);

CREATE INDEX IF NOT EXISTS idx_eventos_eventid 
ON eventos(eventid);

CREATE INDEX IF NOT EXISTS idx_eventos_session_id 
ON eventos(session_id);

CREATE INDEX IF NOT EXISTS idx_eventos_src_ip 
ON eventos(src_ip);

CREATE INDEX IF NOT EXISTS idx_eventos_timestamp 
ON eventos(timestamp_evento);


CREATE TABLE IF NOT EXISTS pipeline_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    events_read INTEGER DEFAULT 0,
    events_inserted INTEGER DEFAULT 0,
    events_indexed INTEGER DEFAULT 0,
    alerts_sent INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status TEXT
);


CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    event_uuid TEXT,
    session_id TEXT,
    event_timestamp TIMESTAMP,
    processed_timestamp TIMESTAMP,
    alert_sent_timestamp TIMESTAMP DEFAULT NOW(),
    mttd_seconds NUMERIC,
    alert_type TEXT,
    alert_status TEXT,
    raw_alert JSONB
);
