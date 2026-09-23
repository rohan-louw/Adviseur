import os

from dotenv import load_dotenv
from openai import OpenAI
from typing import Literal
from pydantic import BaseModel


class ClientTriage(BaseModel):
    category: Literal[
        "ADMIN",
        "GENERAL_QUERY",
        "DOCUMENT_REQUEST",
        "SERVICE_REQUEST",
        "FINANCIAL_ADVICE",
        "URGENT"
    ]

    urgency: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ]

    requires_human: bool
    reason: str
    recommended_action: str

# Load variables from the .env file
load_dotenv()

# Create an OpenAI client using our API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def classify_client_message(message):
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
        text_format=ClientTriage
    )

    return response.output_parsed


