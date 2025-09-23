import os
from .settings import settings
from openai import OpenAI, AzureOpenAI

def get_openai_client():
    # Prefer Azure if endpoint provided
    if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY and settings.AZURE_OPENAI_DEPLOYMENT:
        return AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-06-01",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        ), settings.AZURE_OPENAI_DEPLOYMENT, True
    # Default to OpenAI
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=settings.OPENAI_API_KEY), "gpt-4o-mini", False
