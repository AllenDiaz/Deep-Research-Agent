"""
Shared Vertex AI client for all deep_research agents.

All agent modules import `vertex_model` (and `vertex_flash_model` for lighter tasks)
from here so that token refresh and env-var loading happen in one place.
"""

import os
import google.auth
import google.auth.transport.requests
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel, set_tracing_disabled

load_dotenv(override=True)

_PROJECT_ID = os.getenv("GCP_PROJECT")
_LOCATION   = os.getenv("GCP_LOCATION", "us-central1")
_MODEL_NAME = os.getenv("MODEL_NAME", "google/gemini-2.5-pro")
_FLASH_MODEL = "google/gemini-2.5-flash"   # cheaper model for lighter tasks

# Disable OpenAI platform tracing — we are not using the OpenAI API
set_tracing_disabled(True)


def _base_url() -> str:
    return (
        f"https://{_LOCATION}-aiplatform.googleapis.com/v1/projects/{_PROJECT_ID}"
        f"/locations/{_LOCATION}/endpoints/openapi"
    )


def get_async_client() -> AsyncOpenAI:
    """Return a fresh AsyncOpenAI pointing at Vertex AI (refreshes ADC token)."""
    creds, _ = google.auth.default()
    req = google.auth.transport.requests.Request()
    creds.refresh(req)
    return AsyncOpenAI(base_url=_base_url(), api_key=creds.token)


def make_model(model_id: str | None = None) -> OpenAIChatCompletionsModel:
    """Return an OpenAIChatCompletionsModel backed by Vertex AI."""
    return OpenAIChatCompletionsModel(
        model=model_id or _MODEL_NAME,
        openai_client=get_async_client(),
    )


# Pre-built model objects used by agent modules
vertex_model       = make_model(_MODEL_NAME)   # Gemini 2.5 Pro (default)
vertex_flash_model = make_model(_FLASH_MODEL)  # Gemini 2.5 Flash (faster/cheaper)
