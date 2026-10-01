CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    client_ref VARCHAR(100),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    risk_profile VARCHAR(20),
    date_joined DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_clients_email_lower
    ON clients (LOWER(email));

CREATE TABLE IF NOT EXISTS client_messages (
    id SERIAL PRIMARY KEY,
    client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    urgency VARCHAR(20) NOT NULL,
    requires_human BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'NEW',
    source VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
    external_message_id VARCHAR(255)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_client_messages_external_id
    ON client_messages (external_message_id)
    WHERE external_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_client_messages_client_id
    ON client_messages (client_id);

CREATE INDEX IF NOT EXISTS idx_client_messages_status
    ON client_messages (status);

CREATE INDEX IF NOT EXISTS idx_client_messages_created_at
    ON client_messages (created_at DESC);

CREATE TABLE IF NOT EXISTS client_email_aliases (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_client_email_aliases_email_lower
    ON client_email_aliases (LOWER(email));

CREATE INDEX IF NOT EXISTS idx_client_email_aliases_client_id
    ON client_email_aliases (client_id);
