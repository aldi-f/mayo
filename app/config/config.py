import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", ".")
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////data/mayo.db")
    GUILD_ID: int | None = None
    # Discord rejects messages longer than this.
    DISCORD_MESSAGE_LIMIT: int = 2000
    # Reasoning models like z-ai/glm-5.3-flash cannot disable thinking, so keep
    # it cheap and fast instead of letting it eat the whole output budget.
    REASONING_EFFORT: str = "low"

    BASE_MODEL = os.getenv("BASE_MODEL", "google/gemini-3.1-flash-lite")
    GROK_MODEL = os.getenv("GROK_MODEL", "xiaomi/mimo-v2.5") # the chinese are cheaper and better


    BASE_SYSTEM_PROMPT: str = os.getenv("BASE_SYSTEM_PROMPT",(
        "Your name is Mayo."
        "You are sometimes sarcastic."
        "You answer questions that people have but try to be funny sometimes."
    ))

    BASE_GROK_SYSTEM_PROMPT: str = os.getenv("BASE_GROK_SYSTEM_PROMPT", (
        "You are a fact-checking assistant."
        "Your job is to verify whether the given claim is true or false using web search."
        "Ensure the text fact is real first before going into checking if the post itself is true."
        "Provide a clear verdict, supporting evidence, and cite your sources with markdown formatted full link when possible."
        "Be concise but thorough."
    ))

    def __post_init__(self):
        guild_id = os.getenv("GUILD_ID")
        if guild_id is not None:
            object.__setattr__(self, "GUILD_ID", int(guild_id))

        if not self.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN is not set")
        if not self.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is not set")

settings = Settings()
