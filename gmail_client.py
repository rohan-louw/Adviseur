import base64
import json
from email.utils import parseaddr
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import get_secret
from email_service import process_email
from database import get_client_by_email


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"


def _credentials_from_deployment_secret():
    token_json = get_secret("GOOGLE_TOKEN_JSON")
    if not token_json:
        return None

    if isinstance(token_json, dict):
        info = token_json
    else:
        info = json.loads(str(token_json))

    return Credentials.from_authorized_user_info(info, SCOPES)


def get_gmail_service():
    creds = _credentials_from_deployment_secret()
    using_deployment_secret = creds is not None

    if creds is None and TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise RuntimeError(
                    "Gmail is not configured. For local use, add credentials.json; "
                    "for deployment, configure GOOGLE_TOKEN_JSON in app secrets."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        if not using_deployment_secret:
            TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_recent_messages(service, limit=5):
    response = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=limit)
        .execute()
    )

    messages = response.get("messages", [])
    results = []

    for item in messages:
        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        headers = message["payload"].get("headers", [])
        header_data = {header["name"]: header["value"] for header in headers}
        results.append(
            {
                "id": item["id"],
                "from": header_data.get("From", ""),
                "subject": header_data.get("Subject", ""),
                "date": header_data.get("Date", ""),
            }
        )

    return results


def decode_body(data):
    if not data:
        return ""
    decoded_bytes = base64.urlsafe_b64decode(data)
    return decoded_bytes.decode("utf-8", errors="replace")


def extract_plain_text(payload):
    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})

    if mime_type == "text/plain" and body.get("data"):
        return decode_body(body["data"])

    for part in payload.get("parts", []):
        text = extract_plain_text(part)
        if text:
            return text

    return ""


def get_message_by_subject(service, subject):
    response = (
        service.users()
        .messages()
        .list(userId="me", labelIds=["INBOX"], q=f'subject:"{subject}"', maxResults=1)
        .execute()
    )
    messages = response.get("messages", [])
    if not messages:
        return None

    gmail_id = messages[0]["id"]
    message = (
        service.users()
        .messages()
        .get(userId="me", id=gmail_id, format="full")
        .execute()
    )
    headers = message["payload"].get("headers", [])
    header_data = {header["name"].lower(): header["value"] for header in headers}
    sender_name, sender_email = parseaddr(header_data.get("from", ""))
    body = extract_plain_text(message["payload"]).strip()

    return {
        "id": gmail_id,
        "sender_name": sender_name,
        "sender_email": sender_email.lower(),
        "subject": header_data.get("subject", ""),
        "body": body,
    }


def get_label_id(service, label_name):
    response = service.users().labels().list(userId="me").execute()
    for label in response.get("labels", []):
        if label["name"].strip().upper() == label_name.strip().upper():
            return label["id"]
    return None


def sync_adviseur_emails(service, limit=50):
    """
    Sync recent Gmail messages into Adviseur.

    Known clients:
        - processed automatically

    Unknown senders:
        - processed only when Gmail considers the message PRIMARY
        - saved as Unknown Client for adviser review

    After successful handling, Adviseur applies the ADVISEUR label.
    """

    label_id = get_label_id(service, "ADVISEUR")

    if not label_id:
        raise ValueError("Gmail label 'ADVISEUR' was not found.")

    response = (
        service.users()
        .messages()
        .list(
            userId="me",
            labelIds=["INBOX"],
            q="-label:ADVISEUR",
            maxResults=limit,
        )
        .execute()
    )

    results = []

    for item in response.get("messages", []):
        gmail_id = item["id"]

        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=gmail_id,
                format="full",
            )
            .execute()
        )

        headers = message["payload"].get("headers", [])

        header_data = {
            header["name"].lower(): header["value"]
            for header in headers
        }

        _, sender_email = parseaddr(
            header_data.get("from", "")
        )

        sender_email = sender_email.strip().lower()

        if not sender_email:
            continue

        client = get_client_by_email(sender_email)

        gmail_labels = message.get("labelIds", [])

        # Known client:
        # process regardless of Gmail category.
        #
        # Unknown sender:
        # only process if Gmail considers it a PRIMARY inbox message.
        if not client and "CATEGORY_PRIMARY" not in gmail_labels:
            continue

        subject = header_data.get("subject", "")
        body = extract_plain_text(
            message["payload"]
        ).strip()

        try:
            result = process_email(
                sender=sender_email,
                subject=subject,
                body=body,
                external_message_id=gmail_id,
            )

            # Mark successfully handled Gmail messages.
            service.users().messages().modify(
                userId="me",
                id=gmail_id,
                body={
                    "addLabelIds": [label_id]
                },
            ).execute()

            results.append(
                {
                    "gmail_id": gmail_id,
                    "sender": sender_email,
                    "subject": subject,
                    "client": (
                        client["name"]
                        if client
                        else "Unknown Client"
                    ),
                    "status": result["status"],
                }
            )

        except Exception as exc:
            results.append(
                {
                    "gmail_id": gmail_id,
                    "sender": sender_email,
                    "subject": subject,
                    "client": (
                        client["name"]
                        if client
                        else "Unknown Client"
                    ),
                    "status": "ERROR",
                    "error": str(exc),
                }
            )

    return results