import logging

from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger('discord')


class EmptyCompletionError(Exception):
    """Raised when a completion carries no assistant text."""


def extract_text(response) -> str:
    """Return the assistant text from a completion, or raise EmptyCompletionError.

    Reasoning models (e.g. z-ai/glm-5.3-flash, which cannot disable thinking)
    count thinking tokens against the output budget. When that budget runs out
    the response has finish_reason "length" and content None.
    """
    choice = response.choices[0]
    message = choice.message
    text = (message.content or "").strip()
    if text:
        return text

    usage = getattr(response, "usage", None)
    details = getattr(usage, "completion_tokens_details", None)
    logger.warning(
        "Empty completion: model=%s finish_reason=%s refusal=%r tool_calls=%s reasoning_tokens=%s",
        getattr(response, "model", None),
        choice.finish_reason,
        getattr(message, "refusal", None),
        bool(getattr(message, "tool_calls", None)),
        getattr(details, "reasoning_tokens", None),
    )
    raise EmptyCompletionError(f"empty completion (finish_reason={choice.finish_reason})")


class OpenRouterClient:
    _instance = None
    _client: OpenAI = None
    _async_client: AsyncOpenAI = None
    def __new__(cls):
        if not cls._instance:
            cls._instance = super(OpenRouterClient, cls).__new__(cls)
        return cls._instance

    def set_client(self, api_key:str):
        self._client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self._async_client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    def chat(self, model:str, messages:list[dict], max_completion_tokens: int=2000, temperature:float=0.7, tools: list | None = None, reasoning: dict | None = None):
        if not self._client:
            raise ValueError("Client not set. Please set the client using set_client() method.")
        
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            n=1
        )
        extra_body = {}
        if tools:
            extra_body["tools"] = tools
        if reasoning:
            extra_body["reasoning"] = reasoning
        if extra_body:
            kwargs["extra_body"] = extra_body
        
        response = self._client.chat.completions.create(**kwargs)
        
        return response

    async def achat(self, model:str, messages:list[dict], max_completion_tokens: int=2000, temperature:float=0.7, tools: list | None = None, reasoning: dict | None = None):
        if not self._async_client:
            raise ValueError("Client not set. Please set the client using set_client() method.")
        
        kwargs = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            n=1
        )
        extra_body = {}
        if tools:
            extra_body["tools"] = tools
        if reasoning:
            extra_body["reasoning"] = reasoning
        if extra_body:
            kwargs["extra_body"] = extra_body
        
        response = await self._async_client.chat.completions.create(**kwargs)
        
        return response

OPENROUTER_CLIENT = OpenRouterClient()
