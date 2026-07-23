"""Azure OpenAI provider — TEMPORARY, throwaway corporate endpoint for local
prototyping. Real target is Bedrock/Claude in our own AWS account.
"""
import os

from openai import AzureOpenAI

from .base import LLMResponse


class AzureOpenAIProvider:
    def __init__(self) -> None:
        self.client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
        # For Azure, the "model" arg is the *deployment* name, not the model id.
        self.deployment = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]

    def complete(self, system: str, user: str) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        resp = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
        )
        return LLMResponse(text=resp.choices[0].message.content, raw=resp)
