"""One place that builds the OpenAI client, so a missing key fails with a message a user can act on.

Without this, the SDK's own error ("The api_key client option must be set…") reached the UI verbatim."""
import os

from openai import OpenAI, OpenAIError


class MissingAPIKeyError(OpenAIError):
    """Subclasses OpenAIError so code that handles the SDK's own error keeps handling this one."""


MISSING_KEY_MESSAGE = (
    "OPENAI_API_KEY is not set. Add it to backend/.env and restart the backend. "
    "Sources, Knowledge Map and the structural Lint checks work without one; Wiki Chat, "
    "ingest and semantic Lint checks need it."
)


def make_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise MissingAPIKeyError(MISSING_KEY_MESSAGE)
    return OpenAI(api_key=api_key)
