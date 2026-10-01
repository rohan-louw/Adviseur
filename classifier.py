from typing import Literal

from openai import OpenAI
from pydantic import BaseModel

from config import get_secret


class ClientTriage(BaseModel):
    category: Literal[
        "ADMIN",
        "GENERAL_QUERY",
        "DOCUMENT_REQUEST",
        "SERVICE_REQUEST",
        "FINANCIAL_ADVICE",
        "URGENT",
    ]
    urgency: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    requires_human: bool
    reason: str
    recommended_action: str


def classify_client_message(message):
    api_key = get_secret("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=api_key)

    instructions = """
    You are a client-message triage assistant for a financial advisory practice.

    Your job is to classify incoming client messages.

    Categories:
    - ADMIN
    - GENERAL_QUERY
    - DOCUMENT_REQUEST
    - SERVICE_REQUEST
    - FINANCIAL_ADVICE
    - URGENT

    Urgency levels:
    - LOW
    - MEDIUM
    - HIGH
    - CRITICAL

    Important rules:
    - Never give financial advice.
    - Any request to buy, sell, switch, withdraw, or change an investment
      must require human review.
    - Complaints should require human review.
    - Death, disability, claims, or highly time-sensitive financial matters
      should be escalated.
    - Administrative requests may be handled without an adviser where appropriate.
    - Recommended actions must be operational and must not execute or imply regulated advice.

    Return:
    Category:
    Urgency:
    Requires human:
    Reason:
    Recommended action:
    """

    response = client.responses.parse(
        model="gpt-5.6",
        instructions=instructions,
        input=message,
        text_format=ClientTriage,
    )

    return response.output_parsed
