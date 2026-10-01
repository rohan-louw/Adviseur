"""
Email ingestion service for Adviseur.

Responsibilities:
- retrieve incoming client emails
- extract sender, subject and body
- identify the client from PostgreSQL
- prevent duplicate email processing
- pass new messages into the Adviseur triage pipeline
- save classified messages to PostgreSQL
"""

from classifier import classify_client_message
from database import (
    get_client_by_email,
    save_client_message,
    message_already_processed,
)


def process_email(sender, subject, body, external_message_id=None):

    # Stop immediately if this email has already been processed
    if external_message_id and message_already_processed(external_message_id):
        return {
            "status": "SKIPPED",
            "reason": "Message already processed.",
            "external_message_id": external_message_id,
        }

    # Identify the client from their email address
    client = get_client_by_email(sender.strip().lower())

    message = f"""
From: {sender}
Subject: {subject}

{body}
"""

    # Only call the AI if this is a new message
    result = classify_client_message(message)

    client_id = client["id"] if client else None

    # Save the classified email to PostgreSQL
    save_client_message(
        message,
        result,
        client_id=client_id,
        source="GMAIL",
        external_message_id=external_message_id,
    )

    return {
        "status": "PROCESSED",
        "sender": sender,
        "subject": subject,
        "body": body,
        "client": client,
        "external_message_id": external_message_id,
        "classification": result,
    }


if __name__ == "__main__":
    email = process_email(
        sender="sarah.williams@example.com",
        subject="Urgent withdrawal request",
        body=(
            "Hi, I urgently need to withdraw R50,000 from my investment. "
            "Please process this today."
        ),
        external_message_id="test-gmail-message-001",
    )

    print(email)