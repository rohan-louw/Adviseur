import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg.connect(
        host="localhost",
        port=5432,
        dbname="financial_advisor_pa",
        user="louwkie",
        password=os.getenv("DB_PASSWORD")
    )

def save_client_message(message, result, client_id=None):
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
                    recommended_action
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    client_id,
                    message,
                    result.category,
                    result.urgency,
                    result.requires_human,
                    result.reason,
                    result.recommended_action,
                ),
            )

    return True



def get_client_by_email(email):
    conn = get_connection()

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                id,
                name,
                email
            FROM clients
            WHERE LOWER(email) = LOWER(%s);
            """,
            (email,)
        )

        client = cur.fetchone()

    conn.close()

    return client

def create_client(name, email):
    conn = get_connection()

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

            client = cur.fetchone()

        conn.commit()
        return client

    except psycopg.IntegrityError:
        conn.rollback()
        return None

    finally:
        conn.close()

def get_clients():
    conn = get_connection()

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
            ORDER BY name;
            """
        )

        clients = cur.fetchall()

    conn.close()

    return clients

def update_client(
    client_id,
    phone,
    client_ref,
    status,
    risk_profile,
    date_joined,
    notes
):
    conn = get_connection()

    with conn.cursor() as cur:
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
            WHERE id = %s;
            """,
            (
                phone,
                client_ref,
                status,
                risk_profile,
                date_joined,
                notes,
                client_id,
            )
        )

    conn.commit()
    conn.close()

def update_client(client_id, phone, client_ref, status, risk_profile, date_joined, notes):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
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

            updated_client = cur.fetchone()
            conn.commit()

            return updated_client

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def get_messages_for_client(client_id):
    conn = get_connection()

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
                created_at
            FROM client_messages
            WHERE client_id = %s
            ORDER BY created_at DESC;
            """,
            (client_id,)
        )

        messages = cur.fetchall()

    conn.close()

    return messages

def get_client_messages():
    conn = get_connection()

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                cm.id,
                c.name AS client_name,
                c.email AS client_email,
                cm.message,
                cm.category,
                cm.urgency,
                cm.requires_human,
                cm.reason,
                cm.recommended_action,
                cm.created_at,
                cm.status
            FROM client_messages AS cm
            LEFT JOIN clients AS c
                ON cm.client_id = c.id
            ORDER BY cm.created_at DESC;
            """
        )

        messages = cur.fetchall()

    conn.close()

    return messages

def update_message_status(message_id, new_status):
    conn = get_connection()

    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE client_messages
            SET status = %s
            WHERE id = %s;
            """,
            (new_status, message_id),
        )

    conn.commit()
    conn.close()

    return True

if __name__ == "__main__":
    client = get_client_by_email("rohan@example.com")
    print(client)

    