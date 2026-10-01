import os

from dotenv import load_dotenv


# Load local .env file when running Adviseur on your Mac.
# In cloud deployment, Streamlit secrets/environment variables are used instead.
load_dotenv()


def get_secret(name, default=None):
    """Read configuration from environment variables or Streamlit secrets."""

    value = os.getenv(name)

    if value not in (None, ""):
        return value

    try:
        import streamlit as st

        if name in st.secrets:
            return st.secrets[name]

    except Exception:
        pass

    return default