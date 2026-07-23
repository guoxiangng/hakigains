"""Select an LLM provider from the LLM_PROVIDER env var."""
import os

from .base import LLMProvider


def get_provider() -> LLMProvider:
    provider = os.environ.get("LLM_PROVIDER", "azure_openai").lower()

    if provider == "azure_openai":
        from .azure_openai import AzureOpenAIProvider

        return AzureOpenAIProvider()

    # Future: "bedrock" -> BedrockClaudeProvider (own AWS account, no egress)
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")
