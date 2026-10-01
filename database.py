import psycopg
from psycopg.rows import dict_row

from config import get_secret


def get_connection():
    database_url = get_secret("DATABASE_URL")
    if database_url:
        return psycopg.connect(database_url)

    return psycopg.connect(
        host=get_secret("DB_HOST", "localhost"),
        port=int(get_secret("DB_PORT", "5432")),
        dbname=get_secret("DB_NAME", "financial_advisor_pa"),
        user=get_secret("DB_USER", "louwkie"),
        password=get_secret("DB_PASSWORD"),
    )


def database_healthcheck():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return cur.fetchone()[0] == 1
    except Exception:
        return False


def save_client_message(
    message,
    result,
    client_id=None,
    source="MANUAL",
    external_message_id=None,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO client_messages (
                    client_id,
                    message,
                    category,
                    urgency,
                    requires_human,
                    reason,
                    recommended_action,
                    source,
                    external_message_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    client_id,
                    message,
                    result.category,
                    result.urgency,
                    result.requires_human,
                    result.reason,
                    result.recommended_action,
                    source,
                    external_message_id,
                ),
            )
    return True


def message_already_processed(external_message_id):
    if not external_message_id:
        return False

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM client_messages
                WHERE external_message_id = %s
                LIMIT 1;
                """,
                (external_message_id,),
            )
            return cur.fetchone() is not None


def get_client_by_email(email):
    if not email:
        return None

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    c.id,
                    c.name,
                    c.email
                FROM clients AS c
                WHERE LOWER(c.email) = LOWER(%s)
                   OR EXISTS (
                        SELECT 1
                        FROM client_email_aliases AS a
                        WHERE a.client_id = c.id
                          AND LOWER(a.email) = LOWER(%s)
                   )
                LIMIT 1;
                """,
                (email, email),
            )
            return cur.fetchone()


def create_client(name, email):
    name = name.strip()
    email = email.strip().lower()

    if not name or not email:
        return None

    if get_client_by_email(email):
        return None

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO clients (name, email)
                    VALUES (%s, %s)
                    RETURNING id, name, email;
                    """,
                    (name, email),
                )
                return cur.fetchone()
        except psycopg.IntegrityError:
            conn.rollback()
            return None


def get_clients():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    phone,
                    client_ref,
                    status,
                    risk_profile,
                    date_joined,
                    notes
                FROM clients
                ORDER BY name, email;
                """
            )
            return cur.fetchall()


def update_client(
    client_id,
    phone,
    client_ref,
    status,
    risk_profile,
    date_joined,
    notes,
):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                UPDATE clients
                SET
                    phone = %s,
                    client_ref = %s,
                    status = %s,
                    risk_profile = %s,
                    date_joined = %s,
                    notes = %s
                WHERE id = %s
                RETURNING id;
                """,
                (
                    phone,
                    client_ref,
                    status,
                    risk_profile,
                    date_joined,
                    notes,
                    client_id,
                ),
            )
            return cur.fetchone()


def get_messages_for_client(client_id):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    message,
                    category,
                    urgency,
                    requires_human,
                    reason,
                    recommended_action,
                    status,
                    source,
                    created_at
                FROM client_messages
                WHERE client_id = %s
                ORDER BY created_at DESC;
                """,
                (client_id,),
            )
            return cur.fetchall()


def get_client_messages():
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    cm.id,
                    cm.client_id,
                    c.name AS client_name,
                    c.email AS client_email,
                    cm.message,
                    cm.category,
                    cm.urgency,
                    cm.requires_human,
                    cm.reason,
                    cm.recommended_action,
                    cm.created_at,
                    cm.status,
                    cm.source,
                    cm.external_message_id
                FROM client_messages AS cm
                LEFT JOIN clients AS c
                    ON cm.client_id = c.id
                ORDER BY cm.created_at DESC;
                """
            )
            return cur.fetchall()


def update_message_status(message_id, new_status):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE client_messages
                SET status = %s
                WHERE id = %s;
                """,
                (new_status, message_id),
            )
    return True


def update_message_client(message_id, client_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE client_messages
                SET client_id = %s
                WHERE id = %s;
                """,
                (client_id, message_id),
            )
    return True


def get_client_aliases(client_id):
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    id,
                    client_id,
                    email,
                    created_at
                FROM client_email_aliases
                WHERE client_id = %s
                ORDER BY email ASC;
                """,
                (client_id,),
            )
            return cur.fetchall()


def add_client_alias(client_id, email):
    email = email.strip().lower()

    if not email:
        return {"status": "error", "message": "Please enter an email address."}

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, name, email
                    FROM clients
                    WHERE id = %s;
                    """,
                    (client_id,),
                )
                client = cur.fetchone()

                if not client:
                    return {"status": "error", "message": "Client not found."}

                primary_email = (client["email"] or "").strip().lower()
                if email == primary_email:
                    return {
                        "status": "exists",
                        "message": "That email is already the client's primary email.",
                    }

                cur.execute(
                    """
                    SELECT id, name
                    FROM clients
                    WHERE LOWER(email) = LOWER(%s);
                    """,
                    (email,),
                )
                primary_match = cur.fetchone()

                if primary_match:
                    return {
                        "status": "error",
                        "message": (
                            f"That email is already the primary email for "
                            f"{primary_match['name']}."
                        ),
                    }

                cur.execute(
                    """
                    SELECT a.id, a.client_id, c.name
                    FROM client_email_aliases AS a
                    JOIN clients AS c ON c.id = a.client_id
                    WHERE LOWER(a.email) = LOWER(%s);
                    """,
                    (email,),
                )
                existing_alias = cur.fetchone()

                if existing_alias:
                    if existing_alias["client_id"] == client_id:
                        return {
                            "status": "exists",
                            "message": "That alternate email already belongs to this client.",
                        }
                    return {
                        "status": "error",
                        "message": (
                            f"That email is already linked to "
                            f"{existing_alias['name']}."
                        ),
                    }

                cur.execute(
                    """
                    INSERT INTO client_email_aliases (client_id, email)
                    VALUES (%s, %s)
                    RETURNING id;
                    """,
                    (client_id, email),
                )
                alias_id = cur.fetchone()["id"]

            return {
                "status": "added",
                "message": "Alternate email added successfully.",
                "alias_id": alias_id,
            }

        except psycopg.IntegrityError:
            conn.rollback()
            return {"status": "error", "message": "That email address is already in use."}


def delete_client_alias(alias_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM client_email_aliases
                WHERE id = %s
                RETURNING id;
                """,
                (alias_id,),
            )
            return cur.fetchone() is not None
