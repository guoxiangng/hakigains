"""Amazon Bedrock / Claude provider — runs in our own AWS account, so the reasoning
call (and the health data in it) stays inside the account's AWS boundary.

Uses the Anthropic SDK's Bedrock client (InvokeModel under the hood) with a global
cross-region inference profile. Credentials + region come from the standard AWS
chain: the Lambda execution role in the cloud, ~/.aws locally.
"""
import os

from anthropic import AnthropicBedrock

from .base import LLMResponse

DEFAULT_MODEL = "global.anthropic.claude-sonnet-5-5"
# Client-side refusal fallback: Bedrock rejects the SDK's fallback middleware
# header, so a refused request is retried once on this model instead.
DEFAULT_FALLBACK_MODEL = "global.anthropic.claude-opus-4-8"


class BedrockClaudeProvider:
    def __init__(self) -> None:
        # aws_region=None -> AWS_REGION / AWS_DEFAULT_REGION / ~/.aws/config.
        self.client = AnthropicBedrock(aws_region=os.environ.get("BEDROCK_REGION"))
        self.model = os.environ.get("BEDROCK_MODEL_ID", DEFAULT_MODEL)
        self.fallback_model = os.environ.get(
            "BEDROCK_FALLBACK_MODEL_ID", DEFAULT_FALLBACK_MODEL
        )
        # Thinking depth. Set BEDROCK_EFFORT="" for models that reject the
        # parameter (e.g. Haiku 4.5).
        self.effort = os.environ.get("BEDROCK_EFFORT", "medium")

    def _create(self, model: str, system: str, user: str):
        kwargs = {}
        if system:
            kwargs["system"] = system
        if model == self.model and self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        return self.client.messages.create(
            model=model,
            max_tokens=16000,
            messages=[{"role": "user", "content": user}],
            **kwargs,
        )

    def complete(self, system: str, user: str) -> LLMResponse:
        resp = self._create(self.model, system, user)
        if resp.stop_reason == "refusal" and self.fallback_model:
            resp = self._create(self.fallback_model, system, user)
        text = "".join(b.text for b in resp.content if b.type == "text")
        return LLMResponse(text=text, raw=resp)
